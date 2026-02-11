from flask import Blueprint, request, jsonify
from services.recommendation_engine import RecommendationEngine
from utils.jwt_handler import token_required, get_current_user
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

engine = RecommendationEngine()


@recommendations_bp.route('/user', methods=['GET'])
@token_required
def get_user_recommendations():
    """
    Get personalized recommendations for the current user
    ---
    tags:
      - Recommendations
    security:
      - Bearer: []
    parameters:
      - name: limit
        in: query
        type: integer
        default: 10
        description: Number of recommendations to return
    responses:
      200:
        description: List of recommended movies
        schema:
          type: object
          properties:
            recommendations:
              type: array
              items:
                type: object
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    limit = request.args.get('limit', 10, type=int)
    
    if limit > 50:
        limit = 50
    
    recommendations = engine.get_user_based_recommendations(user_id, limit)
    
    movies = [movie.to_dict(include_stats=True) for movie in recommendations]
    
    return jsonify({'recommendations': movies}), 200


@recommendations_bp.route('/category/<string:genre>', methods=['GET'])
def get_category_recommendations(genre):
    """
    Get recommendations for a specific genre
    ---
    tags:
      - Recommendations
    parameters:
      - name: genre
        in: path
        type: string
        required: true
        description: Genre name
      - name: limit
        in: query
        type: integer
        default: 10
        description: Number of recommendations to return
    responses:
      200:
        description: List of recommended movies in the genre
        schema:
          type: object
          properties:
            genre:
              type: string
            recommendations:
              type: array
              items:
                type: object
    """
    limit = request.args.get('limit', 10, type=int)
    
    if limit > 50:
        limit = 50
    
    # Check if user is authenticated (optional)
    user_id = None
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except:
        pass
    
    recommendations = engine.get_genre_based_recommendations(genre, user_id, limit)
    
    movies = [movie.to_dict(include_stats=True) for movie in recommendations]
    
    return jsonify({
        'genre': genre,
        'recommendations': movies
    }), 200


@recommendations_bp.route('/home', methods=['GET'])
def get_home_recommendations():
    """
    Get mixed recommendations for home page
    ---
    tags:
      - Recommendations
    parameters:
      - name: limit
        in: query
        type: integer
        default: 10
        description: Number of recommendations per section
    responses:
      200:
        description: Mixed recommendations
        schema:
          type: object
          properties:
            personalized:
              type: array
              items:
                type: object
            popular:
              type: array
              items:
                type: object
            trending:
              type: array
              items:
                type: object
    """
    limit = request.args.get('limit', 10, type=int)
    
    if limit > 50:
        limit = 50
    
    # Check if user is authenticated (optional)
    user_id = None
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except:
        pass
    
    recommendations = engine.get_home_recommendations(user_id, limit)
    
    result = {
        'personalized': [m.to_dict(include_stats=True) for m in recommendations['personalized']],
        'popular': [m.to_dict(include_stats=True) for m in recommendations['popular']],
        'trending': [m.to_dict(include_stats=True) for m in recommendations['trending']]
    }
    
    return jsonify(result), 200


@recommendations_bp.route('/similar/<int:movie_id>', methods=['GET'])
def get_similar_movies(movie_id):
    """
    Get movies similar to a given movie
    ---
    tags:
      - Recommendations
    parameters:
      - name: movie_id
        in: path
        type: integer
        required: true
        description: Movie ID
      - name: limit
        in: query
        type: integer
        default: 10
        description: Number of similar movies to return
    responses:
      200:
        description: List of similar movies
        schema:
          type: object
          properties:
            movie_id:
              type: integer
            similar_movies:
              type: array
              items:
                type: object
      404:
        description: Movie not found
    """
    limit = request.args.get('limit', 10, type=int)
    
    if limit > 50:
        limit = 50
    
    similar_movies = engine.get_similar_movies(movie_id, limit)
    
    if not similar_movies and similar_movies != []:
        return jsonify({'error': 'Movie not found'}), 404
    
    movies = [movie.to_dict(include_stats=True) for movie in similar_movies]
    
    return jsonify({
        'movie_id': movie_id,
        'similar_movies': movies
    }), 200
