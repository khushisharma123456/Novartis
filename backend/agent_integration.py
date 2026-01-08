"""
🔗 AGENT INTEGRATION MODULE
Connects DataQualityAgent and agentBackend.py to Flask backend
WITHOUT modifying their core code
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataQualityAgent import DataQualityAgent
from backend.models import db, Patient, Alert, User
from flask import current_app


# =============================================================================
# CALLBACK FUNCTIONS FOR DATA QUALITY AGENT
# =============================================================================

def create_dashboard_callback(app):
    """
    Factory function to create dashboard callback with Flask app context
    """
    def dashboard_callback(update_data):
        """
        Callback function that updates patient dashboard in database
        Called by DataQualityAgent when patient status changes
        
        Args:
            update_data: Dictionary with patient status update info
        """
        with app.app_context():
            try:
                patient_token = update_data['patient_token']
                
                # Find patient in database
                patient = Patient.query.get(patient_token)
                
                if not patient:
                    print(f"[DASHBOARD] Patient {patient_token} not found in database")
                    return False
                
                # Map agent risk levels to database risk levels
                risk_mapping = {
                    'LOW': 'Low',
                    'MEDIUM': 'Medium',
                    'HIGH': 'High'
                }
                
                # Update patient risk level
                patient.risk_level = risk_mapping.get(update_data['risk_level'], 'Medium')
                
                # Update patient symptoms with quality/status info
                status_update = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Agent Status: {update_data['status']}"
                if patient.symptoms:
                    patient.symptoms += status_update
                else:
                    patient.symptoms = status_update.strip()
                
                db.session.commit()
                
                print(f"[DASHBOARD] Updated patient {patient_token}: Status={update_data['status']}, Risk={patient.risk_level}")
                return True
                
            except Exception as e:
                print(f"[DASHBOARD ERROR] {e}")
                db.session.rollback()
                return False
    
    return dashboard_callback


def create_alert_callback(app):
    """
    Factory function to create alert callback with Flask app context
    """
    def alert_callback(alert_data):
        """
        Callback function that creates alerts in database
        Called by DataQualityAgent when risks are detected
        
        Args:
            alert_data: Dictionary with alert information
        """
        with app.app_context():
            try:
                # Map agent priorities to database severities
                priority_mapping = {
                    'urgent': 'Critical',
                    'high': 'High',
                    'medium': 'Medium',
                    'low': 'Low'
                }
                
                # Create alert in database
                # Get system user or first pharma user as sender
                system_user = User.query.filter_by(role='pharma').first()
                
                if not system_user:
                    print("[ALERT] No pharma user found to create alert")
                    return False
                
                new_alert = Alert(
                    drug_name=f"Patient {alert_data['patient_token']}",
                    message=f"{alert_data['message']}\nReason: {alert_data['reason']}\nAction: {alert_data['recommended_action']}",
                    severity=priority_mapping.get(alert_data['priority'], 'Medium'),
                    sender_id=system_user.id
                )
                
                db.session.add(new_alert)
                db.session.commit()
                
                print(f"[ALERT] Created {alert_data['priority']} alert for patient {alert_data['patient_token']}")
                return True
                
            except Exception as e:
                print(f"[ALERT ERROR] {e}")
                db.session.rollback()
                return False
    
    return alert_callback


# =============================================================================
# AGENT INITIALIZATION
# =============================================================================

def initialize_data_quality_agent(patient_token, app):
    """
    Initialize DataQualityAgent with database callbacks
    
    Args:
        patient_token: Patient ID to monitor
        app: Flask app instance for database context
        
    Returns:
        Configured DataQualityAgent instance
    """
    dashboard_cb = create_dashboard_callback(app)
    alert_cb = create_alert_callback(app)
    
    agent = DataQualityAgent(
        patient_token=patient_token,
        dashboard_callback=dashboard_cb,
        alert_callback=alert_cb
    )
    
    return agent


# =============================================================================
# PATIENT DATA PROCESSOR
# =============================================================================

def process_patient_with_agent(patient_id, app):
    """
    Process a patient's data through the DataQualityAgent
    
    Args:
        patient_id: Patient ID to process
        app: Flask app instance
        
    Returns:
        DataQualityReport or None if error
    """
    with app.app_context():
        try:
            # Get patient from database
            patient = Patient.query.get(patient_id)
            
            if not patient:
                print(f"[PROCESS] Patient {patient_id} not found")
                return None
            
            # Initialize agent
            agent = initialize_data_quality_agent(patient_id, app)
            
            # Convert database patient to agent format
            patient_data = {
                "patient_token": patient.id,
                "drug_name": patient.drug_name,
                "side_effects": [patient.symptoms] if patient.symptoms else [],
                "severity": patient.risk_level,  # Will be adjusted by agent
                "time_after_medication": "Unknown",
                "patient_confidence": "Medium",
                "previous_reactions": "See patient history",
                "currently_taking": patient.drug_name
            }
            
            # Load and process
            agent.load_patient_data(patient_data)
            report = agent.generate_quality_report()
            
            print(f"[PROCESS] Patient {patient_id} processed - Quality: {report['data_quality_level']}, Risk: {report['safety_risk_level']}")
            
            return report
            
        except Exception as e:
            print(f"[PROCESS ERROR] {e}")
            return None


# =============================================================================
# DOCTOR UPDATE HANDLER
# =============================================================================

def handle_doctor_correction(patient_id, field, old_value, new_value, doctor_id, notes, app):
    """
    Process doctor corrections through DataQualityAgent
    
    Args:
        patient_id: Patient ID
        field: Field being updated
        old_value: Previous value
        new_value: New value
        doctor_id: Doctor making the update
        notes: Doctor's notes
        app: Flask app instance
        
    Returns:
        Updated report or None
    """
    with app.app_context():
        try:
            # Get doctor info
            doctor = User.query.get(doctor_id)
            if not doctor:
                return None
            
            # Initialize agent
            agent = initialize_data_quality_agent(patient_id, app)
            
            # First load current patient data
            patient = Patient.query.get(patient_id)
            if not patient:
                return None
            
            patient_data = {
                "patient_token": patient.id,
                "drug_name": patient.drug_name,
                "side_effects": [patient.symptoms] if patient.symptoms else [],
                "severity": patient.risk_level,
                "time_after_medication": "Unknown",
                "patient_confidence": "Medium",
                "previous_reactions": "See patient history",
                "currently_taking": patient.drug_name
            }
            
            agent.load_patient_data(patient_data)
            
            # Create doctor update
            doctor_update = {
                "patient_token": patient_id,
                "updated_by": f"DR_{doctor.id}_{doctor.name.upper().replace(' ', '_')}",
                "field_updated": field,
                "old_value": old_value,
                "new_value": new_value,
                "doctor_notes": notes,
                "timestamp": datetime.now().isoformat(),
                "confidence_override": True
            }
            
            # Apply correction
            updated_report = agent.apply_doctor_update(doctor_update)
            
            print(f"[CORRECTION] Doctor {doctor.name} updated {field} for patient {patient_id}")
            
            return updated_report
            
        except Exception as e:
            print(f"[CORRECTION ERROR] {e}")
            return None


# =============================================================================
# WHATSAPP AGENT CONNECTION
# =============================================================================

def get_whatsapp_agent_url():
    """
    Get the URL for WhatsApp agent backend
    Usually runs separately on different port
    """
    return os.getenv('WHATSAPP_AGENT_URL', 'http://localhost:8000')


def trigger_whatsapp_followup(patient_id, app):
    """
    Trigger WhatsApp follow-up for a patient via agentBackend.py
    
    Args:
        patient_id: Patient ID to follow up with
        app: Flask app instance
        
    Returns:
        Success status
    """
    with app.app_context():
        try:
            import requests
            
            patient = Patient.query.get(patient_id)
            if not patient or not patient.phone:
                print(f"[WHATSAPP] Patient {patient_id} has no phone number")
                return False
            
            # Call agentBackend.py's /start-conversation endpoint
            whatsapp_url = get_whatsapp_agent_url()
            
            response = requests.post(
                f"{whatsapp_url}/start-conversation",
                json={
                    "patient_id": patient.id,
                    "patient_name": patient.name,
                    "phone_number": patient.phone,
                    "drug_name": patient.drug_name
                }
            )
            
            if response.status_code == 200:
                print(f"[WHATSAPP] Follow-up initiated for patient {patient_id}")
                return True
            else:
                print(f"[WHATSAPP] Failed to initiate follow-up: {response.text}")
                return False
                
        except Exception as e:
            print(f"[WHATSAPP ERROR] {e}")
            return False
