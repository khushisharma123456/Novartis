"""
Follow-up Agent Service
=======================
Sends follow-up questionnaire emails and WhatsApp messages to patients 
and processes their responses to update case data and improve case scoring.

Setup Gmail:
1. Enable 2-Factor Authentication on your Google Account
2. Go to: Google Account → Security → 2-Step Verification → App passwords
3. Generate an "App password" for Mail
4. Set environment variables:
   - GMAIL_ADDRESS=your-email@gmail.com
   - GMAIL_APP_PASSWORD=your-16-char-app-password

Setup Twilio WhatsApp:
1. Create a Twilio account at https://www.twilio.com
2. Set up WhatsApp Sandbox or approved WhatsApp Business API
3. Set environment variables:
   - TWILIO_ACCOUNT_SID=your-account-sid
   - TWILIO_AUTH_TOKEN=your-auth-token
   - TWILIO_WHATSAPP_FROM=whatsapp:+14155238886  (your Twilio WhatsApp number)
   
Or update the config in this file directly (not recommended for production).
"""

import smtplib
import os
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gmail Configuration - Set these via environment variables in .env file
GMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': os.environ.get('GMAIL_ADDRESS'),
    'password': os.environ.get('GMAIL_APP_PASSWORD'),
}

# Twilio WhatsApp Configuration - Set these via environment variables in .env file
TWILIO_CONFIG = {
    'account_sid': os.environ.get('TWILIO_ACCOUNT_SID'),
    'auth_token': os.environ.get('TWILIO_AUTH_TOKEN'),
    'whatsapp_from': os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886'),
}

# Base URL for the application (set in .env file)
# Using ngrok for public access - update APP_BASE_URL in .env when ngrok restarts
APP_BASE_URL = os.environ.get('APP_BASE_URL', 'http://localhost:5000')


