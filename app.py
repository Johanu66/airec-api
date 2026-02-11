from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flasgger import Swagger
from config import config
from models import db
from services.llm_service import llm_service

# Import blueprints
from routes.auth import auth_bp
from routes.movies import movies_bp
from routes.categories import categories_bp
from routes.user import user_bp
from routes.ratings import ratings_bp
from routes.recommendations import recommendations_bp
from routes.chatbot import chatbot_bp


def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    jwt = JWTManager(app)
    migrate = Migrate(app, db)
    
    # Initialize LLM service
    llm_service.initialize(
        app.config['LLM_API_KEY'],
        app.config['LLM_API_URL'],
        app.config['LLM_MODEL']
    )
    
    # Swagger configuration
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/swagger/"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": app.config['API_TITLE'],
            "description": app.config['API_DESCRIPTION'],
            "version": app.config['API_VERSION'],
            "contact": {
                "name": "AiRec API",
                "url": "https://github.com/your-repo/airec-api"
            }
        },
        "host": "airec-api.randever.com",
        "basePath": "/",
        "schemes": ["https", "http"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
            }
        },
        "tags": [
            {"name": "Authentication", "description": "User authentication endpoints"},
            {"name": "User", "description": "User profile management"},
            {"name": "Movies", "description": "Movie browsing and details"},
            {"name": "Categories", "description": "Movie genres and categories"},
            {"name": "Ratings", "description": "User movie ratings"},
            {"name": "Recommendations", "description": "Movie recommendation system"},
            {"name": "Chatbot", "description": "AI-powered movie chatbot"}
        ]
    }
    
    Swagger(app, config=swagger_config, template=swagger_template)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(movies_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(ratings_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(chatbot_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400
    
    # JWT error handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return jsonify({'error': 'Missing or invalid authorization token'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'name': 'AiRec API',
            'version': app.config['API_VERSION'],
            'description': app.config['API_DESCRIPTION'],
            'documentation': '/swagger/'
        }), 200
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({'status': 'healthy'}), 200
    
    # Database initialization
    with app.app_context():
        db.create_all()
    
    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
