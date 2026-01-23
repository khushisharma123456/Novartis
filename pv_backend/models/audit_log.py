"""
Audit Log model - tracks ALL changes in the system.
CRITICAL for regulatory compliance - every action must be logged.
"""
import enum
from datetime import datetime
from . import db


class AuditAction(enum.Enum):
    """Types of auditable actions."""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'  # Soft delete only
    READ = 'read'      # For sensitive data access
    LOGIN = 'login'
    LOGOUT = 'logout'
    OVERRIDE = 'override'
    EXPORT = 'export'
    REPORT = 'report'


class AuditLog(db.Model):
    """
    Comprehensive audit log for the PV system.
    
    PV Context:
    - EVERY create/update MUST write to this log
    - Before and after states are stored for full traceability
    - NEVER delete audit records
    - Required for regulatory compliance (21 CFR Part 11, etc.)
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Action details
    action = db.Column(db.Enum(AuditAction), nullable=False)
    
    # Who performed the action
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    user_email = db.Column(db.String(255))  # Stored for historical reference
    user_role = db.Column(db.String(50))
    
    # What was affected
    entity_type = db.Column(db.String(100), nullable=False, index=True)  # Table/model name
    entity_id = db.Column(db.Integer, index=True)
    entity_identifier = db.Column(db.String(255))  # Human-readable identifier
    
    # State tracking (CRITICAL for compliance)
    state_before = db.Column(db.JSON)  # Full state before change
    state_after = db.Column(db.JSON)   # Full state after change
    changes = db.Column(db.JSON)       # Diff of what changed
    
    # Context
    action_reason = db.Column(db.Text)  # Why this action was taken
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.String(500))
    session_id = db.Column(db.String(255))
    
    # API request details
    request_method = db.Column(db.String(10))
    request_path = db.Column(db.String(500))
    request_id = db.Column(db.String(100))  # Unique request identifier
    
    # Timestamp (immutable)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # NO soft delete for audit logs - they are immutable
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    @classmethod
    def log(cls, action, user, entity_type, entity_id=None, 
            entity_identifier=None, state_before=None, state_after=None,
            changes=None, reason=None, request=None):
        """
        Create an audit log entry.
        
        PV Context:
        - This method should be called for EVERY data modification
        - State tracking enables full reconstruction of history
        """
        log_entry = cls(
            action=action,
            user_id=user.id if user else None,
            user_email=user.email if user else 'system',
            user_role=user.role.value if user and user.role else 'system',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_identifier=entity_identifier,
            state_before=state_before,
            state_after=state_after,
            changes=changes,
            action_reason=reason,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request and request.user_agent else None,
            request_method=request.method if request else None,
            request_path=request.path if request else None
        )
        db.session.add(log_entry)
        return log_entry
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'action': self.action.value if self.action else None,
            'user_email': self.user_email,
            'user_role': self.user_role,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_identifier': self.entity_identifier,
            'changes': self.changes,
            'action_reason': self.action_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
