"""
Experience Event model - the core submission unit in the PV system.
Every submission from doctors, hospitals, pharmacies, or AI agents creates an event.
"""
import enum
from datetime import datetime
from . import db


class EventSource(enum.Enum):
    """
    Source of the experience event.
    Different sources have different data completeness expectations.
    """
    DOCTOR = 'doctor'           # Clinical observation with medical context
    HOSPITAL = 'hospital'       # Institutional report, often more detailed
    PHARMACY = 'pharmacy'       # Sale/dispensing data, minimal clinical info
    AI_FOLLOWUP = 'ai_followup' # AI agent follow-up response
    PATIENT = 'patient'         # Direct patient report (rare)


class ExperienceEvent(db.Model):
    """
    Raw experience event submission.
    
    PV Context:
    - This is the PRIMARY input record for all PV data
    - Every submission creates an event, even if it's a duplicate
    - Events are NEVER deleted, only soft-deleted
    - Idempotency is ensured via idempotency_key
    """
    __tablename__ = 'experience_events'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Idempotency key to prevent duplicate submissions
    # Format: {source}_{reporter_id}_{drug_id}_{timestamp_hash}
    idempotency_key = db.Column(db.String(255), unique=True, index=True)
    
    # Source and reporter
    source = db.Column(db.Enum(EventSource), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('reporters.id'), index=True)
    submitted_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Drug information
    drug_name = db.Column(db.String(255), nullable=False, index=True)
    drug_code = db.Column(db.String(100))  # NDC, ATC code, etc.
    drug_batch = db.Column(db.String(100))  # Batch/lot number if available
    
    # Patient identifier (ALWAYS HASHED for privacy)
    patient_identifier_hash = db.Column(db.String(255), index=True)
    
    # Event details
    indication = db.Column(db.Text)  # Why was the drug prescribed/taken
    dosage = db.Column(db.String(100))
    route_of_administration = db.Column(db.String(50))  # oral, IV, topical, etc.
    
    # Dates
    start_date = db.Column(db.Date)  # When drug was started
    end_date = db.Column(db.Date)    # When drug was stopped (if applicable)
    event_date = db.Column(db.Date)  # When the event/observation occurred
    
    # Observed events (free text, will be normalized)
    observed_events = db.Column(db.Text)  # What happened - symptoms, reactions, etc.
    
    # Outcome (if known)
    outcome = db.Column(db.Text)  # Recovered, ongoing, fatal, unknown
    
    # Pharmacy-specific fields
    quantity_dispensed = db.Column(db.Integer)  # For pharmacy sales
    prescriber_info = db.Column(db.String(255))  # Prescriber name/ID if available
    
    # Raw submission data (JSON blob for audit/debug)
    raw_payload = db.Column(db.JSON)
    
    # Processing status
    is_processed = db.Column(db.Boolean, default=False)
    processed_at = db.Column(db.DateTime)
    
    # Link to case (populated after case linking)
    case_id = db.Column(db.Integer, db.ForeignKey('case_master.id'), index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete (CRITICAL: never hard delete PV data)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    reporter = db.relationship('Reporter', backref='events')
    submitted_by = db.relationship('User', backref='submitted_events')
    case = db.relationship('CaseMaster', backref='events')
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'source': self.source.value,
            'drug_name': self.drug_name,
            'drug_code': self.drug_code,
            'indication': self.indication,
            'observed_events': self.observed_events,
            'outcome': self.outcome,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'case_id': self.case_id,
            'is_processed': self.is_processed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
