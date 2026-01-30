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
        """Render the follow-up questionnaire form with predefined + LLM-generated questions"""
        from pv_backend.services.llm_service import get_combined_questions, PREDEFINED_QUESTIONS
        from models import AgentFollowupTracking
        
        # Validate token
        validation = validate_followup_token(patient_id, token)
        
        if not validation['valid']:
            return render_template('followup/error.html', 
                                   error=validation['error']), 400
        
        patient = Patient.query.get(patient_id)
        if not patient:
            return render_template('followup/error.html', 
                                   error='Patient not found'), 404
        
        # Get predefined questions from FollowupAgent
        agent = FollowupAgent()
        predefined_questions = agent.get_followup_questions(patient)
        
        # Get LLM-generated questions based on case scoring and missing data
        llm_questions_data = get_combined_questions(patient)
        llm_questions = llm_questions_data.get('llm_questions', [])
        
        # Convert LLM questions to form format
        for i, llm_q in enumerate(llm_questions):
            predefined_questions.append({
                'id': f'llm_question_{i}',
                'type': 'textarea',
                'label': llm_q.get('question', ''),
                'placeholder': 'Please describe...',
                'required': False,
                'maps_to_column': llm_q.get('maps_to_column')
            })
        
        # Get tracking record to check current day
        tracking = AgentFollowupTracking.query.filter_by(
            patient_id=patient_id,
            status='active'
        ).first()
        
        current_day = tracking.current_day if tracking else 1
        
        return render_template('followup/form.html',
                               patient=patient,
                               questions=predefined_questions,
                               token=token,
                               current_day=current_day,
                               llm_analysis=llm_questions_data.get('analysis', ''))
    
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
            
            # Mark email as responded in tracking (so WhatsApp knows)
            from models import AgentFollowupTracking
            tracking = AgentFollowupTracking.query.filter_by(
                patient_id=patient_id,
                status='active'
            ).first()
            
            if tracking:
                current_day = tracking.current_day
                setattr(tracking, f'day{current_day}_email_responded', True)
                setattr(tracking, f'day{current_day}_responses', data)
                # Update chatbot state so WhatsApp knows form was filled
                if tracking.chatbot_state == 'awaiting_language':
                    tracking.chatbot_state = 'informed'
                db.session.commit()
            
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
    
    # ===================================================================
    # WHATSAPP CHATBOT WEBHOOK
    # ===================================================================
    
    @app.route('/api/whatsapp/webhook', methods=['POST'])
    def whatsapp_webhook():
        """
        Twilio WhatsApp webhook - receives incoming messages from patients.
        Configure this URL in Twilio Console: Messaging > WhatsApp sandbox > Webhook URL
        """
        from pv_backend.services.whatsapp_chatbot import WhatsAppChatbot
        from models import AgentFollowupTracking
        
        # Get message details from Twilio
        from_number = request.values.get('From', '').replace('whatsapp:', '')
        body = request.values.get('Body', '').strip()
        
        if not from_number or not body:
            return 'OK', 200
        
        # Find patient by phone number
        patient = Patient.query.filter(
            Patient.phone.like(f'%{from_number[-10:]}%')  # Match last 10 digits
        ).first()
        
        if not patient:
            return 'OK', 200
        
        # Find or create tracking
        tracking = AgentFollowupTracking.query.filter_by(
            patient_id=patient.id,
            status='active'
        ).first()
        
        if not tracking:
            return 'OK', 200
        
        # Process message
        chatbot = WhatsAppChatbot()
        result = chatbot.process_incoming_message(tracking, patient, body)
        
        # Send response
        if result.get('response_message'):
            chatbot.send_message(patient.phone, result['response_message'])
        
        return 'OK', 200
    
    # ===================================================================
    # PHARMA RECALL API
    # ===================================================================
    
    @app.route('/api/pharma/recall', methods=['POST'])
    def request_patient_recall():
        """
        Pharma company requests patient recall for health check-up.
        Sends empathetic WhatsApp message to patient.
        """
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        from pv_backend.services.whatsapp_chatbot import WhatsAppChatbot
        from models import AgentFollowupTracking, User
        
        data = request.get_json()
        patient_id = data.get('patient_id')
        reason = data.get('reason', 'Routine health check-up')
        
        if not patient_id:
            return jsonify({'success': False, 'message': 'Patient ID required'}), 400
        
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        
        if not patient.phone:
            return jsonify({'success': False, 'message': 'Patient has no phone number'}), 400
        
        # Get company name from session user
        user = User.query.get(session['user_id'])
        company_name = user.name if user else 'Pharma Company'
        
        # Find tracking record
        tracking = AgentFollowupTracking.query.filter_by(
            patient_id=patient.id
        ).first()
        
        if not tracking:
            # Create a tracking record just for recall
            tracking = AgentFollowupTracking(
                patient_id=patient.id,
                status='recall_only',
                language_preference='English'
            )
            db.session.add(tracking)
            db.session.commit()
        
        # Send recall message
        chatbot = WhatsAppChatbot()
        result = chatbot.send_pharma_recall(tracking, patient, company_name, reason)
        
        if result.get('success'):
            patient.recalled = True
            patient.recalled_by = session['user_id']
            patient.recall_reason = reason
            patient.recall_date = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Recall message sent to patient',
                'patient_id': patient_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send recall message',
                'error': result.get('error')
            }), 500
    
    # ===================================================================
    # 2-HOUR REMINDER CHECK (Call via scheduler/cron)
    # ===================================================================
    
    @app.route('/api/agent/check-reminders', methods=['POST'])
    def check_pending_reminders():
        """
        Check for unanswered questions and send reminders.
        Should be called by a scheduler every 30 minutes.
        """
        from pv_backend.services.whatsapp_chatbot import check_and_send_reminders
        
        result = check_and_send_reminders()
        
        return jsonify({
            'success': True,
            'reminders_sent': result.get('reminders_sent', 0),
            'details': result.get('details', [])
        })
    
    # ===================================================================
    # SCHEDULED DAY CYCLE PROCESSING (Day 3, 5, 7)
    # ===================================================================
    
    @app.route('/api/agent/process-scheduled-followups', methods=['POST'])
    def process_scheduled_followups():
        """
        Process scheduled Day 3, 5, 7 follow-ups.
        Should be called by a scheduler once daily.
        
        This will:
        1. Check for trackings due for next day cycle
        2. Re-run case scoring with new response data
        3. Get new LLM questions
        4. Send Email + WhatsApp for the new day
        """
        from pv_backend.services.followup_agent import PVAgentOrchestrator
        from models import AgentFollowupTracking
        
        orchestrator = PVAgentOrchestrator()
        due_trackings = orchestrator.get_due_followups()
        
        results = {
            'processed': 0,
            'completed': 0,
            'errors': 0,
            'details': []
        }
        
        for tracking in due_trackings:
            try:
                result = orchestrator.process_day_cycle(tracking.id)
                
                if result.get('success'):
                    if result.get('completed'):
                        results['completed'] += 1
                    else:
                        results['processed'] += 1
                    
                    results['details'].append({
                        'tracking_id': tracking.id,
                        'patient_id': tracking.patient_id,
                        'current_day': result.get('current_day'),
                        'previous_day': result.get('previous_day'),
                        'status': 'success'
                    })
                else:
                    results['errors'] += 1
                    results['details'].append({
                        'tracking_id': tracking.id,
                        'patient_id': tracking.patient_id,
                        'status': 'error',
                        'error': result.get('error')
                    })
            except Exception as e:
                results['errors'] += 1
                results['details'].append({
                    'tracking_id': tracking.id,
                    'patient_id': tracking.patient_id,
                    'status': 'exception',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': f"Processed {results['processed']} day cycles, {results['completed']} completed, {results['errors']} errors",
            'results': results
        })
    
    # ===================================================================
    # AGENT STATUS & DASHBOARD
    # ===================================================================
    
    @app.route('/api/agent/status', methods=['GET'])
    def get_agent_status():
        """Get overall PV Agent status and statistics."""
        from models import AgentFollowupTracking
        
        active_trackings = AgentFollowupTracking.query.filter_by(status='active').count()
        completed_trackings = AgentFollowupTracking.query.filter_by(status='completed').count()
        patient_fine = AgentFollowupTracking.query.filter_by(status='patient_fine').count()
        
        # Get pending reminders (questions not answered in 2+ hours)
        now = datetime.utcnow()
        two_hours_ago = now - timedelta(hours=2)
        pending_reminders = AgentFollowupTracking.query.filter(
            AgentFollowupTracking.status == 'active',
            AgentFollowupTracking.chatbot_state == 'asking_questions',
            AgentFollowupTracking.last_question_sent_at <= two_hours_ago,
            AgentFollowupTracking.reminder_count < 3
        ).count()
        
        # Get due followups (next day cycle ready)
        due_followups = AgentFollowupTracking.query.filter(
            AgentFollowupTracking.status == 'active',
            AgentFollowupTracking.next_followup_date <= now
        ).count()
        
        return jsonify({
            'success': True,
            'status': {
                'active_trackings': active_trackings,
                'completed_trackings': completed_trackings,
                'patient_fine': patient_fine,
                'pending_reminders': pending_reminders,
                'due_followups': due_followups
            }
        })
    
    return app

