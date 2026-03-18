from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, ChatbotSession
from services.chat_orchestrator import chat_orchestrator
from services.rag_service import rag_service
from utils.jwt_handler import token_required, get_current_user
from flask_jwt_extended import jwt_required, get_jwt_identity

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
    data = request.get_json() or {}
    
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
    
    # Build response with orchestrator (criteria + semantic RAG + fallback)
    history = session.get_conversation_history()
    orchestrated = chat_orchestrator.process_message(
      message=user_message,
      conversation_history=history,
      user_id=user_id,
      session_id=str(session.id),
      limit=10
    )

    llm_response = orchestrated.get('response', '')
    recommendations = orchestrated.get('recommendations', [])

    # Persist chat history in session table
    session.add_message('user', user_message)
    session.add_message('assistant', llm_response)
    session.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    # Prepare response
    response_data = {
        'response': llm_response,
        'session_id': session.id
    }
    
    if recommendations:
      response_data['recommendations'] = recommendations[:10]
    
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
    data = request.get_json() or {}
    
    if 'query' not in data or not data['query']:
        return jsonify({'error': 'Query is required'}), 400
    
    query = data['query']
    limit = data.get('limit', 10)
    
    if limit > 50:
        limit = 50
    
    search_result = chat_orchestrator.search_movies(query=query, limit=limit)
    unique_movies = search_result.get('movies', [])
    intent = search_result.get('intent', {})
    
    return jsonify({
        'query': query,
      'extracted_preferences': intent,
      'rag_enabled': rag_service.is_available(),
      'movies': unique_movies[:limit]
    }), 200


@chatbot_bp.route('/rag/status', methods=['GET'])
def rag_status():
  """Get RAG availability status"""
  return jsonify({
    'rag_available': rag_service.is_available()
  }), 200


@chatbot_bp.route('/rag/reindex', methods=['POST'])
def rag_reindex():
  """Rebuild semantic index from current database movies"""
  result = rag_service.rebuild_index()
  return jsonify(result), 200
