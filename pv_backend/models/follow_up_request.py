"""
Follow-Up Request model - tracks required follow-ups for incomplete data.
Follow-ups are triggered when scoring engine detects data gaps.
"""
import enum
from datetime import datetime
from . import db


class FollowUpStatus(enum.Enum):
    """Status of the follow-up request."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class FollowUpReason(enum.Enum):
    """
    Reason for the follow-up request.
    
    PV Context:
    - Follow-ups improve data quality and case strength
    - Specific questions are generated based on missing data
    """
    SCORE_ZERO = 'score_zero'           # Score is 0 (unclear data)
    LOW_STRENGTH = 'low_strength'       # AE polarity but strength < 2
    MISSING_FIELDS = 'missing_fields'   # Mandatory fields missing
    CLARIFICATION = 'clarification'     # Need clarification on existing data
    OUTCOME_UPDATE = 'outcome_update'   # Need outcome information
    CAUSALITY = 'causality'             # Need causality information


class FollowUpRequest(db.Model):
    """
    Follow-up request for pharmacovigilance data collection.
    
    PV Context:
    - Triggered automatically by scoring engine
    - Can be handled by AI agents or human staff
    - Responses create new experience events
    """
    __tablename__ = 'follow_up_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to case and event
    case_id = db.Column(db.Integer, db.ForeignKey('case_master.id'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('experience_events.id'), index=True)
    
    # Follow-up reason
    reason = db.Column(db.Enum(FollowUpReason), nullable=False)
    reason_details = db.Column(db.Text)
    
    # Questions to ask
    questions = db.Column(db.JSON)  # List of specific questions
    missing_fields = db.Column(db.JSON)  # List of missing field names
    
    # Target for follow-up
    target_reporter_id = db.Column(db.Integer, db.ForeignKey('reporters.id'))
    target_contact = db.Column(db.String(255))  # Email or phone (hashed)
    
    # Status
    status = db.Column(db.Enum(FollowUpStatus), default=FollowUpStatus.PENDING)
    
    # Assignment
    assigned_to_type = db.Column(db.String(50))  # 'ai_agent', 'human'
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Scheduling
    scheduled_at = db.Column(db.DateTime)
    due_by = db.Column(db.DateTime)
    
    # Attempt tracking
    attempt_count = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    last_attempt_at = db.Column(db.DateTime)
    
    # Response (if completed)
    response_event_id = db.Column(db.Integer, db.ForeignKey('experience_events.id'))
    response_summary = db.Column(db.Text)
    
    # Completion
    completed_at = db.Column(db.DateTime)
    completed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Priority
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    case = db.relationship('CaseMaster', backref='follow_up_requests')
    event = db.relationship('ExperienceEvent', foreign_keys=[event_id], backref='follow_ups')
    target_reporter = db.relationship('Reporter', backref='follow_up_requests')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_user_id], backref='assigned_followups')
    response_event = db.relationship('ExperienceEvent', foreign_keys=[response_event_id])
    completed_by = db.relationship('User', foreign_keys=[completed_by_user_id])
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'event_id': self.event_id,
            'reason': self.reason.value if self.reason else None,
            'reason_details': self.reason_details,
            'questions': self.questions,
            'missing_fields': self.missing_fields,
            'status': self.status.value if self.status else None,
            'priority': self.priority,
            'attempt_count': self.attempt_count,
            'due_by': self.due_by.isoformat() if self.due_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
