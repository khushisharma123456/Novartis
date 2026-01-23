"""
Submission API routes for the Pharmacovigilance system.
Handles submissions from doctors, hospitals, and pharmacies.
"""
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from pv_backend.models import (
    db, User, UserRole, ExperienceEvent, EventSource,
    NormalizedExperience, CaseMaster, Reporter,
    AuditLog, AuditAction
)
from pv_backend.auth import token_required, roles_required, verified_pharmacy_required
from pv_backend.services.normalization_service import NormalizationService
from pv_backend.services.case_linking_service import CaseLinkingService
from pv_backend.services.scoring_service import ScoringService
from pv_backend.services.followup_service import FollowUpService
from pv_backend.services.audit_service import AuditService


submission_bp = Blueprint('submission', __name__, url_prefix='/api/submit')


def generate_idempotency_key(source: str, user_id: int, drug_name: str, patient_id: str, timestamp: str) -> str:
    """
    Generate a unique idempotency key for deduplication.
    
    PV Context:
    - Prevents duplicate submissions
    - Same submission within short window returns same result
    """
    key_string = f"{source}:{user_id}:{drug_name}:{patient_id}:{timestamp}"
    return hashlib.sha256(key_string.encode()).hexdigest()


def get_or_create_reporter(user: User, data: dict) -> Reporter:
    """
    Get or create a reporter record for the submission.
    
    PV Context:
    - Reporters are essential for follow-up
    - Links to user account if available
    """
    # Check for existing reporter linked to user
    existing = Reporter.query.filter_by(user_id=user.id, is_deleted=False).first()
    if existing:
        return existing
    
    # Create new reporter
    reporter = Reporter(
        user_id=user.id,
        reporter_type=user.role.value,
        full_name=user.full_name,
        email=user.email,
        qualification=data.get('qualification'),
        institution=user.organization,
        consent_to_contact=data.get('consent_to_contact', False),
        consent_date=datetime.utcnow() if data.get('consent_to_contact') else None
    )
    db.session.add(reporter)
    return reporter