class FollowupAgent:
    """
    Agent responsible for sending follow-up questionnaires to patients
    via email and WhatsApp, and processing their responses to update case data.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.email_config = GMAIL_CONFIG
        self.twilio_config = TWILIO_CONFIG
        self.twilio_client = None
        
        # Initialize Twilio client if credentials are available
        if self.is_whatsapp_configured():
            try:
                from twilio.rest import Client
                self.twilio_client = Client(
                    self.twilio_config['account_sid'],
                    self.twilio_config['auth_token']
                )
            except ImportError:
                print("⚠️ Twilio library not installed. Run: pip install twilio")
            except Exception as e:
                print(f"⚠️ Failed to initialize Twilio client: {e}")
        
    def configure_email(self, email: str, password: str):
        """Configure email credentials programmatically"""
        self.email_config['email'] = email
        self.email_config['password'] = password
    
    def configure_whatsapp(self, account_sid: str, auth_token: str, whatsapp_from: str):
        """Configure Twilio WhatsApp credentials programmatically"""
        self.twilio_config['account_sid'] = account_sid
        self.twilio_config['auth_token'] = auth_token
        self.twilio_config['whatsapp_from'] = whatsapp_from
        
        # Re-initialize client with new credentials
        try:
            from twilio.rest import Client
            self.twilio_client = Client(account_sid, auth_token)
        except Exception as e:
            print(f"⚠️ Failed to initialize Twilio client: {e}")
        
    def is_email_configured(self) -> bool:
        """Check if email credentials are properly configured"""
        return bool(self.email_config['email'] and self.email_config['password'])
    
    def is_whatsapp_configured(self) -> bool:
        """Check if WhatsApp/Twilio credentials are properly configured"""
        return bool(
            self.twilio_config.get('account_sid') and 
            self.twilio_config.get('auth_token') and
            self.twilio_config.get('whatsapp_from')
        )
    
    def generate_followup_token(self, patient_id: str) -> str:
        """Generate a secure token for the follow-up form link"""
        return secrets.token_urlsafe(32)
    
    def get_followup_questions(self, patient) -> list:
        """
        Generate follow-up questions based on patient's current data.
        Questions target missing or incomplete information to improve case scoring.
        """
        questions = []
        
        # Always ask about current status
        questions.append({
            'id': 'current_status',
            'type': 'select',
            'label': 'How are you feeling now regarding the reported side effect?',
            'options': ['Fully Recovered', 'Improving', 'Same as before', 'Worsening', 'New symptoms appeared'],
            'required': True
        })
        
        # Temporal clarity questions
        if not patient.symptom_onset_date:
            questions.append({
                'id': 'symptom_onset_date',
                'type': 'date',
                'label': 'When did the symptoms first appear?',
                'required': False
            })
            
        if not patient.symptom_resolution_date:
            questions.append({
                'id': 'symptom_resolution_date', 
                'type': 'date',
                'label': 'If symptoms have resolved, when did they stop?',
                'required': False
            })
        
        # Medical confirmation
        if not patient.doctor_confirmed:
            questions.append({
                'id': 'doctor_visit',
                'type': 'select',
                'label': 'Have you consulted a doctor about these symptoms?',
                'options': ['Yes', 'No', 'Planning to'],
                'required': False
            })
            
        # Severity update
        questions.append({
            'id': 'current_severity',
            'type': 'select',
            'label': 'How would you rate the severity of symptoms now?',
            'options': ['None', 'Mild', 'Moderate', 'Severe'],
            'required': True
        })
        
        # Additional symptoms
        questions.append({
            'id': 'additional_symptoms',
            'type': 'textarea',
            'label': 'Have you experienced any new or additional symptoms?',
            'placeholder': 'Describe any new symptoms, or write "None" if no new symptoms',
            'required': False
        })
        
        # Medication changes
        questions.append({
            'id': 'medication_status',
            'type': 'select',
            'label': 'Are you still taking the medication that caused the side effect?',
            'options': ['Yes, still taking', 'Stopped taking', 'Switched to alternative', 'Dosage changed'],
            'required': True
        })
        
        # Additional notes
        questions.append({
            'id': 'additional_notes',
            'type': 'textarea',
            'label': 'Any additional information you would like to share?',
            'placeholder': 'Optional: Share any other relevant information',
            'required': False
        })
        
        return questions
    
    def create_email_html(self, patient, followup_token: str) -> str:
        """Generate the HTML email content with the follow-up form link"""
        
        form_url = f"{APP_BASE_URL}/followup/{patient.id}/{followup_token}"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
        .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }}
        .button {{ display: inline-block; background: #3B82F6; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
        .button:hover {{ background: #2563eb; }}
        .footer {{ background: #1f2937; color: #9ca3af; padding: 20px; border-radius: 0 0 10px 10px; text-align: center; font-size: 12px; }}
        .info-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #3B82F6; }}
        .highlight {{ color: #3B82F6; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">📋 Follow-up Request</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Pharmacovigilance Safety Monitoring</p>
        </div>
        
        <div class="content">
            <p>Dear <span class="highlight">{patient.name}</span>,</p>
            
            <p>As part of our ongoing safety monitoring, we would like to follow up on the adverse event report 
            you submitted regarding <strong>{patient.drug_name}</strong>.</p>
            
            <div class="info-box">
                <p style="margin: 0;"><strong>📅 Original Report Date:</strong> {patient.created_at.strftime('%B %d, %Y') if patient.created_at else 'N/A'}</p>
                <p style="margin: 10px 0 0 0;"><strong>💊 Medication:</strong> {patient.drug_name}</p>
                <p style="margin: 10px 0 0 0;"><strong>📝 Reported Symptoms:</strong> {patient.symptoms or 'Not specified'}</p>
            </div>
            
            <p>Your feedback is crucial for ensuring medication safety. Please take a few minutes to complete our follow-up questionnaire:</p>
            
            <div style="text-align: center;">
                <a href="{form_url}" class="button">Complete Follow-up Form →</a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">
                ⏰ This link will expire in <strong>7 days</strong>.<br>
                🔒 Your information is kept confidential and secure.
            </p>
        </div>
        
        <div class="footer">
            <p>This is an automated message from the Pharmacovigilance Safety Monitoring System.</p>
            <p>If you did not submit a report or have questions, please contact your healthcare provider.</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def create_email_text(self, patient, followup_token: str) -> str:
        """Generate plain text version of the email"""
        form_url = f"{APP_BASE_URL}/followup/{patient.id}/{followup_token}"
        
        text = f"""
FOLLOW-UP REQUEST - Pharmacovigilance Safety Monitoring

Dear {patient.name},

As part of our ongoing safety monitoring, we would like to follow up on the adverse event report you submitted regarding {patient.drug_name}.

