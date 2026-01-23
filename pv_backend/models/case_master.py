"""
Case Master model - the living record for a drug-person combination.
Cases evolve over time as more experience events are linked to them.
"""
from datetime import datetime
from . import db


class CaseMaster(db.Model):
    """
    Case Master - central record for pharmacovigilance case management.
    
    PV Context:
    - A case represents a DRUG + PERSON combination
    - Multiple experience events can belong to one case
    - The case score evolves over time (never overwritten, historized)
    - Cases are the unit of regulatory reporting
    """
    __tablename__ = 'case_master'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Case identifier (human-readable unique ID)
    case_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Drug-Person combination (the key for case linking)
    drug_name_normalized = db.Column(db.String(255), nullable=False, index=True)
    drug_active_ingredient = db.Column(db.String(255))
    patient_identifier_hash = db.Column(db.String(255), nullable=False, index=True)
    
    # Current score (latest score from score history)
    # Range: -2 to +2
    current_score = db.Column(db.Float, default=0.0)
    
    # Case status
    status = db.Column(db.String(50), default='open')  # open, closed, under_review, reported
    
    # Priority based on score and severity
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    
    # First and latest event dates
    first_event_date = db.Column(db.DateTime)
    latest_event_date = db.Column(db.DateTime)
    
    # Event count
    event_count = db.Column(db.Integer, default=0)
    
    # Seriousness criteria (for regulatory reporting)
    is_serious = db.Column(db.Boolean, default=False)
    seriousness_criteria = db.Column(db.JSON)  # death, hospitalization, disability, etc.
    
    # Regulatory reporting
    is_reportable = db.Column(db.Boolean, default=False)
    reported_to = db.Column(db.JSON)  # List of agencies reported to
    report_date = db.Column(db.DateTime)
    
    # Medical review
    requires_medical_review = db.Column(db.Boolean, default=False)
    medical_review_status = db.Column(db.String(50))  # pending, in_progress, completed
    
    # Follow-up status
    has_pending_followup = db.Column(db.Boolean, default=False)
    
    # Assigned to (case owner)
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    assigned_to = db.relationship('User', backref='assigned_cases')
    
    def update_event_count(self):
        """Update the event count for this case."""
        from .experience_event import ExperienceEvent
        self.event_count = ExperienceEvent.query.filter_by(
            case_id=self.id,
            is_deleted=False
        ).count()
    
    def determine_priority(self):
        """
        Determine case priority based on score and seriousness.
        
        PV Context:
        - Critical: Serious AE with strong evidence (score <= -2)
        - High: AE with moderate evidence (score < 0)
        - Normal: Unclear or mixed evidence (score == 0)
        - Low: Positive experience (score > 0)
        """
        if self.is_serious and self.current_score <= -1:
            self.priority = 'critical'
        elif self.current_score <= -1:
            self.priority = 'high'
        elif self.current_score < 0:
            self.priority = 'normal'
        else:
            self.priority = 'low'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'case_number': self.case_number,
            'drug_name_normalized': self.drug_name_normalized,
            'current_score': self.current_score,
            'status': self.status,
            'priority': self.priority,
            'is_serious': self.is_serious,
            'event_count': self.event_count,
            'has_pending_followup': self.has_pending_followup,
            'first_event_date': self.first_event_date.isoformat() if self.first_event_date else None,
            'latest_event_date': self.latest_event_date.isoformat() if self.latest_event_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