def process_submission(user: User, data: dict, source: EventSource) -> dict:
    """
    Process a submission and return the result.
    
    PV Context:
    - This is the CORE submission processing pipeline
    - Creates: experience_event → normalized_experience → case_master
    - Links event to existing or new case
    - Computes score and triggers follow-ups if needed
    
    Pipeline:
    1. Validate and hash patient identifier
    2. Check idempotency
    3. Create experience event
    4. Create reporter (if needed)
    5. Normalize the event
    6. Link to case (existing or new)
    7. Update case score
    8. Check for follow-up triggers
    9. Audit log everything
    """
    # Hash patient identifier for privacy
    patient_id_raw = data.get('patient_identifier', '')
    if patient_id_raw:
        patient_hash = hashlib.sha256(patient_id_raw.encode()).hexdigest()
    else:
        patient_hash = None
    
    # Generate idempotency key
    idempotency_key = generate_idempotency_key(
        source=source.value,
        user_id=user.id,
        drug_name=data.get('drug_name', ''),
        patient_id=patient_hash or '',
        timestamp=datetime.utcnow().strftime('%Y%m%d%H')  # Hourly granularity
    )
    
    # Check for duplicate submission (idempotency)
    existing_event = ExperienceEvent.query.filter_by(
        idempotency_key=idempotency_key
    ).first()
    
    if existing_event:
        # Return existing event (idempotent)
        return {
            'success': True,
            'message': 'Duplicate submission detected, returning existing record',
            'is_duplicate': True,
            'event_id': existing_event.id,
            'case_id': existing_event.case_id,
            'case_number': existing_event.case.case_number if existing_event.case else None
        }
    
    # Get or create reporter
    reporter = get_or_create_reporter(user, data)
    
    # Create experience event
    event = ExperienceEvent(
        idempotency_key=idempotency_key,
        source=source,
        reporter_id=reporter.id,
        submitted_by_user_id=user.id,
        drug_name=data.get('drug_name'),
        drug_code=data.get('drug_code'),
        drug_batch=data.get('drug_batch'),
        patient_identifier_hash=patient_hash,
        indication=data.get('indication'),
        dosage=data.get('dosage'),
        route_of_administration=data.get('route_of_administration'),
        start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
        end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
        event_date=datetime.fromisoformat(data['event_date']) if data.get('event_date') else datetime.utcnow(),
        observed_events=data.get('observed_events'),
        outcome=data.get('outcome'),
        quantity_dispensed=data.get('quantity_dispensed'),
        prescriber_info=data.get('prescriber_info'),
        raw_payload=data
    )
    
    db.session.add(event)
    db.session.flush()  # Get event ID
    
    # Audit log: event created
    AuditService.log_create(
        user=user,
        entity_type='ExperienceEvent',
        entity_id=event.id,
        entity_identifier=f'Event-{event.id}',
        state_after=event.to_dict(),
        reason=f'New {source.value} submission'
    )
    
    # Normalize the event
    normalized = NormalizationService.normalize_event(event, user)
    db.session.flush()
    
    # Audit log: normalized created
    AuditService.log_create(
        user=user,
        entity_type='NormalizedExperience',
        entity_id=normalized.id,
        entity_identifier=f'Normalized-{normalized.id}',
        state_after=normalized.to_dict(),
        reason='Event normalization'
    )
    
    # Link to case
    case, linking_log = CaseLinkingService.link_event_to_case(event, normalized, user)
    db.session.flush()
    
    # Audit log: case linked/created
    if linking_log.is_new_case:
        AuditService.log_create(
            user=user,
            entity_type='CaseMaster',
            entity_id=case.id,
            entity_identifier=case.case_number,
            state_after=case.to_dict(),
            reason='New case created from event'
        )
    
    # Update case score
    score_history = ScoringService.update_case_score(
        case=case,
        normalized=normalized,
        trigger_event_id=event.id,
        user=user
    )
    
    # Check for follow-up triggers
    followups = FollowUpService.process_event_for_followup(
        event=event,
        normalized=normalized,
        case=case,
        user=user
    )
    
    # Commit all changes
    db.session.commit()
    
    # Build response
    response = {
        'success': True,
        'message': 'Submission processed successfully',
        'is_duplicate': False,
        'event_id': event.id,
        'case_id': case.id,
        'case_number': case.case_number,
        'is_new_case': linking_log.is_new_case,
        'linking_confidence': linking_log.confidence,
        'score': {
            'polarity': normalized.polarity.value if normalized.polarity else None,
            'strength': normalized.strength,
            'computed_score': normalized.computed_score,
            'case_current_score': case.current_score
        },
        'data_quality': {
            'has_mandatory_fields': normalized.has_mandatory_fields,
            'missing_fields': normalized.missing_fields
        },
        'followups_created': len(followups),
        'followup_reasons': [f.reason.value for f in followups] if followups else []
    }
    
    return response


@submission_bp.route('/doctor', methods=['POST'])
@token_required
@roles_required(UserRole.DOCTOR, UserRole.ADMIN)
def submit_doctor():
    """
    Submit a doctor/clinical observation.
    
    PV Context:
    - Doctor submissions have higher source credibility
    - Expected to have clinical context (indication, dosage)
    - Creates experience_event, normalized_experience, links to case
    
    Required fields:
    - drug_name: Name of the prescribed drug
    - patient_identifier: Unique patient ID (will be hashed)
    
    Optional fields:
    - drug_code: NDC, ATC code, etc.
    - indication: Why the drug was prescribed
    - dosage: Dosage information
    - route_of_administration: oral, IV, etc.
    - start_date: When drug was started (ISO format)
    - end_date: When drug was stopped (ISO format)
    - event_date: When observation occurred (ISO format)
    - observed_events: What happened (symptoms, reactions)
    - outcome: Patient outcome
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body is required'
        }), 400
    
    # Validate required fields
    if not data.get('drug_name'):
        return jsonify({
            'success': False,
            'message': 'drug_name is required'
        }), 400
    
    if not data.get('patient_identifier'):
        return jsonify({
            'success': False,
            'message': 'patient_identifier is required'
        }), 400
    
    try:
        user = g.current_user
        result = process_submission(user, data, EventSource.DOCTOR)
        
        status_code = 200 if result.get('is_duplicate') else 201
        return jsonify(result), status_code
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing submission: {str(e)}'
        }), 500


@submission_bp.route('/hospital', methods=['POST'])
@token_required
@roles_required(UserRole.HOSPITAL, UserRole.ADMIN)
def submit_hospital():
    """
    Submit a hospital/institutional report.
    
    PV Context:
    - Hospital submissions are similar to doctor submissions
    - May have additional institutional context
    - Expected to be more detailed/complete
    
    Required fields:
    - drug_name: Name of the drug
    - patient_identifier: Unique patient ID (will be hashed)
    
    Optional fields: (same as doctor submission)
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body is required'
        }), 400
    
    if not data.get('drug_name'):
        return jsonify({
            'success': False,
            'message': 'drug_name is required'
        }), 400
    
    if not data.get('patient_identifier'):
        return jsonify({
            'success': False,
            'message': 'patient_identifier is required'
        }), 400
    
    try:
        user = g.current_user
        result = process_submission(user, data, EventSource.HOSPITAL)
        
        status_code = 200 if result.get('is_duplicate') else 201
        return jsonify(result), status_code
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing submission: {str(e)}'
        }), 500


