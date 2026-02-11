"""
Script to fetch movie posters and metadata from TMDB API

Requires TMDB API key set in .env file

Usage:
    python fetch_posters.py [--limit 100]
"""

import sys
import os
import requests
import time
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Movie


class TMDBFetcher:
    """Fetch movie data from TMDB API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://api.themoviedb.org/3'
        self.image_base_url = 'https://image.tmdb.org/t/p/w500'
        self.backdrop_base_url = 'https://image.tmdb.org/t/p/original'
    
    def search_movie(self, title, year=None):
        """Search for a movie by title and year"""
        url = f'{self.base_url}/search/movie'
        params = {
            'api_key': self.api_key,
            'query': title
        }
        
        if year:
            params['year'] = year
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    return data['results'][0]  # Return first result
            return None
        except Exception as e:
            print(f"Error searching for {title}: {e}")
            return None
    
    def get_movie_details(self, tmdb_id):
        """Get detailed movie information"""
        url = f'{self.base_url}/movie/{tmdb_id}'
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching details for TMDB ID {tmdb_id}: {e}")
            return None
    
    def get_poster_url(self, poster_path):
        """Get full poster URL"""
        if poster_path:
            return f'{self.image_base_url}{poster_path}'
        return None
    
    def get_backdrop_url(self, backdrop_path):
        """Get full backdrop URL"""
        if backdrop_path:
            return f'{self.backdrop_base_url}{backdrop_path}'
        return None


def update_movie_metadata(app, tmdb_api_key, limit=None):
    """Update movies with TMDB metadata"""
    
    if not tmdb_api_key:
        print("Error: TMDB API key not found. Please set TMDB_API_KEY in .env file")
        return
    
    fetcher = TMDBFetcher(tmdb_api_key)
    
    with app.app_context():
        # Get movies without posters
        query = Movie.query.filter(
            (Movie.poster_url == None) | (Movie.poster_url == '')
        )
        
        if limit:
            query = query.limit(limit)
        
        movies = query.all()
        total = len(movies)
        
        print(f"Updating {total} movies with TMDB data...")
        
        updated = 0
        not_found = 0
        
        for i, movie in enumerate(movies, 1):
            print(f"[{i}/{total}] Processing: {movie.title}", end='')
            
            # Search for movie on TMDB
            result = fetcher.search_movie(movie.title, movie.release_year)
            
            if result:
                # Get detailed information
                tmdb_id = result['id']
                details = fetcher.get_movie_details(tmdb_id)
                
                if details:
                    # Update movie data
                    movie.tmdb_id = tmdb_id
                    movie.poster_url = fetcher.get_poster_url(details.get('poster_path'))
                    movie.backdrop_url = fetcher.get_backdrop_url(details.get('backdrop_path'))
                    
                    if details.get('overview'):
                        movie.description = details['overview']
                    
                    if details.get('imdb_id'):
                        movie.imdb_id = details['imdb_id']
                    
                    # Update release year if not set
                    if not movie.release_year and details.get('release_date'):
                        try:
                            movie.release_year = int(details['release_date'][:4])
                        except:
                            pass
                    
                    updated += 1
                    print(f" ✓ Updated")
                else:
                    not_found += 1
                    print(f" ✗ Details not found")
            else:
                not_found += 1
                print(f" ✗ Not found")
            
            # Commit every 10 movies
            if i % 10 == 0:
                db.session.commit()
                print(f"Progress: {updated} updated, {not_found} not found")
            
            # Rate limiting: TMDB allows 40 requests per 10 seconds
            time.sleep(0.26)  # ~3.8 requests per second
        
        # Final commit
        db.session.commit()
        
        print("\n" + "="*50)
        print(f"Update completed!")
        print(f"Total processed: {total}")
        print(f"Successfully updated: {updated}")
        print(f"Not found: {not_found}")
        print(f"Success rate: {updated/total*100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Fetch movie posters from TMDB')
    parser.add_argument('--limit', type=int, help='Limit number of movies to update')
    
    args = parser.parse_args()
    
    # Create app
    app = create_app()
    
    # Get TMDB API key from config
    tmdb_api_key = app.config.get('TMDB_API_KEY')
    
    # Update movies
    update_movie_metadata(app, tmdb_api_key, args.limit)


if __name__ == '__main__':
    main()
