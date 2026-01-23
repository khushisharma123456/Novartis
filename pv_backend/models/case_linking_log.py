"""
Case Linking Log model - tracks case linking decisions.
Documents why events were linked to specific cases.
"""
from datetime import datetime
from . import db


class CaseLinkingLog(db.Model):
    """
    Log of case linking decisions.
    
    PV Context:
    - Case linking is CRITICAL for accurate pharmacovigilance
    - Links events to existing cases or creates new ones
    - Confidence score helps assess linking quality
    - Enables review and override of automated decisions
    """
    __tablename__ = 'case_linking_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # The event being linked
    event_id = db.Column(db.Integer, db.ForeignKey('experience_events.id'), nullable=False, index=True)
    
    # The case it was linked to (or created)
    case_id = db.Column(db.Integer, db.ForeignKey('case_master.id'), nullable=False, index=True)
    
    # Linking decision
    is_new_case = db.Column(db.Boolean, default=False)  # Was a new case created?
    
    # Confidence in the linking decision (0.0 to 1.0)
    confidence = db.Column(db.Float, nullable=False)
    
    # Linking criteria used
    linking_criteria = db.Column(db.JSON)  # What factors were considered
    # Example: {"patient_match": true, "drug_match": true, "time_window": "30_days"}
    
    # Matching details
    patient_identifier_matched = db.Column(db.Boolean)
    drug_matched = db.Column(db.Boolean)
    time_window_days = db.Column(db.Integer)  # Days between events
    
    # Alternative cases considered
    alternative_cases = db.Column(db.JSON)  # List of other potential case matches
    
    # Linking method
    linked_by = db.Column(db.String(50))  # 'auto', 'manual', 'ai'
    linking_algorithm_version = db.Column(db.String(20))
    
    # Human override
    is_overridden = db.Column(db.Boolean, default=False)
    override_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    override_reason = db.Column(db.Text)
    override_at = db.Column(db.DateTime)
    original_case_id = db.Column(db.Integer)  # Case before override
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    event = db.relationship('ExperienceEvent', backref='linking_log', uselist=False)
    case = db.relationship('CaseMaster', backref='linking_logs')
    override_by = db.relationship('User', backref='case_linking_overrides')
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'case_id': self.case_id,
            'is_new_case': self.is_new_case,
            'confidence': self.confidence,
            'linking_criteria': self.linking_criteria,
            'linked_by': self.linked_by,
            'is_overridden': self.is_overridden,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
