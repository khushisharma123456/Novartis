"""
Case Management API routes for the Pharmacovigilance system.
Handles case retrieval, scoring, and follow-up management.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from pv_backend.models import (
    db, User, UserRole, CaseMaster, CaseScoreHistory,
    ExperienceEvent, NormalizedExperience, FollowUpRequest,
    FollowUpStatus, AdverseEvent, Polarity,
    AuditLog, AuditAction
)
from pv_backend.auth import token_required, roles_required, admin_required
from pv_backend.services.scoring_service import ScoringService
from pv_backend.services.followup_service import FollowUpService
from pv_backend.services.audit_service import AuditService


case_bp = Blueprint('case', __name__, url_prefix='/api/cases')


@case_bp.route('', methods=['GET'])
@token_required
def list_cases():
    """
    List cases with optional filters.
    
    Query parameters:
    - status: Filter by status (open, closed, under_review, reported)
    - priority: Filter by priority (low, normal, high, critical)
    - min_score: Minimum score filter
    - max_score: Maximum score filter
    - has_followup: Filter cases with pending follow-ups (true/false)
    - limit: Maximum results (default 50)
    - offset: Pagination offset (default 0)
    """
    # Parse query parameters
    status = request.args.get('status')
    priority = request.args.get('priority')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    has_followup = request.args.get('has_followup')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Build query
    query = CaseMaster.query.filter_by(is_deleted=False)
    
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if min_score is not None:
        query = query.filter(CaseMaster.current_score >= min_score)
    if max_score is not None:
        query = query.filter(CaseMaster.current_score <= max_score)
    if has_followup:
        has_pending = has_followup.lower() == 'true'
        query = query.filter_by(has_pending_followup=has_pending)
    
    # Order by priority (critical first) and latest event date
    priority_order = db.case(
        (CaseMaster.priority == 'critical', 1),
        (CaseMaster.priority == 'high', 2),
        (CaseMaster.priority == 'normal', 3),
        else_=4
    )
    query = query.order_by(priority_order, CaseMaster.latest_event_date.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    cases = query.offset(offset).limit(limit).all()
    
    return jsonify({
        'success': True,
        'total': total,
        'limit': limit,
        'offset': offset,
        'cases': [c.to_dict() for c in cases]
    }), 200


@case_bp.route('/<int:case_id>', methods=['GET'])
@token_required
def get_case(case_id):
    """
    Get detailed case information.
    
    PV Context:
    - Returns full case details including:
      - Case metadata
      - Linked events
      - Score history
      - Adverse events (if any)
      - Follow-up requests
    """
    case = CaseMaster.query.filter_by(id=case_id, is_deleted=False).first()
    
    if not case:
        return jsonify({
            'success': False,
            'message': 'Case not found'
        }), 404
    
    # Get linked events
    events = ExperienceEvent.query.filter_by(
        case_id=case_id,
        is_deleted=False
    ).order_by(ExperienceEvent.created_at.desc()).all()
    
    # Get score history
    score_history = CaseScoreHistory.query.filter_by(
        case_id=case_id
    ).order_by(CaseScoreHistory.created_at.desc()).limit(10).all()
    
    # Get adverse events
    adverse_events = AdverseEvent.query.filter_by(
        case_id=case_id,
        is_deleted=False
    ).all()
    
    # Get follow-ups
    followups = FollowUpRequest.query.filter_by(
        case_id=case_id,
        is_deleted=False
    ).order_by(FollowUpRequest.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'case': case.to_dict(),
        'events': [e.to_dict() for e in events],
        'score_history': [s.to_dict() for s in score_history],
        'adverse_events': [a.to_dict() for a in adverse_events],
        'followups': [f.to_dict() for f in followups]
    }), 200


@case_bp.route('/<int:case_id>/score', methods=['GET'])
@token_required
def get_case_score(case_id):
    """
    Get case score details and history.
    
    PV Context:
    - Returns current score and full history
    - Score = Polarity × Strength
    - History shows score evolution over time
    """
    case = CaseMaster.query.filter_by(id=case_id, is_deleted=False).first()
    
    if not case:
        return jsonify({
            'success': False,
            'message': 'Case not found'
        }), 404
    
    # Get full score history
    score_history = CaseScoreHistory.query.filter_by(
        case_id=case_id
    ).order_by(CaseScoreHistory.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'case_id': case_id,
        'case_number': case.case_number,
        'current_score': case.current_score,
        'priority': case.priority,
        'score_history': [s.to_dict() for s in score_history]
    }), 200


@case_bp.route('/<int:case_id>/score/override', methods=['POST'])
@token_required
@roles_required(UserRole.ADMIN, UserRole.DOCTOR)
def override_case_score(case_id):
    """
    Override the case score (human override).
    
    PV Context:
    - Allows human override of automated scoring
    - Reason is MANDATORY
    - Full audit trail is maintained
    
    Request body:
    - polarity: 'ae', 'no_ae', or 'unclear'
    - strength: 0, 1, or 2
    - reason: Reason for the override (required)
    """
    case = CaseMaster.query.filter_by(id=case_id, is_deleted=False).first()
    
    if not case:
        return jsonify({
            'success': False,
            'message': 'Case not found'
        }), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body is required'
        }), 400
    
    # Validate required fields
    if 'polarity' not in data:
        return jsonify({
            'success': False,
            'message': 'polarity is required'
        }), 400
    
    if 'strength' not in data:
        return jsonify({
            'success': False,
            'message': 'strength is required'
        }), 400
    
    if not data.get('reason'):
        return jsonify({
            'success': False,
            'message': 'reason is required for score override'
        }), 400
    
    # Parse polarity
    try:
        polarity = Polarity(data['polarity'])
    except ValueError:
        return jsonify({
            'success': False,
            'message': f"Invalid polarity. Must be one of: {[p.value for p in Polarity]}"
        }), 400
    
    # Validate strength
    strength = data['strength']
    if strength not in [0, 1, 2]:
        return jsonify({
            'success': False,
            'message': 'strength must be 0, 1, or 2'
        }), 400
    
    try:
        user = g.current_user
        
        # Store before state
        state_before = case.to_dict()
        
        # Override score
        score_history = ScoringService.override_score(
            case=case,
            new_polarity=polarity,
            new_strength=strength,
            reason=data['reason'],
            user=user
        )
        
        # Audit log
        AuditService.log_override(
            user=user,
            entity_type='CaseMaster',
            entity_id=case.id,
            entity_identifier=case.case_number,
            state_before=state_before,
            state_after=case.to_dict(),
            reason=data['reason']
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Score overridden successfully',
            'case_id': case.id,
            'new_score': case.current_score,
            'score_history': score_history.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error overriding score: {str(e)}'
        }), 500


@case_bp.route('/<int:case_id>/follow-ups', methods=['GET'])
@token_required
def get_case_followups(case_id):
    """
    Get follow-up requests for a case.
    
    Query parameters:
    - status: Filter by status (pending, in_progress, completed, failed, cancelled)
    """
    case = CaseMaster.query.filter_by(id=case_id, is_deleted=False).first()
    
    if not case:
        return jsonify({
            'success': False,
            'message': 'Case not found'
        }), 404
    
    status = request.args.get('status')
    
    query = FollowUpRequest.query.filter_by(
        case_id=case_id,
        is_deleted=False
    )
    
    if status:
        try:
            status_enum = FollowUpStatus(status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass
    
    followups = query.order_by(FollowUpRequest.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'case_id': case_id,
        'case_number': case.case_number,
        'followups': [f.to_dict() for f in followups]
    }), 200


@case_bp.route('/<int:case_id>/status', methods=['PUT'])
@token_required
@roles_required(UserRole.ADMIN, UserRole.DOCTOR)
def update_case_status(case_id):
    """
    Update case status.
    
    Request body:
    - status: New status (open, closed, under_review, reported)
    - reason: Reason for status change
    """
    case = CaseMaster.query.filter_by(id=case_id, is_deleted=False).first()
    
    if not case:
        return jsonify({
            'success': False,
            'message': 'Case not found'
        }), 404
    
    data = request.get_json()
    
    if not data or not data.get('status'):
        return jsonify({
            'success': False,
            'message': 'status is required'
        }), 400
    
    valid_statuses = ['open', 'closed', 'under_review', 'reported']
    if data['status'] not in valid_statuses:
        return jsonify({
            'success': False,
            'message': f'Invalid status. Must be one of: {valid_statuses}'
        }), 400
    
    try:
        user = g.current_user
        state_before = case.to_dict()
        
        case.status = data['status']
        
        AuditService.log_update(
            user=user,
            entity_type='CaseMaster',
            entity_id=case.id,
            entity_identifier=case.case_number,
            state_before=state_before,
            state_after=case.to_dict(),
            reason=data.get('reason', f'Status changed to {data["status"]}')
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Case status updated',
            'case': case.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        }), 500


@case_bp.route('/<int:case_id>/audit', methods=['GET'])
@token_required
def get_case_audit_log(case_id):
    """
    Get audit log for a case.
    
    PV Context:
    - Full audit trail for regulatory compliance
    - Shows all changes to the case
    """
    case = CaseMaster.query.filter_by(id=case_id, is_deleted=False).first()
    
    if not case:
        return jsonify({
            'success': False,
            'message': 'Case not found'
        }), 404
    
    audit_logs = AuditService.get_entity_history(
        entity_type='CaseMaster',
        entity_id=case_id,
        limit=100
    )
    
    return jsonify({
        'success': True,
        'case_id': case_id,
        'case_number': case.case_number,
        'audit_log': [a.to_dict() for a in audit_logs]
    }), 200


# --- Development Endpoint (No Auth Required) ---

@case_bp.route('/dev', methods=['GET'])
def list_cases_dev():
    """
    Development-only endpoint to list cases WITHOUT authentication.
    
    WARNING: This endpoint should be DISABLED in production!
    
    Same functionality as the authenticated /cases endpoint.
    """
    from flask import current_app
    
    # Only allow in development mode
    if not current_app.config.get('DEBUG', False):
        return jsonify({
            'success': False,
            'message': 'This endpoint is only available in development mode'
        }), 403
    
    # Parse query parameters
    status = request.args.get('status')
    priority = request.args.get('priority')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    has_followup = request.args.get('has_followup')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Build query
    query = CaseMaster.query.filter_by(is_deleted=False)
    
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if min_score is not None:
        query = query.filter(CaseMaster.current_score >= min_score)
    if max_score is not None:
        query = query.filter(CaseMaster.current_score <= max_score)
    if has_followup:
        has_pending = has_followup.lower() == 'true'
        query = query.filter_by(has_pending_followup=has_pending)
    
    # Order by priority and latest event date
    priority_order = db.case(
        (CaseMaster.priority == 'critical', 1),
        (CaseMaster.priority == 'high', 2),
        (CaseMaster.priority == 'normal', 3),
        else_=4
    )
    query = query.order_by(priority_order, CaseMaster.latest_event_date.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    cases = query.offset(offset).limit(limit).all()
    
    return jsonify({
        'success': True,
        'total': total,
        'limit': limit,
        'offset': offset,
        'cases': [c.to_dict() for c in cases]
    }), 200
