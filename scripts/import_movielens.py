"""
Script to import MovieLens dataset into the database

Download the MovieLens dataset from:
https://grouplens.org/datasets/movielens/

This script expects:
- movies.csv (or movies.dat)
- ratings.csv (or ratings.dat)

Usage:
    python import_movielens.py --movies movies.csv --ratings ratings.csv
"""

import sys
import os
import csv
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Movie, Rating, User


def parse_movielens_movies(file_path, file_format='csv'):
    """Parse MovieLens movies file"""
    movies = []
    
    if file_format == 'csv':
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extract year from title if present
                title = row['title']
                year = None
                
                # MovieLens format: "Movie Title (YEAR)"
                if '(' in title and ')' in title:
                    try:
                        year_str = title[title.rfind('(')+1:title.rfind(')')]
                        if year_str.isdigit():
                            year = int(year_str)
                            title = title[:title.rfind('(')].strip()
                    except:
                        pass
                
                movies.append({
                    'id': int(row['movieId']),
                    'title': title,
                    'genres': row['genres'] if row['genres'] != '(no genres listed)' else None,
                    'release_year': year
                })
    else:  # dat format
        with open(file_path, 'r', encoding='latin-1') as f:
            for line in f:
                parts = line.strip().split('::')
                if len(parts) >= 3:
                    movie_id, title, genres = parts[0], parts[1], parts[2]
                    
                    # Extract year
                    year = None
                    if '(' in title and ')' in title:
                        try:
                            year_str = title[title.rfind('(')+1:title.rfind(')')]
                            if year_str.isdigit():
                                year = int(year_str)
                                title = title[:title.rfind('(')].strip()
                        except:
                            pass
                    
                    movies.append({
                        'id': int(movie_id),
                        'title': title,
                        'genres': genres if genres != '(no genres listed)' else None,
                        'release_year': year
                    })
    
    return movies


def parse_movielens_ratings(file_path, file_format='csv', limit=None):
    """Parse MovieLens ratings file"""
    ratings = []
    
    if file_format == 'csv':
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                
                ratings.append({
                    'user_id': int(row['userId']),
                    'movie_id': int(row['movieId']),
                    'rating': float(row['rating']),
                    'timestamp': datetime.fromtimestamp(int(row['timestamp']))
                })
    else:  # dat format
        with open(file_path, 'r', encoding='latin-1') as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                
                parts = line.strip().split('::')
                if len(parts) >= 4:
                    user_id, movie_id, rating, timestamp = parts
                    ratings.append({
                        'user_id': int(user_id),
                        'movie_id': int(movie_id),
                        'rating': float(rating),
                        'timestamp': datetime.fromtimestamp(int(timestamp))
                    })
    
    return ratings


def import_movies(app, movies_data):
    """Import movies into database"""
    with app.app_context():
        print(f"Importing {len(movies_data)} movies...")
        
        batch_size = 1000
        for i in range(0, len(movies_data), batch_size):
            batch = movies_data[i:i+batch_size]
            
            for movie_data in batch:
                # Check if movie already exists
                existing = Movie.query.get(movie_data['id'])
                if not existing:
                    movie = Movie(
                        id=movie_data['id'],
                        title=movie_data['title'],
                        genres=movie_data['genres'],
                        release_year=movie_data['release_year']
                    )
                    db.session.add(movie)
            
            db.session.commit()
            print(f"Imported {min(i+batch_size, len(movies_data))}/{len(movies_data)} movies")
        
        print("Movies import completed!")


def import_ratings(app, ratings_data):
    """Import ratings into database"""
    with app.app_context():
        print(f"Importing {len(ratings_data)} ratings...")
        
        # First, create users for unique user_ids
        unique_user_ids = set(r['user_id'] for r in ratings_data)
        print(f"Creating {len(unique_user_ids)} users...")
        
        for user_id in unique_user_ids:
            existing = User.query.get(user_id)
            if not existing:
                user = User(
                    id=user_id,
                    email=f"user{user_id}@movielens.import",
                    nom=f"User{user_id}",
                    prenom="MovieLens"
                )
                user.set_password("changeme123")
                db.session.add(user)
        
        db.session.commit()
        print("Users created!")
        
        # Now import ratings
        batch_size = 5000
        for i in range(0, len(ratings_data), batch_size):
            batch = ratings_data[i:i+batch_size]
            
            for rating_data in batch:
                # Check if rating already exists
                existing = Rating.query.filter_by(
                    user_id=rating_data['user_id'],
                    movie_id=rating_data['movie_id']
                ).first()
                
                if not existing:
                    # Verify movie exists
                    movie = Movie.query.get(rating_data['movie_id'])
                    if movie:
                        rating = Rating(
                            user_id=rating_data['user_id'],
                            movie_id=rating_data['movie_id'],
                            rating=rating_data['rating'],
                            timestamp=rating_data['timestamp']
                        )
                        db.session.add(rating)
            
            db.session.commit()
            print(f"Imported {min(i+batch_size, len(ratings_data))}/{len(ratings_data)} ratings")
        
        print("Ratings import completed!")


def main():
    parser = argparse.ArgumentParser(description='Import MovieLens dataset')
    parser.add_argument('--movies', required=True, help='Path to movies file (csv or dat)')
    parser.add_argument('--ratings', required=True, help='Path to ratings file (csv or dat)')
    parser.add_argument('--format', default='csv', choices=['csv', 'dat'], help='File format')
    parser.add_argument('--limit-ratings', type=int, help='Limit number of ratings to import')
    
    args = parser.parse_args()
    
    # Create app
    app = create_app()
    
    # Parse files
    print("Parsing movies file...")
    movies_data = parse_movielens_movies(args.movies, args.format)
    
    print("Parsing ratings file...")
    ratings_data = parse_movielens_ratings(args.ratings, args.format, args.limit_ratings)
    
    # Import data
    import_movies(app, movies_data)
    import_ratings(app, ratings_data)
    
    print("\nImport completed successfully!")
    print(f"Total movies: {len(movies_data)}")
    print(f"Total ratings: {len(ratings_data)}")


if __name__ == '__main__':
    main()
