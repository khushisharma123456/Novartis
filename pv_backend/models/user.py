"""
User model for authentication and role-based access control.
Roles: DOCTOR, HOSPITAL, PHARMACY, ADMIN
Pharmacies must be verified entities before they can submit data.
"""
import enum
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class UserRole(enum.Enum):
    """
    User roles in the pharmacovigilance system.
    Each role has different permissions for data submission and access.
    """
    DOCTOR = 'doctor'
    HOSPITAL = 'hospital'
    PHARMACY = 'pharmacy'
    ADMIN = 'admin'


class User(db.Model):
    """
    User account for the PV system.
    
    PV Context:
    - Doctors and Hospitals can submit adverse event reports
    - Pharmacies submit dispensing/sale data (requires verification)
    - Admins manage the system and can override automated decisions
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Role-based access control
    role = db.Column(db.Enum(UserRole), nullable=False)
    
    # Profile information
    full_name = db.Column(db.String(255), nullable=False)
    organization = db.Column(db.String(255))  # Hospital name, clinic, pharmacy chain
    license_number = db.Column(db.String(100))  # Medical license for doctors
    
    # Pharmacy verification (CRITICAL for PV compliance)
    # Pharmacies must be verified before they can submit dispensing data
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps for audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    
    # Soft delete (NO HARD DELETES in PV systems)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    verified_by = db.relationship('User', remote_side=[id], backref='verified_users')
    
    def set_password(self, password):
        """Hash and set the user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the password against the hash."""
        return check_password_hash(self.password_hash, password)
    
    def can_submit(self):
        """
        Check if user can submit data to the PV system.
        Pharmacies require verification before submission.
        """
        if not self.is_active or self.is_deleted:
            return False
        if self.role == UserRole.PHARMACY:
            return self.is_verified
        return True
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role.value,
            'full_name': self.full_name,
            'organization': self.organization,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
