"""
JWT Authentication utilities for the Pharmacovigilance system.
Handles token generation, validation, and role-based access control.
"""
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, g

from pv_backend.models import db, User, UserRole, AuditLog, AuditAction


def generate_token(user, token_type='access'):
    """
    Generate a JWT token for authenticated user.
    
    Args:
        user: User object
        token_type: 'access' or 'refresh'
    
    Returns:
        JWT token string
    """
    if token_type == 'access':
        expires = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=8))
    else:
        expires = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))
    
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role.value,
        'is_verified': user.is_verified,
        'token_type': token_type,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expires
    }
    
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )


def decode_token(token):
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """
    Decorator to require a valid JWT token for an endpoint.
    
    PV Context:
    - All PV endpoints require authentication
    - Token contains user role for authorization
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid authorization header format'
                }), 401
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Authentication token is required'
            }), 401
        
        payload = decode_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token'
            }), 401
        
        if payload.get('token_type') != 'access':
            return jsonify({
                'success': False,
                'message': 'Invalid token type'
            }), 401
        
        # Get user from database
        user = User.query.get(payload['user_id'])
        if not user or user.is_deleted or not user.is_active:
            return jsonify({
                'success': False,
                'message': 'User account is inactive or deleted'
            }), 401
        
        # Store user in flask g object for access in endpoint
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated


def roles_required(*roles):
    """
    Decorator to require specific roles for an endpoint.
    
    Args:
        roles: UserRole enum values that are allowed
    
    PV Context:
    - Different roles have different permissions
    - Pharmacies must be verified to submit data
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = g.get('current_user')
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required'
                }), 401
            
            # Check if user's role is in allowed roles
            allowed_roles = [r if isinstance(r, UserRole) else UserRole(r) for r in roles]
            if user.role not in allowed_roles:
                return jsonify({
                    'success': False,
                    'message': f'Access denied. Required roles: {[r.value for r in allowed_roles]}'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def verified_pharmacy_required(f):
    """
    Decorator to require verified pharmacy status.
    
    PV Context:
    - Pharmacies must be verified before they can submit dispensing data
    - This ensures data quality and prevents unauthorized submissions
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = g.get('current_user')
        if not user:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
        
        if user.role == UserRole.PHARMACY and not user.is_verified:
            return jsonify({
                'success': False,
                'message': 'Pharmacy verification required before submitting data'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f):
    """
    Decorator to require admin role.
    
    PV Context:
    - Admins can override automated decisions
    - Admins can verify pharmacies
    - Admins have full system access
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = g.get('current_user')
        if not user:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
        
        if user.role != UserRole.ADMIN:
            return jsonify({
                'success': False,
                'message': 'Admin access required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated
