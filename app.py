from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flasgger import Swagger
import logging
import os
from logging.handlers import RotatingFileHandler
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


def setup_logging(app, environment='development'):
    """Configure application logging"""
    # Create logs directory if it doesn't exist
    log_dir = app.config.get('LOG_DIR')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set log level
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    app.logger.setLevel(log_level)
    
    # Remove default handlers
    app.logger.handlers.clear()
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        app.config.get('LOG_FILE'),
        maxBytes=app.config.get('LOG_MAX_BYTES'),
        backupCount=app.config.get('LOG_BACKUP_COUNT')
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(app.config.get('LOG_FORMAT'))
    file_handler.setFormatter(file_formatter)
    app.logger.addHandler(file_handler)
    
    # Console handler for development
    if app.config.get('DEBUG'):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        app.logger.addHandler(console_handler)
    
    # Log startup
    app.logger.info('='*50)
    app.logger.info('AiRec API Starting')
    app.logger.info(f'Environment: {environment}')
    app.logger.info(f'Log Level: {app.config.get("LOG_LEVEL")}')
    app.logger.info(f'Log File: {app.config.get("LOG_FILE")}')
    app.logger.info('='*50)


def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Setup logging
    setup_logging(app, config_name)
    
    # Initialize extensions
    app.logger.info('Initializing database...')
    db.init_app(app)
    
    app.logger.info('Configuring CORS...')
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    
    app.logger.info('Initializing JWT...')
    jwt = JWTManager(app)
    
    app.logger.info('Setting up database migrations...')
    migrate = Migrate(app, db)
    
    # Initialize LLM service
    app.logger.info('Initializing LLM service...')
    llm_service.initialize(
        app.config['LLM_API_KEY'],
        app.config['LLM_API_URL'],
        app.config['LLM_MODEL']
    )
    if app.config['LLM_API_KEY']:
        app.logger.info(f'LLM configured with model: {app.config["LLM_MODEL"]}')
    else:
        app.logger.warning('LLM API key not configured')
    
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
    
    app.logger.info('Configuring Swagger documentation...')
    Swagger(app, config=swagger_config, template=swagger_template)
    
    # Register blueprints
    app.logger.info('Registering blueprints...')
    app.register_blueprint(auth_bp)
    app.register_blueprint(movies_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(ratings_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(chatbot_bp)
    app.logger.info('All blueprints registered successfully')
    
    # Request logging
    @app.before_request
    def log_request():
        app.logger.debug(f'{request.method} {request.path} - IP: {request.remote_addr}')
    
    @app.after_request
    def log_response(response):
        app.logger.debug(f'{request.method} {request.path} - Status: {response.status_code}')
        return response
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f'404 Not Found: {request.path} - IP: {request.remote_addr}')
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500 Internal Server Error: {str(error)} - Path: {request.path}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f'400 Bad Request: {request.path} - {str(error)}')
        return jsonify({'error': 'Bad request'}), 400
    
    # JWT error handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        app.logger.warning(f'Unauthorized access attempt: {request.path} - IP: {request.remote_addr}')
        return jsonify({'error': 'Missing or invalid authorization token'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        app.logger.warning(f'Invalid token used: {request.path} - Error: {error}')
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.info(f'Expired token used: {request.path} - User ID: {jwt_payload.get("sub")}')
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
    app.logger.info('Initializing database tables...')
    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Database tables initialized successfully')
        except Exception as e:
            app.logger.error(f'Database initialization failed: {str(e)}', exc_info=True)
    
    app.logger.info('Application initialization complete')
    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.logger.info(f'Starting Flask development server on port {port}')
    app.logger.info(f'Debug mode: {debug}')
    app.run(host='0.0.0.0', port=port, debug=debug)
