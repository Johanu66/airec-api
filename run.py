import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask application
from app import app

# For running directly
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

