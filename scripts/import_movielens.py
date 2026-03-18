"""
Script to import MovieLens dataset into the database

Download the MovieLens dataset from:
https://grouplens.org/datasets/movielens/

This script supports MovieLens 1M dataset with .dat files:
- movies.dat (MovieID::Title::Genres)
- ratings.dat (UserID::MovieID::Rating::Timestamp)
- users.dat (UserID::Gender::Age::Occupation::Zip-code)

Usage:
    python scripts/import_movielens.py /path/to/ml-1m/
    or
    python scripts/import_movielens.py --movies movies.dat --ratings ratings.dat --users users.dat
"""

import sys
import os
import csv
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Movie, Rating, User, Genre, movie_genres


def clear_existing_data(app):
    """Clear all imported data from database"""
    with app.app_context():
        print("WARNING: This will delete all MovieLens data!")
        response = input("Continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return False
        
        print("Clearing existing data...")
        
        # Delete in correct order to avoid foreign key constraints
        Rating.query.delete()
        print("  - Cleared ratings")
        
        # Clear movie-genre associations
        db.session.execute(movie_genres.delete())
        print("  - Cleared movie-genre associations")
        
        Movie.query.delete()
        print("  - Cleared movies")
        
        Genre.query.delete()
        print("  - Cleared genres")
        
        # Only delete imported users, not real users
        User.query.filter_by(is_imported=True).delete()
        print("  - Cleared imported users")
        
        db.session.commit()
        print("Data cleared successfully!")
        return True


def parse_movielens_movies(file_path):
    """Parse MovieLens movies file (expects .dat format with :: delimiter)"""
    movies = []
    
    print(f"Reading movies from {file_path}...")
    with open(file_path, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.strip().split('::')
            if len(parts) >= 3:
                movie_id, title, genres = parts[0], parts[1], parts[2]
                
                # Extract year from title - MovieLens format: "Movie Title (YEAR)"
                year = None
                if '(' in title and ')' in title:
                    try:
                        year_str = title[title.rfind('(')+1:title.rfind(')')]
                        if year_str.isdigit() and len(year_str) == 4:
                            year = int(year_str)
                            title = title[:title.rfind('(')].strip()
                    except:
                        pass
                
                movies.append({
                    'id': int(movie_id),
                    'title': title,
                    'genres': genres.split('|') if genres and genres != '(no genres listed)' else [],
                    'release_year': year
                })
    
    return movies


def parse_movielens_users(file_path):
    """Parse MovieLens users file (expects .dat format with :: delimiter)"""
    users = []
    
    print(f"Reading users from {file_path}...")
    with open(file_path, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.strip().split('::')
            if len(parts) >= 5:
                user_id, gender, age, occupation, zipcode = parts
                users.append({
                    'id': int(user_id),
                    'gender': gender,
                    'age': age,
                    'occupation': occupation,
                    'zipcode': zipcode
                })
    
    return users


def parse_movielens_ratings(file_path, limit=None):
    """Parse MovieLens ratings file (expects .dat format with :: delimiter)
    
    Note: MovieLens 1M uses 1-5 whole star ratings, which are compatible with
    the API's 0.5-5.0 scale (in 0.5 increments)
    """
    ratings = []
    
    print(f"Reading ratings from {file_path}...")
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
                    'rating': float(rating),  # 1-5 whole star ratings
                    'timestamp': datetime.fromtimestamp(int(timestamp))
                })
    
    return ratings


def import_genres(app, movies_data):
    """Import unique genres from movies data"""
    with app.app_context():
        # Extract all unique genres
        all_genres = set()
        for movie in movies_data:
            all_genres.update(movie['genres'])
        
        # Remove empty strings
        all_genres.discard('')
        all_genres = sorted(all_genres)
        
        print(f"Importing {len(all_genres)} genres...")
        
        genre_map = {}
        for genre_name in all_genres:
            # Check if genre already exists
            genre = Genre.query.filter_by(name=genre_name).first()
            if not genre:
                genre = Genre(name=genre_name)
                db.session.add(genre)
            genre_map[genre_name] = genre
        
        db.session.commit()
        print(f"Genres imported: {', '.join(all_genres)}")
        
        return genre_map


def import_movies(app, movies_data, genre_map):
    """Import movies into database with genre relationships"""
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
                        release_year=movie_data['release_year']
                    )
                    
                    # Add genre relationships
                    for genre_name in movie_data['genres']:
                        if genre_name in genre_map:
                            movie.genres_list.append(genre_map[genre_name])
                    
                    db.session.add(movie)
            
            db.session.commit()
            print(f"Imported {min(i+batch_size, len(movies_data))}/{len(movies_data)} movies")
        
        print("Movies import completed!")


def import_users(app, users_data):
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


