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
import re
import unicodedata
from difflib import SequenceMatcher

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
    
    def normalize_title(self, text):
        """Normalize title for fuzzy matching"""
        if not text:
            return ''
        text_norm = unicodedata.normalize('NFD', str(text)).encode('ascii', 'ignore').decode('ascii')
        text_norm = re.sub(r'[^a-zA-Z0-9]+', ' ', text_norm.lower()).strip()
        return text_norm

    def fix_mojibake(self, text):
        """Fix common mojibake encoding issues"""
        if not text:
            return text
        try:
            fixed = str(text).encode('latin-1').decode('utf-8')
            return fixed if fixed != text else text
        except Exception:
            return text

    def title_similarity(self, a, b):
        """Compute similarity score between two titles"""
        return SequenceMatcher(None, self.normalize_title(a), self.normalize_title(b)).ratio()

    def _search_once(self, query_title, query_year=None):
        """Single TMDB search request"""
        url = f'{self.base_url}/search/movie'
        params = {
            'api_key': self.api_key,
            'query': query_title,
            'include_adult': False
        }

        if query_year:
            params['year'] = str(query_year)

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json().get('results', [])

    def search_movie_best_match(self, title, year=None, sleep_seconds=0.26):
        """Search TMDB with multiple variants and return best scored match"""
        base_title = title or ''
        cleaned_title = re.sub(r'\s*\(.*?\)\s*$', '', base_title).strip()
        fixed_title = self.fix_mojibake(base_title)

        queries = []
        if year:
            queries.append((base_title, str(year)))
        queries.append((base_title, None))

        if cleaned_title and cleaned_title != base_title:
            queries.append((cleaned_title, str(year) if year else None))
            queries.append((cleaned_title, None))

        if fixed_title and fixed_title != base_title:
            queries.append((fixed_title, str(year) if year else None))
            queries.append((fixed_title, None))

        if year:
            try:
                year_int = int(year)
                queries.append((base_title, str(year_int - 1)))
                queries.append((base_title, str(year_int + 1)))
            except (TypeError, ValueError):
                pass

        # Keep order, remove duplicates
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        def score_candidate(candidate):
            candidate_title = candidate.get('title') or ''
            candidate_original = candidate.get('original_title') or ''

            scores = [
                self.title_similarity(base_title, candidate_title),
                self.title_similarity(base_title, candidate_original),
                self.title_similarity(cleaned_title, candidate_title),
                self.title_similarity(cleaned_title, candidate_original),
            ]
            score = max(scores)

            if year and candidate.get('release_date'):
                try:
                    candidate_year = int(candidate['release_date'][:4])
                    requested_year = int(year)
                    diff = abs(candidate_year - requested_year)

                    if diff == 0:
                        score += 0.18
                    elif diff == 1:
                        score += 0.10
                    elif diff == 2:
                        score += 0.05
                    else:
                        score -= 0.05 * min(diff, 4)
                except (TypeError, ValueError):
                    pass

            if candidate.get('poster_path'):
                score += 0.02

            return score

        best = None
        best_score = 0.0

        for query_title, query_year in unique_queries:
            try:
                results = self._search_once(query_title, query_year)
            except requests.RequestException as error:
                print(f"  ! Search error for '{query_title}': {error}")
                continue

            for candidate in results[:6]:
                score = score_candidate(candidate)
                if score > best_score:
                    best_score = score
                    best = candidate

            if best_score >= 1.05:
                break

            time.sleep(sleep_seconds)

        if not best or best_score < 0.45:
            return None

        return {
            'tmdb_id': best.get('id'),
            'title': best.get('title'),
            'poster_url': self.get_poster_url(best.get('poster_path')),
            'backdrop_url': self.get_backdrop_url(best.get('backdrop_path')),
            'description': best.get('overview'),
            'release_date': best.get('release_date'),
            'score': round(best_score, 3)
        }
    
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
    """Update movies with missing TMDB metadata"""
    
    if not tmdb_api_key:
        print("Error: TMDB API key not found. Please set TMDB_API_KEY in .env file")
        return
    
    fetcher = TMDBFetcher(tmdb_api_key)
    
    with app.app_context():
        # Get movies missing at least one important TMDB field
        query = Movie.query.filter(
            (Movie.tmdb_id == None) |
            (Movie.description == None) | (Movie.description == '') |
            (Movie.poster_url == None) | (Movie.poster_url == '') |
            (Movie.backdrop_url == None) | (Movie.backdrop_url == '')
        )
        
        if limit:
            query = query.limit(limit)
        
        movies = query.all()
        total = len(movies)
        
        print(f"Updating missing TMDB fields for {total} movies...")
        
        updated = 0
        not_found = 0
        
        for i, movie in enumerate(movies, 1):
            print(f"[{i}/{total}] Processing: {movie.title}", end='')
            
            # Search best TMDB candidate with robust title matching
            result = fetcher.search_movie_best_match(movie.title, movie.release_year)

            if result:
                changed = False

                if not movie.tmdb_id and result.get('tmdb_id'):
                    movie.tmdb_id = result['tmdb_id']
                    changed = True

                if (not movie.description) and result.get('description'):
                    movie.description = result['description']
                    changed = True

                if (not movie.poster_url) and result.get('poster_url'):
                    movie.poster_url = result['poster_url']
                    changed = True

                if (not movie.backdrop_url) and result.get('backdrop_url'):
                    movie.backdrop_url = result['backdrop_url']
                    changed = True

                # Optional release year backfill
                if not movie.release_year and result.get('release_date'):
                    try:
                        movie.release_year = int(result['release_date'][:4])
                        changed = True
                    except (TypeError, ValueError):
                        pass

                if changed:
                    updated += 1
                    print(f" ✓ Updated (score={result.get('score')})")
                else:
                    print(" - Already complete")
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
