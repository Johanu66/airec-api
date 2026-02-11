from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from models import db, TokenBlacklist


def token_required(fn):
    """Decorator to require valid JWT token"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        jti = get_jwt()['jti']
        
        # Check if token is blacklisted
        token = TokenBlacklist.query.filter_by(jti=jti).first()
        if token:
            return jsonify({'error': 'Token has been revoked'}), 401
        
        return fn(*args, **kwargs)
    return wrapper


def get_current_user():
    """Get current user ID from JWT token"""
    return get_jwt_identity()


def add_token_to_blacklist(jti):
    """Add token to blacklist"""
    blacklisted_token = TokenBlacklist(jti=jti)
    db.session.add(blacklisted_token)
    db.session.commit()