Original Report Details:
- Report Date: {patient.created_at.strftime('%B %d, %Y') if patient.created_at else 'N/A'}
- Medication: {patient.drug_name}
- Reported Symptoms: {patient.symptoms or 'Not specified'}

Your feedback is crucial for ensuring medication safety. Please complete our follow-up questionnaire by visiting:

{form_url}

This link will expire in 7 days.

Your information is kept confidential and secure.

---
This is an automated message from the Pharmacovigilance Safety Monitoring System.
If you did not submit a report or have questions, please contact your healthcare provider.
"""
        return text
    
    def send_followup_email(self, patient, followup_token: str = None) -> Dict[str, Any]:
        """
        Send a follow-up questionnaire email to the patient.
        
        Args:
            patient: Patient model object
            followup_token: Optional pre-generated token, will generate if not provided
            
        Returns:
            Dict with success status and details
        """
        # Validate email configuration
        if not self.is_email_configured():
            return {
                'success': False,
                'error': 'Email not configured. Please set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables.',
                'setup_required': True
            }
        
        # Validate patient has email
        if not patient.email:
            return {
                'success': False,
                'error': f'Patient {patient.id} does not have an email address on file.',
                'patient_id': patient.id
            }
        
        # Generate token if not provided
        if not followup_token:
            followup_token = self.generate_followup_token(patient.id)
        
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'📋 Follow-up Request: {patient.drug_name} Safety Monitoring'
            msg['From'] = self.email_config['email']
            msg['To'] = patient.email
            
            # Attach both plain text and HTML versions
            text_content = self.create_email_text(patient, followup_token)
            html_content = self.create_email_html(patient, followup_token)
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email via Gmail SMTP
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['email'], self.email_config['password'])
                server.send_message(msg)
            
            return {
                'success': True,
                'message': f'Follow-up email sent successfully to {patient.email}',
                'patient_id': patient.id,
                'token': followup_token,
                'sent_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'error': 'Gmail authentication failed. Please check your email and app password.',
                'help': 'Make sure you are using an App Password, not your regular Gmail password.'
            }
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'error': f'SMTP error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send email: {str(e)}'
            }
    
    def create_whatsapp_message(self, patient, followup_token: str) -> str:
        """Generate the WhatsApp message content with the follow-up form link"""
        form_url = f"{APP_BASE_URL}/followup/{patient.id}/{followup_token}"
        
        message = f"""📋 *Follow-up Request*
_Pharmacovigilance Safety Monitoring_

Dear *{patient.name}*,

We would like to follow up on your adverse event report regarding *{patient.drug_name}*.

📅 *Report Date:* {patient.created_at.strftime('%B %d, %Y') if patient.created_at else 'N/A'}
💊 *Medication:* {patient.drug_name}
📝 *Symptoms:* {patient.symptoms or 'Not specified'}

Please take a few minutes to complete our follow-up questionnaire:
👉 {form_url}

⏰ This link expires in 7 days.
🔒 Your information is kept confidential.

Reply *HELP* if you have questions or *STOP* to opt out.

