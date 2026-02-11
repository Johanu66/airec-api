from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, ChatbotSession, Movie
from services.llm_service import llm_service
from utils.jwt_handler import token_required, get_current_user
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')


@chatbot_bp.route('/query', methods=['POST'])
def chatbot_query():
    """
    Send a query to the chatbot
    ---
    tags:
      - Chatbot
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - message
          properties:
            message:
              type: string
              example: "I'm looking for a fun action movie"
            session_id:
              type: integer
              description: Optional session ID to continue conversation
    responses:
      200:
        description: Chatbot response
        schema:
          type: object
          properties:
            response:
              type: string
            session_id:
              type: integer
            recommendations:
              type: array
              items:
                type: object
      400:
        description: Invalid input
    """
    data = request.get_json()
    
    if 'message' not in data or not data['message']:
        return jsonify({'error': 'Message is required'}), 400
    
    user_message = data['message']
    session_id = data.get('session_id')
    
    # Get user_id if authenticated
    user_id = None
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except:
        pass
    
    # Get or create session
    session = None
    if session_id:
        session = ChatbotSession.query.get(session_id)
    
    if not session:
        session = ChatbotSession(user_id=user_id)
        db.session.add(session)
        db.session.flush()
    
    # Add user message to history
    session.add_message('user', user_message)
    
    # Extract preferences from message
    preferences = llm_service.extract_movie_preferences(user_message)
    
    # Get movie recommendations based on extracted preferences
    movie_recommendations = []
    if preferences.get('genres'):
        # Get movies from mentioned genres
        from services.recommendation_engine import RecommendationEngine
        engine = RecommendationEngine()
        
        for genre in preferences['genres'][:2]:  # Limit to 2 genres
            genre_movies = engine.get_genre_based_recommendations(
                genre, user_id, limit=5
            )
            movie_recommendations.extend(genre_movies)
    
    # Build context about available movies
    movie_context = ""
    if movie_recommendations:
        movie_context = "Some relevant movies from our database:\n"
        for movie in movie_recommendations[:5]:
            movie_context += f"- {movie.title} ({movie.release_year}): {', '.join(movie.get_genres_list())}\n"
    
    # Get conversation history for context
    history = session.get_conversation_history()
    messages = []
    
    # Add recent conversation history (last 5 messages)
    for msg in history[-5:]:
        if msg['role'] in ['user', 'assistant']:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
    
    # Generate LLM response
    llm_response = llm_service.get_movie_recommendations_from_prompt(
        user_message,
        movie_context
    )
    
    # Add assistant response to history
    session.add_message('assistant', llm_response)
    session.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    # Prepare response
    response_data = {
        'response': llm_response,
        'session_id': session.id
    }
    
    if movie_recommendations:
        response_data['recommendations'] = [
            m.to_dict(include_stats=True) for m in movie_recommendations[:10]
        ]
    
    return jsonify(response_data), 200


@chatbot_bp.route('/history', methods=['GET'])
@token_required
def get_chatbot_history():
    """
    Get chatbot conversation history for current user
    ---
    tags:
      - Chatbot
    security:
      - Bearer: []
    parameters:
      - name: session_id
        in: query
        type: integer
        description: Optional specific session ID
    responses:
      200:
        description: Conversation history
        schema:
          type: object
          properties:
            sessions:
              type: array
              items:
                type: object
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    
    session_id = request.args.get('session_id', type=int)
    
    if session_id:
        # Get specific session
        session = ChatbotSession.query.filter_by(
            id=session_id,
            user_id=user_id
        ).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify(session.to_dict()), 200
    else:
        # Get all user sessions
        sessions = ChatbotSession.query.filter_by(
            user_id=user_id
        ).order_by(ChatbotSession.updated_at.desc()).all()
        
        return jsonify({
            'sessions': [s.to_dict() for s in sessions]
        }), 200


@chatbot_bp.route('/session/<int:session_id>', methods=['DELETE'])
@token_required
def delete_session(session_id):
    """
    Delete a chatbot session
    ---
    tags:
      - Chatbot
    security:
      - Bearer: []
    parameters:
      - name: session_id
        in: path
        type: integer
        required: true
        description: Session ID to delete
    responses:
      200:
        description: Session deleted
      403:
        description: Not authorized
      404:
        description: Session not found
      401:
        description: Unauthorized
    """
    user_id = get_current_user()
    
    session = ChatbotSession.query.get(session_id)
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    if session.user_id != user_id:
        return jsonify({'error': 'Not authorized to delete this session'}), 403
    
    db.session.delete(session)
    db.session.commit()
    
    return jsonify({'message': 'Session deleted successfully'}), 200


@chatbot_bp.route('/search', methods=['POST'])
def search_movies_by_description():
    """
    Search movies based on natural language description
    ---
    tags:
      - Chatbot
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - query
          properties:
            query:
              type: string
              example: "movies about space exploration"
            limit:
              type: integer
              default: 10
    responses:
      200:
        description: Search results
        schema:
          type: object
          properties:
            query:
              type: string
            movies:
              type: array
              items:
                type: object
      400:
        description: Invalid input
    """
    data = request.get_json()
    
    if 'query' not in data or not data['query']:
        return jsonify({'error': 'Query is required'}), 400
    
    query = data['query']
    limit = data.get('limit', 10)
    
    if limit > 50:
        limit = 50
    
    # Extract preferences from query
    preferences = llm_service.extract_movie_preferences(query)
    
    # Search movies based on extracted preferences
    movies = []
    
    if preferences.get('genres'):
        from services.recommendation_engine import RecommendationEngine
        engine = RecommendationEngine()
        
        for genre in preferences['genres']:
            genre_movies = engine.get_genre_based_recommendations(
                genre, None, limit=limit
            )
            movies.extend(genre_movies)
    
    # Remove duplicates
    seen = set()
    unique_movies = []
    for movie in movies:
        if movie.id not in seen:
            seen.add(movie.id)
            unique_movies.append(movie)
    
    # If no movies found, return popular movies
    if not unique_movies:
        from services.recommendation_engine import RecommendationEngine
        engine = RecommendationEngine()
        unique_movies = engine.get_popular_movies(limit)
    
    return jsonify({
        'query': query,
        'extracted_preferences': preferences,
        'movies': [m.to_dict(include_stats=True) for m in unique_movies[:limit]]
    }), 200
