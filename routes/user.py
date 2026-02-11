from flask import Blueprint, request, jsonify
from models import db, User, UserPreferences, Rating
from utils.jwt_handler import token_required, get_current_user
from utils.validators import validate_pagination, sanitize_string

user_bp = Blueprint('user', __name__, url_prefix='/api/user')


@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """
    Get current user profile
    ---
    tags:
      - User
    security:
      - Bearer: []
    responses:
      200:
        description: User profile
        schema:
          type: object
      401:
        description: Unauthorized
      404:
        description: User not found
    """
    user_id = get_current_user()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    profile = user.to_dict(include_ratings=True)
    
    # Get recent ratings
    recent_ratings = Rating.query.filter_by(user_id=user_id).order_by(
        Rating.timestamp.desc()
    ).limit(10).all()
    
    profile['recent_ratings'] = [r.to_dict(include_movie=True) for r in recent_ratings]
    
    return jsonify(profile), 200


@user_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """
    Update user profile
    ---
    tags:
      - User
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
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
      200:
        description: Profile updated successfully
      400:
        description: Invalid input
      401:
        description: Unauthorized
      404:
        description: User not found
    """
    user_id = get_current_user()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update name fields if provided
    if 'nom' in data:
        nom = sanitize_string(data['nom'], max_length=100)
        if nom:
            user.nom = nom
    
    if 'prenom' in data:
        prenom = sanitize_string(data['prenom'], max_length=100)
        if prenom:
            user.prenom = prenom
    
    # Update preferences if provided
    if 'favorite_genres' in data:
        preferences = UserPreferences.query.filter_by(user_id=user_id).first()
        
        if not preferences:
            preferences = UserPreferences(user_id=user_id)
            db.session.add(preferences)
        
        if isinstance(data['favorite_genres'], list):
            preferences.set_favorite_genres(data['favorite_genres'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict(include_ratings=True)
    }), 200


@user_bp.route('/ratings', methods=['GET'])
@token_required
def get_user_ratings():
    """
    Get all ratings by the current user
    ---
    tags:
      - User
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: List of user ratings
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 20)
    
    valid, message, page, per_page = validate_pagination(page, per_page)
    if not valid:
        return jsonify({'error': message}), 400
    
    pagination = Rating.query.filter_by(user_id=user_id).order_by(
        Rating.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    ratings = [rating.to_dict(include_movie=True) for rating in pagination.items]
    
    return jsonify({
        'ratings': ratings,
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages
    }), 200


@user_bp.route('/preferences', methods=['GET'])
@token_required
def get_preferences():
    """
    Get user preferences
    ---
    tags:
      - User
    security:
      - Bearer: []
    responses:
      200:
        description: User preferences
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    preferences = UserPreferences.query.filter_by(user_id=user_id).first()
    
    if not preferences:
        return jsonify({'favorite_genres': []}), 200
    
    return jsonify(preferences.to_dict()), 200


@user_bp.route('/preferences', methods=['PUT'])
@token_required
def update_preferences():
    """
    Update user preferences
    ---
    tags:
      - User
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            favorite_genres:
              type: array
              items:
                type: string
              example: ["Action", "Comedy", "Sci-Fi"]
    responses:
      200:
        description: Preferences updated
      400:
        description: Invalid input
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    data = request.get_json()
    
    if 'favorite_genres' not in data or not isinstance(data['favorite_genres'], list):
        return jsonify({'error': 'favorite_genres must be an array'}), 400
    
    preferences = UserPreferences.query.filter_by(user_id=user_id).first()
    
    if not preferences:
        preferences = UserPreferences(user_id=user_id)
        db.session.add(preferences)
    
    preferences.set_favorite_genres(data['favorite_genres'])
    db.session.commit()
    
    return jsonify({
        'message': 'Preferences updated successfully',
        'preferences': preferences.to_dict()
    }), 200
