from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_, func
from models import db, Movie, Rating
from utils.validators import validate_pagination, validate_year

movies_bp = Blueprint('movies', __name__, url_prefix='/api/movies')


@movies_bp.route('', methods=['GET'])
def get_movies():
    """
    Get list of movies with pagination and filters
    ---
    tags:
      - Movies
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Items per page
      - name: genre
        in: query
        type: string
        description: Filter by genre
      - name: year
        in: query
        type: integer
        description: Filter by release year
      - name: min_rating
        in: query
        type: number
        description: Minimum average rating
      - name: search
        in: query
        type: string
        description: Search in movie titles
      - name: sort_by
        in: query
        type: string
        enum: [title, year, rating]
        default: title
        description: Sort by field
      - name: order
        in: query
        type: string
        enum: [asc, desc]
        default: asc
        description: Sort order
    responses:
      200:
        description: List of movies
        schema:
          type: object
          properties:
            movies:
              type: array
              items:
                type: object
            page:
              type: integer
            per_page:
              type: integer
            total:
              type: integer
            pages:
              type: integer
    """
    # Get pagination parameters
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 20)
    
    valid, message, page, per_page = validate_pagination(page, per_page)
    if not valid:
        return jsonify({'error': message}), 400
    
    # Build query
    query = Movie.query
    
    # Filter by genre
    genre = request.args.get('genre')
    if genre:
        query = query.filter(Movie.genres.like(f'%{genre}%'))
    
    # Filter by year
    year = request.args.get('year')
    if year:
        valid_year, year_or_error = validate_year(year)
        if valid_year:
            query = query.filter(Movie.release_year == year_or_error)
    
    # Search in titles
    search = request.args.get('search')
    if search:
        query = query.filter(Movie.title.like(f'%{search}%'))
    
    # Filter by minimum rating
    min_rating = request.args.get('min_rating')
    if min_rating:
        try:
            min_rating = float(min_rating)
            # Subquery to get movies with average rating >= min_rating
            subquery = db.session.query(
                Rating.movie_id,
                func.avg(Rating.rating).label('avg_rating')
            ).group_by(Rating.movie_id).having(
                func.avg(Rating.rating) >= min_rating
            ).subquery()
            
            query = query.join(subquery, Movie.id == subquery.c.movie_id)
        except ValueError:
            pass
    
    # Sorting
    sort_by = request.args.get('sort_by', 'title')
    order = request.args.get('order', 'asc')
    
    if sort_by == 'title':
        query = query.order_by(Movie.title.asc() if order == 'asc' else Movie.title.desc())
    elif sort_by == 'year':
        query = query.order_by(Movie.release_year.asc() if order == 'asc' else Movie.release_year.desc())
    elif sort_by == 'rating':
        # Sort by average rating (requires subquery)
        subquery = db.session.query(
            Rating.movie_id,
            func.avg(Rating.rating).label('avg_rating')
        ).group_by(Rating.movie_id).subquery()
        
        query = query.outerjoin(subquery, Movie.id == subquery.c.movie_id)
        query = query.order_by(
            subquery.c.avg_rating.asc() if order == 'asc' else subquery.c.avg_rating.desc()
        )
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    movies = [movie.to_dict(include_stats=True) for movie in pagination.items]
    
    return jsonify({
        'movies': movies,
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages
    }), 200


@movies_bp.route('/<int:movie_id>', methods=['GET'])
def get_movie(movie_id):
    """
    Get movie details by ID
    ---
    tags:
      - Movies
    parameters:
      - name: movie_id
        in: path
        type: integer
        required: true
        description: Movie ID
    responses:
      200:
        description: Movie details
        schema:
          type: object
      404:
        description: Movie not found
    """
    movie = Movie.query.get(movie_id)
    
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404
    
    return jsonify(movie.to_dict(include_stats=True)), 200


@movies_bp.route('/featured', methods=['GET'])
def get_featured_movies():
    """
    Get featured movies (popular with high ratings)
    ---
    tags:
      - Movies
    parameters:
      - name: limit
        in: query
        type: integer
        default: 10
        description: Number of featured movies to return
    responses:
      200:
        description: List of featured movies
        schema:
          type: object
          properties:
            movies:
              type: array
              items:
                type: object
    """
    limit = request.args.get('limit', 10, type=int)
    if limit > 50:
        limit = 50
    
    # Get movies with highest average ratings and most ratings
    subquery = db.session.query(
        Rating.movie_id,
        func.avg(Rating.rating).label('avg_rating'),
        func.count(Rating.id).label('rating_count')
    ).group_by(Rating.movie_id).having(
        func.count(Rating.id) >= 50  # At least 50 ratings
    ).subquery()
    
    featured = db.session.query(Movie).join(
        subquery, Movie.id == subquery.c.movie_id
    ).order_by(
        subquery.c.avg_rating.desc(),
        subquery.c.rating_count.desc()
    ).limit(limit).all()
    
    movies = [movie.to_dict(include_stats=True) for movie in featured]
    
    return jsonify({'movies': movies}), 200


@movies_bp.route('/<int:movie_id>/ratings', methods=['GET'])
def get_movie_ratings(movie_id):
    """
    Get all ratings for a specific movie
    ---
    tags:
      - Movies
    parameters:
      - name: movie_id
        in: path
        type: integer
        required: true
        description: Movie ID
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: List of ratings
      404:
        description: Movie not found
    """
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404
    
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 20)
    
    valid, message, page, per_page = validate_pagination(page, per_page)
    if not valid:
        return jsonify({'error': message}), 400
    
    pagination = Rating.query.filter_by(movie_id=movie_id).order_by(
        Rating.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    ratings = [rating.to_dict(include_user=True) for rating in pagination.items]
    
    return jsonify({
        'movie_id': movie_id,
        'ratings': ratings,
        'average_rating': movie.get_average_rating(),
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages
    }), 200
