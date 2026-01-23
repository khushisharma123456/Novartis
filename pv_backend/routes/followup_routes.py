"""
Follow-Up API routes for the Pharmacovigilance system.
Handles follow-up request management and completion.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from pv_backend.models import (
    db, User, UserRole, FollowUpRequest, FollowUpStatus,
    ExperienceEvent, EventSource, CaseMaster,
    AuditLog, AuditAction
)
from pv_backend.auth import token_required, roles_required
from pv_backend.services.followup_service import FollowUpService
from pv_backend.services.normalization_service import NormalizationService
from pv_backend.services.case_linking_service import CaseLinkingService
from pv_backend.services.scoring_service import ScoringService
from pv_backend.services.audit_service import AuditService


followup_bp = Blueprint('followup', __name__, url_prefix='/api/followups')


@followup_bp.route('', methods=['GET'])
@token_required
def list_followups():
    """
    List follow-up requests with optional filters.
    
    Query parameters:
    - status: Filter by status
    - priority: Filter by priority
    - assigned_to_type: Filter by assignment type (ai_agent, human)
    - limit: Maximum results (default 50)
    - offset: Pagination offset (default 0)
    """
    status = request.args.get('status')
    priority = request.args.get('priority')
    assigned_to_type = request.args.get('assigned_to_type')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    query = FollowUpRequest.query.filter_by(is_deleted=False)
    
    if status:
        try:
            status_enum = FollowUpStatus(status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass
    
    if priority:
        query = query.filter_by(priority=priority)
    
    if assigned_to_type:
        query = query.filter_by(assigned_to_type=assigned_to_type)
    
    # Order by priority and due date
    priority_order = db.case(
        (FollowUpRequest.priority == 'urgent', 1),
        (FollowUpRequest.priority == 'high', 2),
        (FollowUpRequest.priority == 'normal', 3),
        else_=4
    )
    query = query.order_by(priority_order, FollowUpRequest.due_by.asc())
    
    total = query.count()
    followups = query.offset(offset).limit(limit).all()
    
    return jsonify({
        'success': True,
        'total': total,
        'limit': limit,
        'offset': offset,
        'followups': [f.to_dict() for f in followups]
    }), 200


@followup_bp.route('/pending', methods=['GET'])
@token_required
def list_pending_followups():
    """
    List pending follow-ups for AI agents or human staff.
    
    Query parameters:
    - assigned_to_type: 'ai_agent' or 'human'
    - limit: Maximum results
    """
    assigned_to_type = request.args.get('assigned_to_type', 'ai_agent')
    limit = request.args.get('limit', 50, type=int)
    
    followups = FollowUpService.get_pending_followups(
        assigned_to_type=assigned_to_type,
        limit=limit
    )
    
    return jsonify({
        'success': True,
        'followups': [f.to_dict() for f in followups]
    }), 200


@followup_bp.route('/<int:followup_id>', methods=['GET'])
@token_required
def get_followup(followup_id):
    """
    Get follow-up request details.
    """
    followup = FollowUpRequest.query.filter_by(
        id=followup_id,
        is_deleted=False
    ).first()
    
    if not followup:
        return jsonify({
            'success': False,
            'message': 'Follow-up not found'
        }), 404
    
    # Get related case and event
    case = CaseMaster.query.get(followup.case_id)
    event = ExperienceEvent.query.get(followup.event_id) if followup.event_id else None
    
    return jsonify({
        'success': True,
        'followup': followup.to_dict(),
        'case': case.to_dict() if case else None,
        'original_event': event.to_dict() if event else None
    }), 200


@followup_bp.route('/<int:followup_id>/assign', methods=['POST'])
@token_required
@roles_required(UserRole.ADMIN)
def assign_followup(followup_id):
    """
    Assign a follow-up request.
    
    Request body:
    - assigned_to_type: 'ai_agent' or 'human'
    - assigned_to_user_id: User ID (if assigning to human)
    """
    followup = FollowUpRequest.query.filter_by(
        id=followup_id,
        is_deleted=False
    ).first()
    
    if not followup:
        return jsonify({
            'success': False,
            'message': 'Follow-up not found'
        }), 404
    
    data = request.get_json()
    
    if not data or not data.get('assigned_to_type'):
        return jsonify({
            'success': False,
            'message': 'assigned_to_type is required'
        }), 400
    
    try:
        user = g.current_user
        state_before = followup.to_dict()
        
        followup.assigned_to_type = data['assigned_to_type']
        followup.assigned_to_user_id = data.get('assigned_to_user_id')
        followup.status = FollowUpStatus.IN_PROGRESS
        
        AuditService.log_update(
            user=user,
            entity_type='FollowUpRequest',
            entity_id=followup.id,
            entity_identifier=f'Followup-{followup.id}',
            state_before=state_before,
            state_after=followup.to_dict(),
            reason=f'Assigned to {data["assigned_to_type"]}'
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Follow-up assigned',
            'followup': followup.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error assigning follow-up: {str(e)}'
        }), 500


@followup_bp.route('/<int:followup_id>/complete', methods=['POST'])
@token_required
def complete_followup(followup_id):
    """
    Complete a follow-up request with response data.
    
    PV Context:
    - Response data creates a new experience event
    - The event is linked to the same case
    - Case score is re-evaluated
    
    Request body:
    - response_data: The follow-up response data
      - observed_events: New observations
      - outcome: Updated outcome
      - (other relevant fields)
    - summary: Summary of the follow-up response
    """
    followup = FollowUpRequest.query.filter_by(
        id=followup_id,
        is_deleted=False
    ).first()
    
    if not followup:
        return jsonify({
            'success': False,
            'message': 'Follow-up not found'
        }), 404
    
    if followup.status == FollowUpStatus.COMPLETED:
        return jsonify({
            'success': False,
            'message': 'Follow-up already completed'
        }), 400
    
    data = request.get_json()
    
    if not data or not data.get('response_data'):
        return jsonify({
            'success': False,
            'message': 'response_data is required'
        }), 400
    
    try:
        user = g.current_user
        response_data = data['response_data']
        
        # Get the original event to copy relevant data
        original_event = ExperienceEvent.query.get(followup.event_id)
        case = CaseMaster.query.get(followup.case_id)
        
        # Create new experience event for the follow-up response
        response_event = ExperienceEvent(
            source=EventSource.AI_FOLLOWUP,
            reporter_id=followup.target_reporter_id,
            submitted_by_user_id=user.id,
            drug_name=original_event.drug_name if original_event else response_data.get('drug_name'),
            drug_code=original_event.drug_code if original_event else None,
            patient_identifier_hash=original_event.patient_identifier_hash if original_event else None,
            indication=response_data.get('indication') or (original_event.indication if original_event else None),
            dosage=response_data.get('dosage') or (original_event.dosage if original_event else None),
            observed_events=response_data.get('observed_events'),
            outcome=response_data.get('outcome'),
            event_date=datetime.utcnow(),
            raw_payload={'followup_response': response_data, 'followup_id': followup.id},
            case_id=case.id
        )
        
        db.session.add(response_event)
        db.session.flush()
        
        # Normalize the response event
        normalized = NormalizationService.normalize_event(response_event, user)
        db.session.flush()
        
        # Update case score
        ScoringService.update_case_score(
            case=case,
            normalized=normalized,
            trigger_event_id=response_event.id,
            user=user
        )
        
        # Complete the follow-up
        followup.status = FollowUpStatus.COMPLETED
        followup.completed_at = datetime.utcnow()
        followup.completed_by_user_id = user.id
        followup.response_event_id = response_event.id
        followup.response_summary = data.get('summary')
        
        # Update case follow-up status
        pending_count = FollowUpRequest.query.filter_by(
            case_id=case.id,
            status=FollowUpStatus.PENDING,
            is_deleted=False
        ).filter(FollowUpRequest.id != followup.id).count()
        
        if pending_count == 0:
            case.has_pending_followup = False
        
        # Audit log
        AuditService.log_update(
            user=user,
            entity_type='FollowUpRequest',
            entity_id=followup.id,
            entity_identifier=f'Followup-{followup.id}',
            state_before={'status': 'pending'},
            state_after=followup.to_dict(),
            reason='Follow-up completed with response'
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Follow-up completed successfully',
            'followup': followup.to_dict(),
            'response_event_id': response_event.id,
            'new_score': {
                'polarity': normalized.polarity.value if normalized.polarity else None,
                'strength': normalized.strength,
                'computed_score': normalized.computed_score,
                'case_current_score': case.current_score
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error completing follow-up: {str(e)}'
        }), 500


@followup_bp.route('/<int:followup_id>/cancel', methods=['POST'])
@token_required
@roles_required(UserRole.ADMIN)
def cancel_followup(followup_id):
    """
    Cancel a follow-up request.
    
    Request body:
    - reason: Reason for cancellation
    """
    followup = FollowUpRequest.query.filter_by(
        id=followup_id,
        is_deleted=False
    ).first()
    
    if not followup:
        return jsonify({
            'success': False,
            'message': 'Follow-up not found'
        }), 404
    
    data = request.get_json() or {}
    
    try:
        user = g.current_user
        state_before = followup.to_dict()
        
        followup.status = FollowUpStatus.CANCELLED
        
        AuditService.log_update(
            user=user,
            entity_type='FollowUpRequest',
            entity_id=followup.id,
            entity_identifier=f'Followup-{followup.id}',
            state_before=state_before,
            state_after=followup.to_dict(),
            reason=data.get('reason', 'Cancelled by admin')
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Follow-up cancelled',
            'followup': followup.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error cancelling follow-up: {str(e)}'
        }), 500