@submission_bp.route('/pharmacy', methods=['POST'])
@token_required
@roles_required(UserRole.PHARMACY, UserRole.ADMIN)
@verified_pharmacy_required
def submit_pharmacy():
    """
    Submit a pharmacy sale/dispensing record.
    
    PV Context:
    - Pharmacy submissions are SALES DATA, not AE reports
    - They do NOT assume adverse events
    - Lower clinical context (no indication, etc.)
    - May trigger AI follow-ups later to collect outcome data
    
    Required fields:
    - drug_name: Name of the drug sold
    - patient_identifier: Buyer identifier (phone/ID, will be hashed)
    - quantity_dispensed: Quantity sold
    
    Optional fields:
    - drug_code: NDC, ATC code
    - drug_batch: Batch/lot number
    - prescriber_info: Prescriber name/ID if available
    - event_date: Date of sale (ISO format)
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body is required'
        }), 400
    
    if not data.get('drug_name'):
        return jsonify({
            'success': False,
            'message': 'drug_name is required'
        }), 400
    
    if not data.get('patient_identifier'):
        return jsonify({
            'success': False,
            'message': 'patient_identifier (buyer identifier) is required'
        }), 400
    
    if not data.get('quantity_dispensed'):
        return jsonify({
            'success': False,
            'message': 'quantity_dispensed is required'
        }), 400
    
    try:
        user = g.current_user
        result = process_submission(user, data, EventSource.PHARMACY)
        
        # Add pharmacy-specific note
        result['note'] = 'Pharmacy sale recorded. This may trigger follow-up for outcome collection.'
        
        status_code = 200 if result.get('is_duplicate') else 201
        return jsonify(result), status_code
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing submission: {str(e)}'
        }), 500


# --- Development Endpoint (No Auth Required) ---

@submission_bp.route('/doctor-dev', methods=['POST'])
def submit_doctor_dev():
    """
    Development-only endpoint for doctor submissions WITHOUT authentication.
    
    WARNING: This endpoint should be DISABLED in production!
    
    It uses or creates a default development doctor user for testing.
    
    Same fields as /doctor endpoint but no JWT required.
    """
    from flask import current_app
    
    # Only allow in development mode
    if not current_app.config.get('DEBUG', False):
        return jsonify({
            'success': False,
            'message': 'This endpoint is only available in development mode'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body is required'
        }), 400
    
    if not data.get('drug_name'):
        return jsonify({
            'success': False,
            'message': 'drug_name is required'
        }), 400
    
    if not data.get('patient_identifier'):
        return jsonify({
            'success': False,
            'message': 'patient_identifier is required'
        }), 400
    
    try:
        # Get or create development doctor user
        dev_user = User.query.filter_by(email='dev_doctor@medsafe.local').first()
        if not dev_user:
            dev_user = User(
                email='dev_doctor@medsafe.local',
                password_hash='dev_not_for_production',
                full_name='Development Doctor',
                role=UserRole.DOCTOR,
                organization='MedSafe Dev',
                is_active=True,
                is_verified=True
            )
            db.session.add(dev_user)
            db.session.commit()
        
        result = process_submission(dev_user, data, EventSource.DOCTOR)
        
        status_code = 200 if result.get('is_duplicate') else 201
        return jsonify(result), status_code
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing submission: {str(e)}'
        }), 500
