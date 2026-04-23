from sqlalchemy import func
from models import db, Movie, Rating, Genre, User, UserRecommendationProfile, TypeRecommendation


class RecommendationEngine:
    """Collaborative filtering recommendation engine"""
    
    def __init__(self):
        self.user_item_matrix = None
        self.user_similarity = None
    
    def get_user_based_recommendations(self, user_id, limit=10):
        """Get personalized recommendations using hybrid strategy.

        Priority:
        1) Collaborative filtering
        2) Segment-based precomputed recommendations (KMeans id_type)
        3) Popular movies fallback
        """
        
        # Get user's ratings
        user_ratings = Rating.query.filter_by(user_id=user_id).all()
        
        if not user_ratings:
            # Cold-start: try segment recommendations first, then fallback to popular.
            segment_movies = self.get_segment_based_recommendations(user_id, limit)
            if len(segment_movies) >= limit:
                return segment_movies[:limit]

            popular_movies = self.get_popular_movies(limit)
            return self._merge_movie_lists(segment_movies, popular_movies, limit)
        
        user_rated_movie_ids = {r.movie_id for r in user_ratings}
        
        # Find similar users based on common movie ratings
        similar_users = self._find_similar_users(user_id, user_rated_movie_ids)
        
        segment_movies = self.get_segment_based_recommendations(user_id, limit)

        if not similar_users:
            if segment_movies:
                if len(segment_movies) >= limit:
                    return segment_movies[:limit]
                return self._merge_movie_lists(segment_movies, self.get_popular_movies(limit), limit)
            return self.get_popular_movies(limit)
        
        # Get movies rated highly by similar users
        collaborative_movies = self._get_recommendations_from_similar_users(
            similar_users,
            user_rated_movie_ids,
            limit
        )

        # Merge with segment-based recommendations to improve coverage/diversity.
        merged = self._merge_movie_lists(collaborative_movies, segment_movies, limit)

        if len(merged) < limit:
            merged = self._merge_movie_lists(merged, self.get_popular_movies(limit), limit)

        return merged

    def get_segment_based_recommendations(self, user_id, limit=10, model_version='v1'):
        """Get recommendations from precomputed user segment (`id_type`) rankings."""
        profile = UserRecommendationProfile.query.filter_by(
            user_id=user_id,
            model_version=model_version
        ).first()

        if not profile:
            return []

        rated_movie_ids = {
            r.movie_id for r in Rating.query.filter_by(user_id=user_id).all()
        }

        rows = TypeRecommendation.query.filter_by(
            id_type=profile.id_type,
            model_version=model_version
        ).order_by(
            TypeRecommendation.rank.asc(),
            TypeRecommendation.score.desc()
        ).limit(limit * 8).all()

        if not rows:
            return []

        movie_ids = []
        for row in rows:
            if row.movie_id not in rated_movie_ids:
                movie_ids.append(row.movie_id)
            if len(movie_ids) >= limit:
                break

        if not movie_ids:
            return []

        movies = Movie.query.filter(Movie.id.in_(movie_ids)).all()
        movie_dict = {m.id: m for m in movies}
        return [movie_dict[mid] for mid in movie_ids if mid in movie_dict]

    def _merge_movie_lists(self, primary, secondary, limit):
        """Merge two movie lists preserving order and uniqueness."""
        merged = []
        seen = set()

        for movie in primary:
            if movie.id not in seen:
                seen.add(movie.id)
                merged.append(movie)
                if len(merged) >= limit:
                    return merged

        for movie in secondary:
            if movie.id not in seen:
                seen.add(movie.id)
                merged.append(movie)
                if len(merged) >= limit:
                    return merged

        return merged
    
    def _find_similar_users(self, user_id, user_rated_movie_ids, limit=50):
        """Find users with similar rating patterns"""
        
        # Get users who have rated similar movies
        similar_user_ratings = db.session.query(
            Rating.user_id,
            func.count(Rating.id).label('common_movies')
        ).filter(
            Rating.movie_id.in_(user_rated_movie_ids),
            Rating.user_id != user_id
        ).group_by(Rating.user_id).order_by(
            func.count(Rating.id).desc()
        ).limit(limit).all()
        
        return [r.user_id for r in similar_user_ratings]
    
    def _get_recommendations_from_similar_users(self, similar_users, exclude_movie_ids, limit):
        """Get highly rated movies from similar users"""
        
        # Get movies rated highly (>= 4.0) by similar users
        recommended_movies = db.session.query(
            Rating.movie_id,
            func.avg(Rating.rating).label('avg_rating'),
            func.count(Rating.id).label('rating_count')
        ).filter(
            Rating.user_id.in_(similar_users),
            Rating.movie_id.notin_(exclude_movie_ids),
            Rating.rating >= 4.0
        ).group_by(Rating.movie_id).having(
            func.count(Rating.id) >= 3  # At least 3 ratings from similar users
        ).order_by(
            func.avg(Rating.rating).desc(),
            func.count(Rating.id).desc()
        ).limit(limit).all()
        
        movie_ids = [r.movie_id for r in recommended_movies]
        movies = Movie.query.filter(Movie.id.in_(movie_ids)).all()
        
        # Sort movies by the order of movie_ids
        movie_dict = {m.id: m for m in movies}
        sorted_movies = [movie_dict[mid] for mid in movie_ids if mid in movie_dict]
        
        return sorted_movies
    
    def get_genre_based_recommendations(self, genre, user_id=None, limit=10):
        """Get best movies in a specific genre"""
        
        # Find the genre object
        genre_obj = Genre.query.filter_by(name=genre).first()
        if not genre_obj:
            return []
        
        # Get movies in this genre
        query = Movie.query.filter(Movie.genres_list.contains(genre_obj))
        
        # If user_id provided, exclude movies they've already rated
        if user_id:
            user_rated_movie_ids = [
                r.movie_id for r in Rating.query.filter_by(user_id=user_id).all()
            ]
            if user_rated_movie_ids:
                query = query.filter(Movie.id.notin_(user_rated_movie_ids))
        
        # Get movies with high ratings and sufficient rating count
        subquery = db.session.query(
            Rating.movie_id,
            func.avg(Rating.rating).label('avg_rating'),
            func.count(Rating.id).label('rating_count')
        ).group_by(Rating.movie_id).having(
            func.avg(Rating.rating) >= 3.5,
            func.count(Rating.id) >= 10
        ).subquery()
        
        movies = query.join(
            subquery, Movie.id == subquery.c.movie_id
        ).order_by(
            subquery.c.avg_rating.desc(),
            subquery.c.rating_count.desc()
        ).limit(limit).all()
        
        return movies
    
    def get_popular_movies(self, limit=10):
        """Get most popular movies (highest ratings and most rated)"""
        
        subquery = db.session.query(
            Rating.movie_id,
            func.avg(Rating.rating).label('avg_rating'),
            func.count(Rating.id).label('rating_count')
        ).group_by(Rating.movie_id).having(
            func.count(Rating.id) >= 50,
            func.avg(Rating.rating) >= 4.0
        ).subquery()
        
        movies = db.session.query(Movie).join(
            subquery, Movie.id == subquery.c.movie_id
        ).order_by(
            subquery.c.avg_rating.desc(),
            subquery.c.rating_count.desc()
        ).limit(limit).all()
        
        return movies
    
    def get_home_recommendations(self, user_id=None, limit=30):
        """Get mixed recommendations for home page"""
        
        recommendations = {
            'personalized': [],
            'popular': [],
            'trending': []
        }
        
        # Get popular movies
        recommendations['popular'] = self.get_popular_movies(limit=10)
        
        # If user is logged in, get personalized recommendations
        if user_id:
            recommendations['personalized'] = self.get_user_based_recommendations(
                user_id, limit=10
            )
            
            # Get recommendations based on user's favorite genres
            user = User.query.get(user_id)
            if user and user.favorite_genres:
                favorite_genres = [g.name for g in user.favorite_genres]
                genre_movies = self.get_genre_based_recommendations(
                    favorite_genres[0], user_id, limit=10
                )
                recommendations['trending'] = genre_movies
        
        # If no personalized or trending, use popular for trending
        if not recommendations['trending']:
            recommendations['trending'] = self.get_popular_movies(limit=10)
        
        return recommendations
    
    def get_similar_movies(self, movie_id, limit=10):
        """Get movies similar to a given movie (based on genre and ratings)"""
        
        movie = Movie.query.get(movie_id)
        if not movie:
            return []
        
        genres = movie.get_genres_list()
        if not genres:
            return []
        
        # Find movies with overlapping genres
        similar_movies = []
        for genre_name in genres:
            genre_obj = Genre.query.filter_by(name=genre_name).first()
            if genre_obj:
                genre_movies = Movie.query.filter(
                    Movie.genres_list.contains(genre_obj),
                    Movie.id != movie_id
                ).limit(limit * 2).all()
                similar_movies.extend(genre_movies)
        
        # Remove duplicates and limit
        seen = set()
        unique_movies = []
        for m in similar_movies:
            if m.id not in seen:
                seen.add(m.id)
                unique_movies.append(m)
                if len(unique_movies) >= limit:
                    break
        
        return unique_movies
