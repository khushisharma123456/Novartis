"""
Medical Validation model - tracks medical review of cases.
Some cases require medical professional validation before reporting.
"""
import enum
from datetime import datetime
from . import db


class ValidationStatus(enum.Enum):
    """Status of medical validation."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    REQUIRES_CHANGES = 'requires_changes'


class MedicalValidation(db.Model):
    """
    Medical validation record for pharmacovigilance cases.
    
    PV Context:
    - Serious cases require medical professional review
    - Validation affects case status and reportability
    - Full audit trail is maintained
    """
    __tablename__ = 'medical_validations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to case
    case_id = db.Column(db.Integer, db.ForeignKey('case_master.id'), nullable=False, index=True)
    
    # Validation request
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    request_reason = db.Column(db.Text)
    
    # Assignment
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_at = db.Column(db.DateTime)
    
    # Status
    status = db.Column(db.Enum(ValidationStatus), default=ValidationStatus.PENDING)
    
    # Validation details
    validation_notes = db.Column(db.Text)
    medical_assessment = db.Column(db.Text)
    
    # Causality opinion
    causality_opinion = db.Column(db.String(50))  # certain, probable, possible, unlikely, unrelated
    causality_reasoning = db.Column(db.Text)
    
    # Seriousness assessment
    seriousness_confirmed = db.Column(db.Boolean)
    seriousness_criteria_confirmed = db.Column(db.JSON)
    
    # Recommendation
    recommendation = db.Column(db.String(50))  # report, monitor, no_action
    recommendation_details = db.Column(db.Text)
    
    # Completion
    completed_at = db.Column(db.DateTime)
    completed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    case = db.relationship('CaseMaster', backref='medical_validations')
    requested_by = db.relationship('User', foreign_keys=[requested_by_user_id])
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_user_id])
    completed_by = db.relationship('User', foreign_keys=[completed_by_user_id])
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'status': self.status.value if self.status else None,
            'causality_opinion': self.causality_opinion,
            'seriousness_confirmed': self.seriousness_confirmed,
            'recommendation': self.recommendation,
            'validation_notes': self.validation_notes,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
