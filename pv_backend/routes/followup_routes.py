"""
Follow-up Routes
================
API endpoints for sending and processing patient follow-up questionnaires.
"""

from flask import Blueprint, request, jsonify, render_template, session
from datetime import datetime, timedelta
import secrets

followup_bp = Blueprint('followup', __name__)

# In-memory token storage (in production, use Redis or database)
# Format: {token: {'patient_id': str, 'expires_at': datetime, 'used': bool}}
followup_tokens = {}


def store_followup_token(patient_id: str, token: str, expires_in_days: int = 7):
    """Store a follow-up token with expiration"""
    followup_tokens[token] = {
        'patient_id': patient_id,
        'expires_at': datetime.utcnow() + timedelta(days=expires_in_days),
        'used': False,
        'created_at': datetime.utcnow()
    }


def validate_followup_token(patient_id: str, token: str) -> dict:
    """Validate a follow-up token"""
    if token not in followup_tokens:
        return {'valid': False, 'error': 'Invalid token'}
    
    token_data = followup_tokens[token]
    
    if token_data['patient_id'] != patient_id:
        return {'valid': False, 'error': 'Token does not match patient'}
    
    if token_data['expires_at'] < datetime.utcnow():
        return {'valid': False, 'error': 'Token has expired'}
    
    if token_data['used']:
        return {'valid': False, 'error': 'Token has already been used'}
    
    return {'valid': True, 'token_data': token_data}


def init_followup_routes(app, db, Patient):
    """Initialize follow-up routes with app context"""
    
    from pv_backend.services.followup_agent import FollowupAgent
    
    @app.route('/api/followup/send', methods=['POST'])
    def send_followup_email():
        """Send a follow-up email to a specific patient"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        data = request.get_json()
        patient_id = data.get('patient_id')
        
        if not patient_id:
            return jsonify({'success': False, 'message': 'Patient ID required'}), 400
        
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        
        if not patient.email:
            return jsonify({
                'success': False, 
                'message': 'Patient does not have an email address on file'
            }), 400
        
        # Create agent and generate token
        agent = FollowupAgent()
        token = agent.generate_followup_token(patient_id)
        
        # Store token
        store_followup_token(patient_id, token)
        
        # Send email
        result = agent.send_followup_email(patient, token)
        
        if result['success']:
            # Update patient record
            patient.followup_sent_date = datetime.utcnow()
            patient.followup_pending = True
            db.session.commit()
        
        return jsonify(result)
    
    @app.route('/api/followup/send-bulk', methods=['POST'])
    def send_bulk_followup_emails():
        """Send follow-up emails to all patients needing follow-up"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        # Get patients who need follow-up
        patients = Patient.query.filter(
            Patient.follow_up_required == True,
            Patient.email.isnot(None),
            Patient.email != ''
        ).all()
        
        if not patients:
            return jsonify({
                'success': True,
                'message': 'No patients require follow-up emails',
                'count': 0
            })
        
        agent = FollowupAgent()
        results = {
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for patient in patients:
            token = agent.generate_followup_token(patient.id)
            store_followup_token(patient.id, token)
            
            result = agent.send_followup_email(patient, token)
            
            if result['success']:
                results['sent'] += 1
                patient.followup_sent_date = datetime.utcnow()
                patient.followup_pending = True
            else:
                results['failed'] += 1
            
            results['details'].append({
                'patient_id': patient.id,
                'patient_name': patient.name,
                'email': patient.email,
                'status': 'sent' if result['success'] else 'failed',
                'message': result.get('message') or result.get('error')
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f"Sent {results['sent']} follow-up emails",
            'results': results
        })
    
    @app.route('/followup/<patient_id>/<token>', methods=['GET'])
    def followup_form_page(patient_id, token):
        """Render the follow-up questionnaire form"""
        # Validate token
        validation = validate_followup_token(patient_id, token)
        
        if not validation['valid']:
            return render_template('followup/error.html', 
                                   error=validation['error']), 400
        
        patient = Patient.query.get(patient_id)
        if not patient:
            return render_template('followup/error.html', 
                                   error='Patient not found'), 404
        
        # Get questions for this patient
        agent = FollowupAgent()
        questions = agent.get_followup_questions(patient)
        
        return render_template('followup/form.html',
                               patient=patient,
                               questions=questions,
                               token=token)
    
    @app.route('/api/followup/submit/<patient_id>/<token>', methods=['POST'])
    def submit_followup_response(patient_id, token):
        """Process the submitted follow-up form"""
        # Validate token
        validation = validate_followup_token(patient_id, token)
        
        if not validation['valid']:
            return jsonify({
                'success': False,
                'message': validation['error']
            }), 400
        
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        
        # Get form data
        data = request.get_json() or request.form.to_dict()
        
        # Process response
        agent = FollowupAgent()
        result = agent.process_followup_response(patient, data)
        
        if result['success']:
            # Mark token as used
            followup_tokens[token]['used'] = True
            
            # Update patient follow-up status
            patient.followup_pending = False
            patient.followup_completed = True
            
            db.session.commit()
        
        return jsonify(result)
    
    @app.route('/api/followup/status/<patient_id>', methods=['GET'])
    def get_patient_followup_status(patient_id):
        """Get follow-up status for a patient"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'has_email': bool(patient.email),
            'email': patient.email,
            'follow_up_required': patient.follow_up_required,
            'followup_sent_date': patient.followup_sent_date.isoformat() if hasattr(patient, 'followup_sent_date') and patient.followup_sent_date else None,
            'followup_pending': getattr(patient, 'followup_pending', False),
            'followup_completed': getattr(patient, 'followup_completed', False),
            'followup_response_date': patient.followup_response_date.isoformat() if hasattr(patient, 'followup_response_date') and patient.followup_response_date else None
        })
    
    @app.route('/api/followup/config-status', methods=['GET'])
    def get_followup_config_status():
        """Check if email is properly configured"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        agent = FollowupAgent()
        
        return jsonify({
            'success': True,
            'email_configured': agent.is_email_configured(),
            'setup_instructions': {
                'step1': 'Enable 2-Factor Authentication on your Google Account',
                'step2': 'Create an App Password at: https://myaccount.google.com/apppasswords',
                'step3': 'Set environment variables: GMAIL_ADDRESS and GMAIL_APP_PASSWORD'
            }
        })
    
    return app
