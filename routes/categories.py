from flask import Blueprint, request, jsonify
from sqlalchemy import func
from models import db, Movie, Rating
from utils.validators import validate_pagination

categories_bp = Blueprint('categories', __name__, url_prefix='/api/categories')

# Available genres from MovieLens
AVAILABLE_GENRES = [
    'Action', 'Adventure', 'Animation', "Children's", 'Comedy', 'Crime',
    'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror', 'Musical',
    'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'
]


@categories_bp.route('', methods=['GET'])
def get_categories():
    """
    Get list of available movie genres
    ---
    tags:
      - Categories
    responses:
      200:
        description: List of genres
        schema:
          type: object
          properties:
            genres:
              type: array
              items:
                type: string
    """
    return jsonify({'genres': AVAILABLE_GENRES}), 200


@categories_bp.route('/<string:genre>/movies', methods=['GET'])
def get_movies_by_category(genre):
    """
    Get movies filtered by genre
    ---
    tags:
      - Categories
    parameters:
      - name: genre
        in: path
        type: string
        required: true
        description: Genre name
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
      - name: sort_by
        in: query
        type: string
        enum: [popularity, rating, title, year]
        default: popularity
        description: Sort criterion
    responses:
      200:
        description: List of movies in the genre
      404:
        description: Genre not found
    """
    # Validate genre
    if genre not in AVAILABLE_GENRES:
        return jsonify({'error': f'Genre "{genre}" not found'}), 404
    
    # Get pagination parameters
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 20)
    
    valid, message, page, per_page = validate_pagination(page, per_page)
    if not valid:
        return jsonify({'error': message}), 400
    
    # Build query
    query = Movie.query.filter(Movie.genres.like(f'%{genre}%'))
    
    # Sorting
    sort_by = request.args.get('sort_by', 'popularity')
    
    if sort_by == 'title':
        query = query.order_by(Movie.title.asc())
    elif sort_by == 'year':
        query = query.order_by(Movie.release_year.desc())
    elif sort_by == 'rating':
        # Sort by average rating
        subquery = db.session.query(
            Rating.movie_id,
            func.avg(Rating.rating).label('avg_rating')
        ).group_by(Rating.movie_id).subquery()
        
        query = query.outerjoin(subquery, Movie.id == subquery.c.movie_id)
        query = query.order_by(subquery.c.avg_rating.desc())
    else:  # popularity (most ratings)
        subquery = db.session.query(
            Rating.movie_id,
            func.count(Rating.id).label('rating_count')
        ).group_by(Rating.movie_id).subquery()
        
        query = query.outerjoin(subquery, Movie.id == subquery.c.movie_id)
        query = query.order_by(subquery.c.rating_count.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    movies = [movie.to_dict(include_stats=True) for movie in pagination.items]
    
    return jsonify({
        'genre': genre,
        'movies': movies,
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages
    }), 200
