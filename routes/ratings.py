from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, Rating, Movie
from utils.jwt_handler import token_required, get_current_user
from utils.validators import validate_rating

ratings_bp = Blueprint('ratings', __name__, url_prefix='/api/movies')


@ratings_bp.route('/<int:movie_id>/ratings', methods=['POST'])
@token_required
def create_or_update_rating(movie_id):
    """
    Create or update a rating for a movie
    ---
    tags:
      - Ratings
    security:
      - Bearer: []
    parameters:
      - name: movie_id
        in: path
        type: integer
        required: true
        description: Movie ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - rating
          properties:
            rating:
              type: number
              minimum: 0.5
              maximum: 5.0
              example: 4.5
              description: Rating value (0.5 to 5.0 in 0.5 increments)
    responses:
      201:
        description: Rating created
      200:
        description: Rating updated
      400:
        description: Invalid rating
      404:
        description: Movie not found
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    
    # Check if movie exists
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404
    
    data = request.get_json()
    
    if 'rating' not in data:
        return jsonify({'error': 'Rating is required'}), 400
    
    # Validate rating
    valid, message = validate_rating(data['rating'])
    if not valid:
        return jsonify({'error': message}), 400
    
    # Check if rating already exists
    existing_rating = Rating.query.filter_by(
        user_id=user_id,
        movie_id=movie_id
    ).first()
    
    if existing_rating:
        # Update existing rating
        existing_rating.rating = data['rating']
        existing_rating.timestamp = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Rating updated successfully',
            'rating': existing_rating.to_dict(include_movie=True)
        }), 200
    else:
        # Create new rating
        new_rating = Rating(
            user_id=user_id,
            movie_id=movie_id,
            rating=data['rating'],
            timestamp=datetime.utcnow()
        )
        db.session.add(new_rating)
        db.session.commit()
        
        return jsonify({
            'message': 'Rating created successfully',
            'rating': new_rating.to_dict(include_movie=True)
        }), 201


@ratings_bp.route('/<int:movie_id>/ratings/<int:rating_id>', methods=['DELETE'])
@token_required
def delete_rating(movie_id, rating_id):
    """
    Delete a rating
    ---
    tags:
      - Ratings
    security:
      - Bearer: []
    parameters:
      - name: movie_id
        in: path
        type: integer
        required: true
        description: Movie ID
      - name: rating_id
        in: path
        type: integer
        required: true
        description: Rating ID
    responses:
      200:
        description: Rating deleted
      403:
        description: Not authorized to delete this rating
      404:
        description: Rating not found
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    
    rating = Rating.query.get(rating_id)
    
    if not rating or rating.movie_id != movie_id:
        return jsonify({'error': 'Rating not found'}), 404
    
    # Check if rating belongs to current user
    if rating.user_id != user_id:
        return jsonify({'error': 'Not authorized to delete this rating'}), 403
    
    db.session.delete(rating)
    db.session.commit()
    
    return jsonify({'message': 'Rating deleted successfully'}), 200


@ratings_bp.route('/<int:movie_id>/ratings/user', methods=['GET'])
@token_required
def get_user_movie_rating(movie_id):
    """
    Get current user's rating for a specific movie
    ---
    tags:
      - Ratings
    security:
      - Bearer: []
    parameters:
      - name: movie_id
        in: path
        type: integer
        required: true
        description: Movie ID
    responses:
      200:
        description: User's rating for the movie
      404:
        description: Rating not found
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    
    rating = Rating.query.filter_by(
        user_id=user_id,
        movie_id=movie_id
    ).first()
    
    if not rating:
        return jsonify({'error': 'Rating not found'}), 404
    
    return jsonify(rating.to_dict(include_movie=True)), 200
