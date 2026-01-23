"""
Reporter model - represents the source of an experience event.
Can be a doctor, hospital staff, pharmacist, or patient (via AI follow-up).
"""
from datetime import datetime
from . import db


class Reporter(db.Model):
    """
    Reporter information for pharmacovigilance events.
    
    PV Context:
    - Reporters are essential for follow-up and clarification
    - Contact information must be stored securely
    - Reporter qualification affects data credibility/strength
    """
    __tablename__ = 'reporters'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to user account (if reporter is a system user)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    
    # Reporter details (may differ from user account)
    reporter_type = db.Column(db.String(50), nullable=False)  # doctor, nurse, pharmacist, patient, caregiver
    full_name = db.Column(db.String(255))
    
    # Contact for follow-up (hashed/encrypted in production)
    email = db.Column(db.String(255))
    phone_hash = db.Column(db.String(255))  # Hashed phone number
    
    # Qualification (affects data strength in scoring)
    qualification = db.Column(db.String(100))  # MD, PharmD, RN, etc.
    institution = db.Column(db.String(255))
    
    # Consent for follow-up
    consent_to_contact = db.Column(db.Boolean, default=False)
    consent_date = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='reporter_profiles')
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'reporter_type': self.reporter_type,
            'full_name': self.full_name,
            'qualification': self.qualification,
            'institution': self.institution,
            'consent_to_contact': self.consent_to_contact,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
