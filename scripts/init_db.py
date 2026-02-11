"""
Database initialization and management script

Usage:
    python scripts/init_db.py [command]

Commands:
    init    - Initialize database (create all tables)
    reset   - Drop all tables and recreate
    seed    - Add sample data for testing
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Movie, Rating, UserPreferences


def init_database(app):
    """Initialize database - create all tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")


def reset_database(app):
    """Drop all tables and recreate"""
    with app.app_context():
        print("WARNING: This will delete all data!")
        response = input("Are you sure? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return
        
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating tables...")
        db.create_all()
        
        print("Database reset completed!")


def seed_database(app):
    """Add sample data for testing"""
    with app.app_context():
        print("Seeding database with sample data...")
        
        # Create sample users
        users_data = [
            {
                'email': 'alice@example.com',
                'password': 'Password123',
                'nom': 'Smith',
                'prenom': 'Alice',
                'genres': ['Action', 'Sci-Fi']
            },
            {
                'email': 'bob@example.com',
                'password': 'Password123',
                'nom': 'Johnson',
                'prenom': 'Bob',
                'genres': ['Comedy', 'Drama']
            },
            {
                'email': 'charlie@example.com',
                'password': 'Password123',
                'nom': 'Williams',
                'prenom': 'Charlie',
                'genres': ['Horror', 'Thriller']
            }
        ]
        
        for user_data in users_data:
            existing = User.query.filter_by(email=user_data['email']).first()
            if not existing:
                user = User(
                    email=user_data['email'],
                    nom=user_data['nom'],
                    prenom=user_data['prenom']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                db.session.flush()
                
                # Add preferences
                prefs = UserPreferences(user_id=user.id)
                prefs.set_favorite_genres(user_data['genres'])
                db.session.add(prefs)
                
                print(f"Created user: {user.email}")
        
        db.session.commit()
        
        # Create sample movies
        movies_data = [
            {
                'id': 1,
                'title': 'The Shawshank Redemption',
                'genres': 'Drama',
                'release_year': 1994,
                'description': 'Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.'
            },
            {
                'id': 2,
                'title': 'The Godfather',
                'genres': 'Crime|Drama',
                'release_year': 1972,
                'description': 'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.'
            },
            {
                'id': 3,
                'title': 'The Dark Knight',
                'genres': 'Action|Crime|Drama',
                'release_year': 2008,
                'description': 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests.'
            },
            {
                'id': 4,
                'title': 'Pulp Fiction',
                'genres': 'Crime|Thriller',
                'release_year': 1994,
                'description': 'The lives of two mob hitmen, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.'
            },
            {
                'id': 5,
                'title': 'Forrest Gump',
                'genres': 'Comedy|Drama|Romance',
                'release_year': 1994,
                'description': 'The presidencies of Kennedy and Johnson, the Vietnam War, and other historical events unfold from the perspective of an Alabama man.'
            }
        ]
        
        for movie_data in movies_data:
            existing = Movie.query.get(movie_data['id'])
            if not existing:
                movie = Movie(**movie_data)
                db.session.add(movie)
                print(f"Created movie: {movie.title}")
        
        db.session.commit()
        
        # Create sample ratings
        print("Creating sample ratings...")
        
        users = User.query.all()
        movies = Movie.query.all()
        
        sample_ratings = [
            (1, 1, 5.0),
            (1, 2, 4.5),
            (1, 3, 4.0),
            (2, 2, 5.0),
            (2, 4, 4.5),
            (2, 5, 4.0),
            (3, 3, 5.0),
            (3, 4, 4.5),
        ]
        
        for user_id, movie_id, rating_val in sample_ratings:
            existing = Rating.query.filter_by(
                user_id=user_id,
                movie_id=movie_id
            ).first()
            
            if not existing:
                rating = Rating(
                    user_id=user_id,
                    movie_id=movie_id,
                    rating=rating_val
                )
                db.session.add(rating)
        
        db.session.commit()
        
        print("\n" + "="*50)
        print("Database seeded successfully!")
        print(f"Created {len(users_data)} users")
        print(f"Created {len(movies_data)} movies")
        print(f"Created {len(sample_ratings)} ratings")
        print("\nSample credentials:")
        for user_data in users_data:
            print(f"  Email: {user_data['email']}, Password: {user_data['password']}")


def main():
    parser = argparse.ArgumentParser(description='Database management')
    parser.add_argument(
        'command',
        choices=['init', 'reset', 'seed'],
        help='Command to execute'
    )
    
    args = parser.parse_args()
    
    # Create app
    app = create_app()
    
    # Execute command
    if args.command == 'init':
        init_database(app)
    elif args.command == 'reset':
        reset_database(app)
    elif args.command == 'seed':
        seed_database(app)


if __name__ == '__main__':
    main()
