from sqlalchemy import func
from models import db, Movie, Rating, Genre


class ChatRetrievalService:
    """Database retrieval logic for chatbot recommendations."""

    def _movie_stats_subquery(self):
        return (
            db.session.query(
                Rating.movie_id.label('movie_id'),
                func.avg(Rating.rating).label('avg_rating'),
                func.count(Rating.id).label('ratings_count')
            )
            .group_by(Rating.movie_id)
            .subquery()
        )

    def _base_query(self):
        stats = self._movie_stats_subquery()
        return (
            db.session.query(
                Movie,
                func.coalesce(stats.c.avg_rating, 0.0).label('avg_rating'),
                func.coalesce(stats.c.ratings_count, 0).label('ratings_count')
            )
            .outerjoin(stats, Movie.id == stats.c.movie_id)
        ), stats

    def _format_results(self, rows):
        items = []
        for movie, avg_rating, ratings_count in rows:
            items.append({
                'id': movie.id,
                'title': movie.title,
                'release_year': movie.release_year,
                'genres': movie.get_genres_list(),
                'description': movie.description,
                'poster_url': movie.poster_url,
                'tmdb_id': movie.tmdb_id,
                'average_rating': round(float(avg_rating or 0.0), 2),
                'ratings_count': int(ratings_count or 0)
            })
        return items

    def search_by_criteria(self, genre=None, year_min=None, year_max=None, rating_min=None, limit=10):
        query, stats = self._base_query()

        if genre:
            query = query.filter(Movie.genres_list.any(Genre.name.ilike(genre)))

        if year_min is not None:
            query = query.filter(Movie.release_year.isnot(None), Movie.release_year >= year_min)

        if year_max is not None:
            query = query.filter(Movie.release_year.isnot(None), Movie.release_year <= year_max)

        if rating_min is not None:
            query = query.filter(func.coalesce(stats.c.avg_rating, 0.0) >= rating_min)

        query = query.order_by(
            func.coalesce(stats.c.avg_rating, 0.0).desc(),
            func.coalesce(stats.c.ratings_count, 0).desc(),
            Movie.title.asc()
        ).limit(limit)

        return self._format_results(query.all())

    def popular_movies(self, genre=None, limit=10, min_ratings=30, min_rating=3.5):
        query, stats = self._base_query()
        query = query.filter(
            func.coalesce(stats.c.ratings_count, 0) >= min_ratings,
            func.coalesce(stats.c.avg_rating, 0.0) >= min_rating,
        )

        if genre:
            query = query.filter(Movie.genres_list.any(Genre.name.ilike(genre)))

        query = query.order_by(
            func.coalesce(stats.c.ratings_count, 0).desc(),
            func.coalesce(stats.c.avg_rating, 0.0).desc(),
            Movie.title.asc()
        ).limit(limit)

        items = self._format_results(query.all())
        if items:
            return items

        # fallback less strict
        query, stats = self._base_query()
        if genre:
            query = query.filter(Movie.genres_list.any(Genre.name.ilike(genre)))

        query = query.order_by(
            func.coalesce(stats.c.ratings_count, 0).desc(),
            func.coalesce(stats.c.avg_rating, 0.0).desc(),
            Movie.title.asc()
        ).limit(limit)

        return self._format_results(query.all())

    def search_by_title(self, title, limit=10):
        query, _ = self._base_query()
        query = query.filter(Movie.title.ilike(f"%{title}%")).order_by(
            Movie.release_year.desc().nullslast(),
            Movie.title.asc()
        ).limit(limit)
        return self._format_results(query.all())

    def similar_movies(self, movie_title, limit=10):
        ref_movie = Movie.query.filter(Movie.title.ilike(f"%{movie_title}%")).first()
        if not ref_movie:
            return []

        ref_genres = ref_movie.get_genres_list()
        query, stats = self._base_query()
        query = query.filter(Movie.id != ref_movie.id)

        if ref_genres:
            query = query.filter(Movie.genres_list.any(Genre.name.in_(ref_genres)))

        ref_avg = ref_movie.get_average_rating()
        query = query.order_by(
            func.abs(func.coalesce(stats.c.avg_rating, 0.0) - ref_avg).asc(),
            func.coalesce(stats.c.ratings_count, 0).desc(),
            Movie.title.asc()
        ).limit(limit)

        return self._format_results(query.all())

    def get_movies_by_ids(self, movie_ids):
        if not movie_ids:
            return []

        query, _ = self._base_query()
        rows = query.filter(Movie.id.in_(movie_ids)).all()
        by_id = {item['id']: item for item in self._format_results(rows)}
        return [by_id[mid] for mid in movie_ids if mid in by_id]


chat_retrieval_service = ChatRetrievalService()
