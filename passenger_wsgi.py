import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask application
from app import app as application

# This is the WSGI application callable that Passenger will use