_This is an automated message from the Pharmacovigilance Safety System._"""
        
        return message
    
    def send_followup_whatsapp(self, patient, followup_token: str = None) -> Dict[str, Any]:
        """
        Send a follow-up questionnaire via WhatsApp to the patient.
        
        Args:
            patient: Patient model object with phone number
            followup_token: Optional pre-generated token, will generate if not provided
            
        Returns:
            Dict with success status and details
        """
        # Validate WhatsApp configuration
        if not self.is_whatsapp_configured():
            return {
                'success': False,
                'error': 'WhatsApp not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM environment variables.',
                'setup_required': True
            }
        
        # Validate patient has phone number
        if not patient.phone:
            return {
                'success': False,
                'error': f'Patient {patient.id} does not have a phone number on file.',
                'patient_id': patient.id
            }
        
        # Ensure Twilio client is initialized
        if not self.twilio_client:
            return {
                'success': False,
                'error': 'Twilio client not initialized. Check your credentials.',
                'setup_required': True
            }
        
        # Generate token if not provided
        if not followup_token:
            followup_token = self.generate_followup_token(patient.id)
        
        try:
            # Format phone number for WhatsApp (needs to be in international format)
            phone = patient.phone.strip()
            if not phone.startswith('+'):
                # Assume Indian number if no country code
                if phone.startswith('0'):
                    phone = '+91' + phone[1:]
                elif len(phone) == 10:
                    phone = '+91' + phone
                else:
                    phone = '+' + phone
            
            # Create WhatsApp message
            message_body = self.create_whatsapp_message(patient, followup_token)
            
            # Send via Twilio
            message = self.twilio_client.messages.create(
                from_=self.twilio_config['whatsapp_from'],
                body=message_body,
                to=f'whatsapp:{phone}'
            )
            
            return {
                'success': True,
                'message': f'Follow-up WhatsApp sent successfully to {phone}',
                'patient_id': patient.id,
                'phone': phone,
                'message_sid': message.sid,
                'token': followup_token,
                'sent_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
            }
            
        except Exception as e:
            error_message = str(e)
            if 'unverified' in error_message.lower():
                return {
                    'success': False,
                    'error': f'WhatsApp number not verified. In Twilio Sandbox mode, the recipient must first message your Twilio number.',
                    'help': 'Ask the patient to send "join <sandbox-keyword>" to your Twilio WhatsApp number first.',
                    'phone': patient.phone
                }
            return {
                'success': False,
                'error': f'Failed to send WhatsApp: {error_message}',
                'phone': patient.phone
            }
    
    def send_followup_all_channels(self, patient, followup_token: str = None) -> Dict[str, Any]:
        """
        Send follow-up via all available channels (email and WhatsApp).
        
        Args:
            patient: Patient model object
            followup_token: Optional pre-generated token
            
        Returns:
            Dict with results from each channel
        """
        if not followup_token:
            followup_token = self.generate_followup_token(patient.id)
        
        results = {
            'patient_id': patient.id,
            'token': followup_token,
            'email': None,
            'whatsapp': None,
            'channels_sent': 0
        }
        
        # Try email if patient has email
        if patient.email:
            results['email'] = self.send_followup_email(patient, followup_token)
            if results['email'].get('success'):
                results['channels_sent'] += 1
        else:
            results['email'] = {'success': False, 'reason': 'no_email'}
        
        # Try WhatsApp if patient has phone
        if patient.phone:
            results['whatsapp'] = self.send_followup_whatsapp(patient, followup_token)
            if results['whatsapp'].get('success'):
                results['channels_sent'] += 1
        else:
            results['whatsapp'] = {'success': False, 'reason': 'no_phone'}
        
        results['success'] = results['channels_sent'] > 0
        
        return results
    
    def process_followup_response(self, patient, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the follow-up form response and update patient data.
        This will also recalculate the case scoring.
        
        Args:
            patient: Patient model object
            response_data: Dictionary containing form responses
            
        Returns:
            Dict with update status and new scoring
        """
        from pv_backend.services.case_scoring import evaluate_case, score_case, check_followup
        
        updates_made = []
        
        try:
            # Update symptom onset date if provided
            if response_data.get('symptom_onset_date'):
                patient.symptom_onset_date = datetime.strptime(
                    response_data['symptom_onset_date'], '%Y-%m-%d'
                )
                updates_made.append('symptom_onset_date')
            
            # Update symptom resolution date if provided
            if response_data.get('symptom_resolution_date'):
                patient.symptom_resolution_date = datetime.strptime(
                    response_data['symptom_resolution_date'], '%Y-%m-%d'
                )
                patient.has_clear_timeline = True
                updates_made.append('symptom_resolution_date')
            
            # Update doctor confirmation if they visited
            if response_data.get('doctor_visit') == 'Yes':
                patient.doctor_confirmed = True
                patient.doctor_confirmation_date = datetime.utcnow()
                updates_made.append('doctor_confirmed')
            
            # Update current status/severity
            if response_data.get('current_status'):
                status_mapping = {
                    'Fully Recovered': 'Recovered',
                    'Improving': 'Recovering',
                    'Same as before': 'Not recovered',
                    'Worsening': 'Not recovered',
                    'New symptoms appeared': 'Not recovered'
                }
                # Could add an outcome field update here
                updates_made.append('current_status')
            
            # Update severity based on response
            if response_data.get('current_severity'):
                severity_mapping = {
                    'None': 'Low',
                    'Mild': 'Low',
                    'Moderate': 'Medium',
                    'Severe': 'High'
                }
                patient.risk_level = severity_mapping.get(response_data['current_severity'], patient.risk_level)
                updates_made.append('risk_level')
            
            # Append additional symptoms
            if response_data.get('additional_symptoms') and response_data['additional_symptoms'].lower() != 'none':
                if patient.symptoms:
                    patient.symptoms = f"{patient.symptoms}\n\n[Follow-up {datetime.utcnow().strftime('%Y-%m-%d')}]: {response_data['additional_symptoms']}"
                else:
                    patient.symptoms = response_data['additional_symptoms']
                updates_made.append('symptoms')
            
            # Record follow-up response
            patient.followup_response_date = datetime.utcnow()
            patient.followup_responded = True
            updates_made.append('followup_response')
            
            # Store the scoring before recalculation
            old_score = patient.case_score
            old_followup_score = patient.followup_responsiveness_score
            
            # Recalculate case scoring (Steps 7-9)
            evaluate_case(patient)
            score_case(patient)
            check_followup(patient)
            
            # Calculate score improvement
            score_change = (patient.case_score or 0) - (old_score or 0)
            followup_score_change = (patient.followup_responsiveness_score or 0) - (old_followup_score or 0)
            
            return {
                'success': True,
                'message': 'Follow-up response processed successfully',
                'patient_id': patient.id,
                'updates_made': updates_made,
                'scoring': {
                    'previous_case_score': old_score,
                    'new_case_score': patient.case_score,
                    'score_change': score_change,
                    'previous_followup_score': old_followup_score,
                    'new_followup_score': patient.followup_responsiveness_score,
                    'followup_score_change': followup_score_change,
                    'strength_level': patient.strength_level,
                    'completeness_score': round(patient.completeness_score * 100, 1) if patient.completeness_score else 0,
                    'interpretation': patient.case_score_interpretation
                },
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing follow-up response: {str(e)}',
                'patient_id': patient.id
            }
    
    def send_bulk_followup(self, patients: list) -> Dict[str, Any]:
        """
        Send follow-up emails to multiple patients who need follow-up.
        
        Args:
            patients: List of Patient model objects
            
        Returns:
            Summary of sent emails
        """
        results = {
            'total': len(patients),
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for patient in patients:
            if not patient.email:
                results['skipped'] += 1
                results['details'].append({
                    'patient_id': patient.id,
                    'status': 'skipped',
                    'reason': 'No email address'
                })
                continue
            
            result = self.send_followup_email(patient)
            
            if result['success']:
                results['sent'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                'patient_id': patient.id,
                'status': 'sent' if result['success'] else 'failed',
                'message': result.get('message') or result.get('error')
            })
        
        return results


