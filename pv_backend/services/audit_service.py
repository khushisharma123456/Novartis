"""
Audit Service for the Pharmacovigilance system.
Centralized audit logging for compliance.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from flask import request as flask_request

from pv_backend.models import db, AuditLog, AuditAction, User


class AuditService:
    """
    Service for comprehensive audit logging.
    
    PV Context:
    - EVERY create/update MUST be logged
    - Before and after states are stored
    - Required for regulatory compliance (21 CFR Part 11)
    - Audit logs are IMMUTABLE
    """
    
    @staticmethod
    def get_state_dict(entity) -> Optional[Dict]:
        """
        Get dictionary representation of an entity.
        
        Args:
            entity: SQLAlchemy model instance
        
        Returns:
            Dictionary or None
        """
        if entity is None:
            return None
        
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        
        # Fallback: try to serialize common attributes
        try:
            return {c.name: getattr(entity, c.name) 
                    for c in entity.__table__.columns
                    if not c.name.startswith('_')}
        except:
            return {'id': getattr(entity, 'id', None)}
    
    @staticmethod
    def compute_changes(before: Dict, after: Dict) -> Dict:
        """
        Compute the differences between before and after states.
        
        Args:
            before: State before change
            after: State after change
        
        Returns:
            Dictionary of changed fields with old and new values
        """
        if not before:
            return {'_action': 'created', 'new_state': after}
        
        if not after:
            return {'_action': 'deleted', 'old_state': before}
        
        changes = {}
        all_keys = set(list(before.keys()) + list(after.keys()))
        
        for key in all_keys:
            old_val = before.get(key)
            new_val = after.get(key)
            
            if old_val != new_val:
                changes[key] = {
                    'old': old_val,
                    'new': new_val
                }
        
        return changes
    
    @classmethod
    def log_create(cls,
                   user: User,
                   entity_type: str,
                   entity_id: int,
                   entity_identifier: str,
                   state_after: Dict,
                   reason: str = None,
                   request=None) -> AuditLog:
        """
        Log a CREATE action.
        
        PV Context:
        - All entity creations must be logged
        - Full state is captured
        """
        return AuditLog.log(
            action=AuditAction.CREATE,
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_identifier=entity_identifier,
            state_before=None,
            state_after=state_after,
            changes={'_action': 'created'},
            reason=reason,
            request=request or flask_request
        )
    
    @classmethod
    def log_update(cls,
                   user: User,
                   entity_type: str,
                   entity_id: int,
                   entity_identifier: str,
                   state_before: Dict,
                   state_after: Dict,
                   reason: str = None,
                   request=None) -> AuditLog:
        """
        Log an UPDATE action.
        
        PV Context:
        - All entity updates must be logged
        - Before and after states are captured
        - Changes are computed automatically
        """
        changes = cls.compute_changes(state_before, state_after)
        
        return AuditLog.log(
            action=AuditAction.UPDATE,
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_identifier=entity_identifier,
            state_before=state_before,
            state_after=state_after,
            changes=changes,
            reason=reason,
            request=request or flask_request
        )
    
    @classmethod
    def log_delete(cls,
                   user: User,
                   entity_type: str,
                   entity_id: int,
                   entity_identifier: str,
                   state_before: Dict,
                   reason: str = None,
                   request=None) -> AuditLog:
        """
        Log a DELETE action (soft delete).
        
        PV Context:
        - PV systems use SOFT DELETE only
        - The final state shows is_deleted = True
        """
        state_after = state_before.copy() if state_before else {}
        state_after['is_deleted'] = True
        state_after['deleted_at'] = datetime.utcnow().isoformat()
        
        return AuditLog.log(
            action=AuditAction.DELETE,
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_identifier=entity_identifier,
            state_before=state_before,
            state_after=state_after,
            changes={'is_deleted': {'old': False, 'new': True}},
            reason=reason,
            request=request or flask_request
        )
    
    @classmethod
    def log_override(cls,
                     user: User,
                     entity_type: str,
                     entity_id: int,
                     entity_identifier: str,
                     state_before: Dict,
                     state_after: Dict,
                     reason: str,
                     request=None) -> AuditLog:
        """
        Log an OVERRIDE action (human override of automated decision).
        
        PV Context:
        - Human overrides are specially tracked
        - Reason is MANDATORY for overrides
        """
        if not reason:
            raise ValueError('Reason is required for override actions')
        
        changes = cls.compute_changes(state_before, state_after)
        changes['_override'] = True
        
        return AuditLog.log(
            action=AuditAction.OVERRIDE,
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_identifier=entity_identifier,
            state_before=state_before,
            state_after=state_after,
            changes=changes,
            reason=f'OVERRIDE: {reason}',
            request=request or flask_request
        )
    
    @classmethod
    def get_entity_history(cls,
                          entity_type: str,
                          entity_id: int,
                          limit: int = 100) -> list:
        """
        Get audit history for a specific entity.
        
        Args:
            entity_type: Type of entity (e.g., 'CaseMaster')
            entity_id: ID of the entity
            limit: Maximum records to return
        
        Returns:
            List of AuditLog records, newest first
        """
        return AuditLog.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
