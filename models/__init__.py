from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    ratings = db.relationship('Rating', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    preferences = db.relationship('UserPreferences', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_ratings=False):
        """Convert user object to dictionary"""
        data = {
            'id': self.id,
            'email': self.email,
            'nom': self.nom,
            'prenom': self.prenom,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_ratings:
            data['ratings_count'] = self.ratings.count()
            data['preferences'] = self.preferences.to_dict() if self.preferences else None
            
        return data
    
    def __repr__(self):
        return f'<User {self.email}>'


class Movie(db.Model):
    """Movie model based on MovieLens dataset"""
    __tablename__ = 'movies'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    genres = db.Column(db.String(255), nullable=True)  # Pipe-separated genres
    release_year = db.Column(db.Integer, nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    poster_url = db.Column(db.String(500), nullable=True)
    backdrop_url = db.Column(db.String(500), nullable=True)
    tmdb_id = db.Column(db.Integer, nullable=True)
    imdb_id = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ratings = db.relationship('Rating', backref='movie', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_genres_list(self):
        """Return genres as a list"""
        if self.genres:
            return [g.strip() for g in self.genres.split('|')]
        return []
    
    def get_average_rating(self):
        """Calculate average rating for this movie"""
        ratings = self.ratings.all()
        if not ratings:
            return 0.0
        return sum(r.rating for r in ratings) / len(ratings)
    
    def get_ratings_count(self):
        """Get total number of ratings"""
        return self.ratings.count()
    
    def to_dict(self, include_stats=False):
        """Convert movie object to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'genres': self.get_genres_list(),
            'release_year': self.release_year,
            'description': self.description,
            'poster_url': self.poster_url,
            'backdrop_url': self.backdrop_url,
            'tmdb_id': self.tmdb_id,
            'imdb_id': self.imdb_id
        }
        
        if include_stats:
            data['average_rating'] = round(self.get_average_rating(), 2)
            data['ratings_count'] = self.get_ratings_count()
            
        return data
    
    def __repr__(self):
        return f'<Movie {self.title}>'


class Rating(db.Model):
    """Rating model for user movie ratings"""
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False, index=True)
    rating = db.Column(db.Float, nullable=False)  # 0.5 to 5.0
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Unique constraint: one rating per user per movie
    __table_args__ = (
        db.UniqueConstraint('user_id', 'movie_id', name='unique_user_movie_rating'),
    )
    
    def to_dict(self, include_movie=False, include_user=False):
        """Convert rating object to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'rating': self.rating,
            'timestamp': self.timestamp.isoformat()
        }
        
        if include_movie and self.movie:
            data['movie'] = self.movie.to_dict()
        
        if include_user and self.user:
            data['user'] = {
                'id': self.user.id,
                'nom': self.user.nom,
                'prenom': self.user.prenom
            }
            
        return data
    
    def __repr__(self):
        return f'<Rating user={self.user_id} movie={self.movie_id} rating={self.rating}>'


class UserPreferences(db.Model):
    """User preferences for personalized recommendations"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    favorite_genres = db.Column(db.Text, nullable=True)  # JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_favorite_genres(self):
        """Return favorite genres as a list"""
        if self.favorite_genres:
            try:
                return json.loads(self.favorite_genres)
            except:
                return []
        return []
    
    def set_favorite_genres(self, genres_list):
        """Set favorite genres from a list"""
        self.favorite_genres = json.dumps(genres_list)
    
    def to_dict(self):
        """Convert preferences object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'favorite_genres': self.get_favorite_genres(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<UserPreferences user={self.user_id}>'


class ChatbotSession(db.Model):
    """Chatbot conversation sessions"""
    __tablename__ = 'chatbot_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    conversation_history = db.Column(db.Text, nullable=True)  # JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_conversation_history(self):
        """Return conversation history as a list"""
        if self.conversation_history:
            try:
                return json.loads(self.conversation_history)
            except:
                return []
        return []
    
    def set_conversation_history(self, history_list):
        """Set conversation history from a list"""
        self.conversation_history = json.dumps(history_list)
    
    def add_message(self, role, content):
        """Add a message to the conversation history"""
        history = self.get_conversation_history()
        history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.set_conversation_history(history)
    
    def to_dict(self):
        """Convert session object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'conversation_history': self.get_conversation_history(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ChatbotSession id={self.id} user={self.user_id}>'


# Blacklist for JWT tokens (logout)
class TokenBlacklist(db.Model):
    """Store blacklisted JWT tokens"""
    __tablename__ = 'token_blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<TokenBlacklist {self.jti}>'