# Utility function for easy import
def create_followup_agent(db_session=None) -> FollowupAgent:
    """Factory function to create a FollowupAgent instance"""
    return FollowupAgent(db_session)


# Example usage and testing
if __name__ == '__main__':
    print("=" * 60)
    print("Follow-up Agent - Setup Guide")
    print("=" * 60)
    print("""
To use this agent, you need to configure Gmail SMTP:

1. ENABLE 2-FACTOR AUTHENTICATION:
   - Go to: https://myaccount.google.com/security
   - Enable 2-Step Verification

2. CREATE APP PASSWORD:
   - Go to: https://myaccount.google.com/apppasswords
   - Select 'Mail' and your device
   - Copy the 16-character password generated

3. SET ENVIRONMENT VARIABLES:
   
   Windows (PowerShell):
   $env:GMAIL_ADDRESS = "your-email@gmail.com"
   $env:GMAIL_APP_PASSWORD = "your-16-char-password"
   
   Windows (CMD):
   set GMAIL_ADDRESS=your-email@gmail.com
   set GMAIL_APP_PASSWORD=your-16-char-password
   
   Linux/Mac:
   export GMAIL_ADDRESS="your-email@gmail.com"
   export GMAIL_APP_PASSWORD="your-16-char-password"

4. ALTERNATIVELY, create a .env file:
   GMAIL_ADDRESS=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-16-char-password

5. TEST THE CONFIGURATION:
   python -c "from pv_backend.services.followup_agent import FollowupAgent; agent = FollowupAgent(); print('Configured:', agent.is_email_configured())"
""")