def import_users(app, users_data):
    """Import users into database"""
    with app.app_context():
        print(f"Importing {len(users_data)} users...")
        
        # Check how many users already exist
        existing_count = User.query.count()
        if existing_count > 0:
            print(f"Found {existing_count} existing users, skipping user import...")
            return
        
        # Bulk insert users in batches
        # Note: Using raw password hash to speed up import
        # Password hash for "MovieLens123!" generated once
        from werkzeug.security import generate_password_hash
        common_password_hash = generate_password_hash("MovieLens123!")
        
        batch_size = 1000
        for i in range(0, len(users_data), batch_size):
            batch = users_data[i:i+batch_size]
            users_to_add = []
            
            for user_data in batch:
                user = User(
                    id=user_data['id'],
                    email=f"user{user_data['id']}@movielens.import",
                    password_hash=common_password_hash,  # Use pre-computed hash
                    nom="User",
                    prenom=f"{user_data['id']}",
                    is_imported=True  # Mark as imported MovieLens user
                )
                users_to_add.append(user)
            
            db.session.bulk_save_objects(users_to_add)
            db.session.commit()
            print(f"Imported {min(i+batch_size, len(users_data))}/{len(users_data)} users")
        
        print("Users import completed!")


def import_ratings(app, ratings_data):
    """Import ratings into database"""
    with app.app_context():
        print(f"Importing {len(ratings_data)} ratings...")
        
        # Import ratings in batches
        batch_size = 5000
        skipped = 0
        imported = 0
        
        for i in range(0, len(ratings_data), batch_size):
            batch = ratings_data[i:i+batch_size]
            
            for rating_data in batch:
                # Check if rating already exists
                existing = Rating.query.filter_by(
                    user_id=rating_data['user_id'],
                    movie_id=rating_data['movie_id']
                ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                # Verify movie and user exist
                movie = Movie.query.get(rating_data['movie_id'])
                user = User.query.get(rating_data['user_id'])
                
                if movie and user:
                    rating = Rating(
                        user_id=rating_data['user_id'],
                        movie_id=rating_data['movie_id'],
                        rating=rating_data['rating'],
                        timestamp=rating_data['timestamp']
                    )
                    db.session.add(rating)
                    imported += 1
                else:
                    skipped += 1
            
            db.session.commit()
            print(f"Progress: {min(i+batch_size, len(ratings_data))}/{len(ratings_data)} processed ({imported} imported, {skipped} skipped)")
        
        print(f"Ratings import completed! Imported: {imported}, Skipped: {skipped}")


def main():
    parser = argparse.ArgumentParser(description='Import MovieLens 1M dataset')
    parser.add_argument('dataset_path', nargs='?', help='Path to MovieLens dataset directory')
    parser.add_argument('--movies', help='Path to movies.dat file')
    parser.add_argument('--ratings', help='Path to ratings.dat file')
    parser.add_argument('--users', help='Path to users.dat file')
    parser.add_argument('--limit-ratings', type=int, help='Limit number of ratings to import')
    
    args = parser.parse_args()
    
    # Determine file paths
    if args.dataset_path:
        # If directory provided, look for .dat files
        movies_file = os.path.join(args.dataset_path, 'movies.dat')
        ratings_file = os.path.join(args.dataset_path, 'ratings.dat')
        users_file = os.path.join(args.dataset_path, 'users.dat')
    else:
        # Use individual file paths
        movies_file = args.movies
        ratings_file = args.ratings
        users_file = args.users
    
    # Validate files exist
    if not movies_file or not os.path.exists(movies_file):
        print(f"Error: Movies file not found: {movies_file}")
        return
    if not ratings_file or not os.path.exists(ratings_file):
        print(f"Error: Ratings file not found: {ratings_file}")
        return
    if not users_file or not os.path.exists(users_file):
        print(f"Error: Users file not found: {users_file}")
        return
    
    print("="*60)
    print("MovieLens 1M Dataset Import")
    print("="*60)
    print(f"Movies:  {movies_file}")
    print(f"Ratings: {ratings_file}")
    print(f"Users:   {users_file}")
    print("="*60)
    
    # Create app
    app = create_app()
    
    # Clear existing data
    print("\n" + "="*60)
    print("Step 1: Clear Existing Data")
    print("="*60)
    if not clear_existing_data(app):
        print("\nImport cancelled by user.")
        return
    
    # Parse files
    print("\n" + "="*60)
    print("Step 2: Parse Data Files")
    print("="*60)
    print("\n[1/3] Parsing movies file...")
    movies_data = parse_movielens_movies(movies_file)
    print(f"Found {len(movies_data)} movies")
    
    print("\n[2/3] Parsing users file...")
    users_data = parse_movielens_users(users_file)
    print(f"Found {len(users_data)} users")
    
    print("\n[3/3] Parsing ratings file...")
    ratings_data = parse_movielens_ratings(ratings_file, args.limit_ratings)
    print(f"Found {len(ratings_data)} ratings")
    
    # Import data
    print("\n" + "="*60)
    print("Step 3: Import Data to Database")
    print("="*60)
    
    print("\n[1/4] Importing genres...")
    genre_map = import_genres(app, movies_data)
    
    print("\n[2/4] Importing movies...")
    import_movies(app, movies_data, genre_map)
    
    print("\n[3/4] Importing users...")
    import_users(app, users_data)
    
    print("\n[4/4] Importing ratings...")
    import_ratings(app, ratings_data)
    
    print("\n" + "="*60)
    print("Import completed successfully!")
    print("="*60)
    print(f"Movies imported:  {len(movies_data)}")
    print(f"Users imported:   {len(users_data)}")
    print(f"Ratings imported: {len(ratings_data)}")
    print("="*60)


if __name__ == '__main__':
    main()
