from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt
from models import db, User, UserPreferences
from utils.validators import validate_email_format, validate_password_strength, sanitize_string
from utils.jwt_handler import token_required, add_token_to_blacklist

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
            - nom
            - prenom
          properties:
            email:
              type: string
              example: "user@example.com"
            password:
              type: string
              example: "Password123"
            nom:
              type: string
              example: "Doe"
            prenom:
              type: string
              example: "John"
            favorite_genres:
              type: array
              items:
                type: string
              example: ["Action", "Comedy"]
    responses:
      201:
        description: User registered successfully
      400:
        description: Invalid input
      409:
        description: Email already exists
    """
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ['email', 'password', 'nom', 'prenom']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate email
    email_valid, email_or_error = validate_email_format(data['email'])
    if not email_valid:
        return jsonify({'error': f'Invalid email: {email_or_error}'}), 400
    
    # Validate password
    password_valid, password_message = validate_password_strength(data['password'])
    if not password_valid:
        return jsonify({'error': password_message}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=email_or_error).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    # Sanitize input
    nom = sanitize_string(data['nom'], max_length=100)
    prenom = sanitize_string(data['prenom'], max_length=100)
    
    if not nom or not prenom:
        return jsonify({'error': 'Name fields cannot be empty'}), 400
    
    # Create new user
    user = User(
        email=email_or_error,
        nom=nom,
        prenom=prenom
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.flush()  # Get user.id
    
    # Create user preferences if provided
    if 'favorite_genres' in data and data['favorite_genres']:
        preferences = UserPreferences(user_id=user.id)
        preferences.set_favorite_genres(data['favorite_genres'])
        db.session.add(preferences)
    
    db.session.commit()
    
    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: "user@example.com"
            password:
              type: string
              example: "Password123"
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
            user:
              type: object
      401:
        description: Invalid credentials
      400:
        description: Missing required fields
    """
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Missing email or password'}), 400
    
    # Find user
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Create tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(include_ratings=True)
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    User logout
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Logout successful
      401:
        description: Unauthorized
    """
    jti = get_jwt()['jti']
    add_token_to_blacklist(jti)
    
    return jsonify({'message': 'Successfully logged out'}), 200


@auth_bp.route('/refresh', methods=['POST'])
@token_required
def refresh():
    """
    Refresh access token
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Token refreshed
        schema:
          type: object
          properties:
            access_token:
              type: string
      401:
        description: Unauthorized
    """
    from flask_jwt_extended import get_jwt_identity
    current_user = get_jwt_identity()
    new_token = create_access_token(identity=current_user)
    
    return jsonify({'access_token': new_token}), 200
