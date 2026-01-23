"""
Follow-Up Service for the Pharmacovigilance system.
Creates follow-up requests when data quality is insufficient.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from pv_backend.models import (
    db, ExperienceEvent, NormalizedExperience, CaseMaster,
    FollowUpRequest, FollowUpStatus, FollowUpReason, Polarity,
    Reporter, AuditLog, AuditAction
)


class FollowUpService:
    """
    Service for managing follow-up requests.
    
    PV Context:
    - Follow-ups are triggered when data is incomplete
    - They improve data quality and case strength
    - Can be assigned to AI agents or human staff
    
    Triggers:
    1. Score = 0 (unclear data)
    2. AE polarity but strength < 2 (incomplete AE)
    3. Missing mandatory fields
    """
    
    # Default due date offset
    DEFAULT_DUE_DAYS = 7
    
    # Maximum follow-up attempts
    MAX_ATTEMPTS = 3
    
    @classmethod
    def should_trigger_followup(cls, 
                               normalized: NormalizedExperience,
                               case: CaseMaster) -> List[Dict]:
        """
        Determine if follow-up is needed and why.
        
        PV Context:
        - Returns list of follow-up reasons (can be multiple)
        - Each reason generates a follow-up request
        
        Triggers:
        1. Score = 0 → Need clarification
        2. AE polarity + strength < 2 → Need more AE details
        3. Missing mandatory fields → Need specific data
        
        Returns:
            List of dicts with reason and details
        """
        triggers = []
        
        # Trigger 1: Score is 0 (unclear data)
        if normalized.computed_score == 0 and normalized.polarity == Polarity.UNCLEAR:
            triggers.append({
                'reason': FollowUpReason.SCORE_ZERO,
                'details': 'Unable to determine if adverse event occurred',
                'questions': [
                    'Did the patient experience any symptoms after taking the medication?',
                    'What was the outcome of the treatment?',
                    'Were there any changes in the patient\'s condition?'
                ]
            })
        
        # Trigger 2: AE polarity but strength < 2
        if normalized.polarity == Polarity.AE and normalized.strength < 2:
            missing_for_strength = []
            factors = normalized.strength_factors or {}
            
            if not factors.get('has_indication'):
                missing_for_strength.append('indication for use')
            if not factors.get('has_dosage'):
                missing_for_strength.append('dosage information')
            if not factors.get('has_dates'):
                missing_for_strength.append('event dates')
            if not factors.get('has_outcome'):
                missing_for_strength.append('outcome information')
            
            triggers.append({
                'reason': FollowUpReason.LOW_STRENGTH,
                'details': f'AE reported but insufficient documentation. Missing: {", ".join(missing_for_strength)}',
                'questions': [
                    f'Please provide {item}' for item in missing_for_strength
                ] + [
                    'Can you describe the adverse event in more detail?',
                    'What action was taken after the event occurred?'
                ]
            })
        
        # Trigger 3: Missing mandatory fields
        if not normalized.has_mandatory_fields and normalized.missing_fields:
            triggers.append({
                'reason': FollowUpReason.MISSING_FIELDS,
                'details': f'Missing mandatory fields: {", ".join(normalized.missing_fields)}',
                'questions': [
                    f'Please provide the {field.replace("_", " ")}' 
                    for field in normalized.missing_fields
                ],
                'missing_fields': normalized.missing_fields
            })
        
        return triggers
    
    @classmethod
    def create_followup_request(cls,
                                case: CaseMaster,
                                event: ExperienceEvent,
                                reason: FollowUpReason,
                                details: str,
                                questions: List[str],
                                missing_fields: List[str] = None,
                                user=None) -> FollowUpRequest:
        """
        Create a follow-up request.
        
        PV Context:
        - Follow-up requests are tracked and managed
        - They have a due date and attempt limits
        - Responses create new experience events
        """
        # Get reporter for follow-up target
        reporter = event.reporter if event else None
        
        # Determine priority based on case priority
        priority_map = {
            'critical': 'urgent',
            'high': 'high',
            'normal': 'normal',
            'low': 'low'
        }
        priority = priority_map.get(case.priority, 'normal')
        
        # Create follow-up request
        followup = FollowUpRequest(
            case_id=case.id,
            event_id=event.id if event else None,
            reason=reason,
            reason_details=details,
            questions=questions,
            missing_fields=missing_fields,
            target_reporter_id=reporter.id if reporter else None,
            target_contact=reporter.email if reporter else None,
            status=FollowUpStatus.PENDING,
            assigned_to_type='ai_agent',  # Default to AI agent
            priority=priority,
            due_by=datetime.utcnow() + timedelta(days=cls.DEFAULT_DUE_DAYS),
            max_attempts=cls.MAX_ATTEMPTS
        )
        
        db.session.add(followup)
        
        # Update case
        case.has_pending_followup = True
        
        return followup
    
    @classmethod
    def process_event_for_followup(cls,
                                   event: ExperienceEvent,
                                   normalized: NormalizedExperience,
                                   case: CaseMaster,
                                   user=None) -> List[FollowUpRequest]:
        """
        Process an event and create follow-up requests if needed.
        
        PV Context:
        - This is called after normalization and scoring
        - Creates follow-ups based on triggers
        
        Returns:
            List of created follow-up requests
        """
        # Check for triggers
        triggers = cls.should_trigger_followup(normalized, case)
        
        followups = []
        for trigger in triggers:
            followup = cls.create_followup_request(
                case=case,
                event=event,
                reason=trigger['reason'],
                details=trigger['details'],
                questions=trigger['questions'],
                missing_fields=trigger.get('missing_fields'),
                user=user
            )
            followups.append(followup)
        
        return followups
    
    @classmethod
    def complete_followup(cls,
                         followup: FollowUpRequest,
                         response_event: ExperienceEvent,
                         user) -> FollowUpRequest:
        """
        Mark a follow-up as completed.
        
        PV Context:
        - Response is stored as a new experience event
        - Follow-up status is updated
        - Case may need re-scoring
        """
        followup.status = FollowUpStatus.COMPLETED
        followup.completed_at = datetime.utcnow()
        followup.completed_by_user_id = user.id
        followup.response_event_id = response_event.id
        
        # Check if case still has pending follow-ups
        pending = FollowUpRequest.query.filter_by(
            case_id=followup.case_id,
            status=FollowUpStatus.PENDING,
            is_deleted=False
        ).filter(FollowUpRequest.id != followup.id).count()
        
        if pending == 0:
            case = CaseMaster.query.get(followup.case_id)
            if case:
                case.has_pending_followup = False
        
        return followup
    
    @classmethod
    def get_pending_followups(cls, 
                             case_id: int = None,
                             assigned_to_type: str = None,
                             limit: int = 100) -> List[FollowUpRequest]:
        """
        Get pending follow-up requests.
        
        Args:
            case_id: Filter by case (optional)
            assigned_to_type: Filter by assignment type (optional)
            limit: Maximum results
        
        Returns:
            List of pending follow-ups
        """
        query = FollowUpRequest.query.filter_by(
            status=FollowUpStatus.PENDING,
            is_deleted=False
        )
        
        if case_id:
            query = query.filter_by(case_id=case_id)
        
        if assigned_to_type:
            query = query.filter_by(assigned_to_type=assigned_to_type)
        
        # Order by priority and due date
        query = query.order_by(
            FollowUpRequest.priority.desc(),
            FollowUpRequest.due_by.asc()
        )
        
        return query.limit(limit).all()
