"""
Scoring Service for the Pharmacovigilance system.
Implements the scoring formula: Score = Polarity × Strength
"""
from datetime import datetime
from typing import Optional, Dict, Tuple

from pv_backend.models import (
    db, CaseMaster, CaseScoreHistory, NormalizedExperience, 
    Polarity, AuditLog, AuditAction
)


class ScoringService:
    """
    Service for computing and tracking case scores.
    
    PV Context:
    SCORING LOGIC (DO NOT CHANGE):
    
    Score = Polarity × Strength
    
    Where:
    - Polarity: AE=-1, NO_AE=+1, UNCLEAR=0
    - Strength: 0, 1, or 2 (data quality/completeness)
    
    Score Range: -2 to +2
    - -2 → Strong, well-documented AE
    - -1 → Weak/incomplete AE
    -  0 → Poor or unclear data
    - +1 → Moderate positive/no-AE experience
    - +2 → Strong, confirmed positive experience
    
    NOTE: Score reflects DATA CONFIDENCE, not medical severity.
    """
    
    ALGORITHM_VERSION = '1.0.0'
    
    # Polarity multipliers
    POLARITY_MULTIPLIER = {
        Polarity.AE: -1,
        Polarity.NO_AE: 1,
        Polarity.UNCLEAR: 0
    }
    
    @classmethod
    def calculate_score(cls, polarity: Polarity, strength: int) -> float:
        """
        Calculate score from polarity and strength.
        
        PV Context:
        - This is the CORE scoring formula
        - Score = Polarity × Strength
        - Range: -2 to +2
        """
        multiplier = cls.POLARITY_MULTIPLIER.get(polarity, 0)
        return multiplier * strength
    
    @classmethod
    def update_case_score(cls,
                         case: CaseMaster,
                         normalized: NormalizedExperience,
                         trigger_event_id: int = None,
                         user=None,
                         is_override: bool = False,
                         override_reason: str = None) -> CaseScoreHistory:
        """
        Update the case score based on a new/updated normalized experience.
        
        PV Context:
        - Scores are NEVER overwritten, only appended to history
        - This enables tracking of score evolution over time
        - Each score update creates a history record
        
        Args:
            case: The case to update
            normalized: The normalized experience with polarity/strength
            trigger_event_id: ID of the event that triggered this update
            user: User performing the action
            is_override: Whether this is a human override
            override_reason: Reason for override
        
        Returns:
            CaseScoreHistory record
        """
        # Calculate new score
        new_score = cls.calculate_score(normalized.polarity, normalized.strength)
        
        # Get previous score for delta tracking
        previous_score = case.current_score
        score_delta = new_score - (previous_score or 0)
        
        # Build scoring factors for audit
        scoring_factors = {
            'polarity': normalized.polarity.value if normalized.polarity else 'unknown',
            'polarity_confidence': normalized.polarity_confidence,
            'strength': normalized.strength,
            'strength_factors': normalized.strength_factors,
            'algorithm_version': cls.ALGORITHM_VERSION
        }
        
        # Build scoring notes
        scoring_notes = (
            f"Score calculated: {normalized.polarity.value if normalized.polarity else 'unclear'} "
            f"(confidence: {normalized.polarity_confidence:.2f}) × "
            f"strength {normalized.strength} = {new_score}"
        )
        
        # Create score history record
        score_history = CaseScoreHistory(
            case_id=case.id,
            triggered_by_event_id=trigger_event_id,
            polarity=normalized.polarity.value if normalized.polarity else 'unclear',
            strength=normalized.strength,
            score=new_score,
            previous_score=previous_score,
            score_delta=score_delta,
            scoring_factors=scoring_factors,
            scoring_notes=scoring_notes,
            scored_by='manual' if is_override else 'auto',
            scoring_algorithm_version=cls.ALGORITHM_VERSION,
            is_override=is_override,
            override_by_user_id=user.id if is_override and user else None,
            override_reason=override_reason
        )
        
        db.session.add(score_history)
        
        # Update case current score
        case.current_score = new_score
        
        # Update case priority based on score
        case.determine_priority()
        
        return score_history
    
    @classmethod
    def recalculate_case_score(cls, case: CaseMaster, user=None) -> CaseScoreHistory:
        """
        Recalculate case score based on all linked events.
        
        PV Context:
        - Sometimes we need to recalculate based on all data
        - This uses the most recent/strongest evidence
        - Useful after case merges or data corrections
        """
        # Get all normalized experiences for this case
        from pv_backend.models import ExperienceEvent
        
        events = ExperienceEvent.query.filter_by(
            case_id=case.id,
            is_deleted=False
        ).all()
        
        if not events:
            # No events, score is 0
            score_history = CaseScoreHistory(
                case_id=case.id,
                polarity='unclear',
                strength=0,
                score=0,
                previous_score=case.current_score,
                score_delta=-case.current_score if case.current_score else 0,
                scoring_notes='No events linked to case',
                scored_by='auto',
                scoring_algorithm_version=cls.ALGORITHM_VERSION
            )
            db.session.add(score_history)
            case.current_score = 0
            case.determine_priority()
            return score_history
        
        # Find the strongest evidence (highest absolute score)
        best_normalized = None
        best_score_abs = -1
        
        for event in events:
            if event.normalized:
                normalized = event.normalized[0] if isinstance(event.normalized, list) else event.normalized
                abs_score = abs(normalized.computed_score)
                if abs_score > best_score_abs:
                    best_score_abs = abs_score
                    best_normalized = normalized
        
        if best_normalized:
            return cls.update_case_score(
                case=case,
                normalized=best_normalized,
                user=user
            )
        else:
            # No normalized data
            score_history = CaseScoreHistory(
                case_id=case.id,
                polarity='unclear',
                strength=0,
                score=0,
                previous_score=case.current_score,
                scoring_notes='No normalized data available',
                scored_by='auto',
                scoring_algorithm_version=cls.ALGORITHM_VERSION
            )
            db.session.add(score_history)
            case.current_score = 0
            case.determine_priority()
            return score_history
    
    @classmethod
    def override_score(cls,
                      case: CaseMaster,
                      new_polarity: Polarity,
                      new_strength: int,
                      reason: str,
                      user) -> CaseScoreHistory:
        """
        Override the case score manually (human override).
        
        PV Context:
        - Humans can override automated scoring
        - This is CRITICAL for PV systems
        - Full audit trail is maintained
        
        Args:
            case: The case to update
            new_polarity: Override polarity
            new_strength: Override strength (0-2)
            reason: Reason for the override
            user: User performing the override
        
        Returns:
            CaseScoreHistory record
        """
        # Validate strength
        if new_strength not in [0, 1, 2]:
            raise ValueError('Strength must be 0, 1, or 2')
        
        # Calculate new score
        new_score = cls.calculate_score(new_polarity, new_strength)
        
        # Create history record
        score_history = CaseScoreHistory(
            case_id=case.id,
            polarity=new_polarity.value,
            strength=new_strength,
            score=new_score,
            previous_score=case.current_score,
            score_delta=new_score - (case.current_score or 0),
            scoring_notes=f'Manual override: {reason}',
            scored_by='manual',
            scoring_algorithm_version=cls.ALGORITHM_VERSION,
            is_override=True,
            override_by_user_id=user.id,
            override_reason=reason
        )
        
        db.session.add(score_history)
        
        # Update case
        case.current_score = new_score
        case.determine_priority()
        
        return score_history
