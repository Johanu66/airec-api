"""
Build precomputed segment-based recommendations from database data.

This script reproduces the notebook pipeline in production form:
1) Build user genre preference profiles from ratings + movie genres
2) Cluster users into `id_type` segments using KMeans
3) Compute movie ranking per `id_type` with dot-product scoring
4) Persist results in:
   - user_recommendation_profiles
   - type_recommendations

Usage:
  python scripts/build_segment_recommendations.py
  python scripts/build_segment_recommendations.py --clusters 11 --top-n 500 --model-version v1
  python scripts/build_segment_recommendations.py --auto-k --max-k 20
"""

import os
import sys
import json
import argparse
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import (
    db,
    Movie,
    Genre,
    Rating,
    UserRecommendationProfile,
    TypeRecommendation,
)


def _build_feature_matrices():
    """Build user feature matrix (mean ratings by genre) and movie genre matrix."""
    genres = Genre.query.order_by(Genre.name.asc()).all()
    genre_names = [g.name for g in genres]

    if not genre_names:
        raise ValueError("No genres found in database. Import data first.")

    genre_index = {name: idx for idx, name in enumerate(genre_names)}
    n_genres = len(genre_names)

    movies = Movie.query.all()
    if not movies:
        raise ValueError("No movies found in database.")

    movie_ids = []
    movie_matrix_rows = []
    movie_vectors = {}

    for movie in movies:
        vec = np.zeros(n_genres, dtype=np.float32)
        for genre in movie.genres_list:
            idx = genre_index.get(genre.name)
            if idx is not None:
                vec[idx] = 1.0

        movie_ids.append(movie.id)
        movie_matrix_rows.append(vec)
        movie_vectors[movie.id] = vec

    movie_matrix = np.vstack(movie_matrix_rows)

    user_weighted = defaultdict(lambda: np.zeros(n_genres, dtype=np.float32))
    user_counts = defaultdict(lambda: np.zeros(n_genres, dtype=np.float32))

    ratings_query = Rating.query.order_by(Rating.id.asc()).yield_per(5000)
    total_ratings = 0

    for rating in ratings_query:
        total_ratings += 1
        vec = movie_vectors.get(rating.movie_id)
        if vec is None:
            continue

        user_weighted[rating.user_id] += (rating.rating * vec)
        user_counts[rating.user_id] += vec

    if not user_weighted:
        raise ValueError("No ratings found to build user profiles.")

    user_ids = sorted(user_weighted.keys())
    user_matrix = np.zeros((len(user_ids), n_genres), dtype=np.float32)

    for i, user_id in enumerate(user_ids):
        weighted = user_weighted[user_id]
        counts = user_counts[user_id]
        means = np.divide(
            weighted,
            counts,
            out=np.zeros_like(weighted),
            where=counts > 0,
        )
        user_matrix[i] = means

    return {
        "genre_names": genre_names,
        "user_ids": user_ids,
        "user_matrix": user_matrix,
        "movie_ids": movie_ids,
        "movie_matrix": movie_matrix,
        "total_ratings": total_ratings,
    }


def _choose_k(user_matrix, max_k=20):
    """Choose number of clusters via silhouette score."""
    n_users = user_matrix.shape[0]
    max_k = max(2, min(max_k, n_users - 1))

    best_k = 2
    best_score = -1.0

    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = km.fit_predict(user_matrix)

        # Silhouette score requires at least 2 labels
        if len(set(labels)) < 2:
            continue

        score = silhouette_score(user_matrix, labels)
        print(f"k={k} -> silhouette={score:.4f}")

        if score > best_score:
            best_score = score
            best_k = k

    return best_k


def build_segments(clusters=11, top_n=500, model_version='v1', auto_k=False, max_k=20):
    data = _build_feature_matrices()
    user_ids = data["user_ids"]
    user_matrix = data["user_matrix"]
    movie_ids = data["movie_ids"]
    movie_matrix = data["movie_matrix"]

    n_users = user_matrix.shape[0]
    if n_users < 2:
        raise ValueError("Need at least 2 users with ratings to build segments.")

    if auto_k:
        clusters = _choose_k(user_matrix, max_k=max_k)
        print(f"Selected clusters={clusters} (auto-k)")

    clusters = min(clusters, n_users)
    if clusters < 2:
        clusters = 2

    print("=" * 60)
    print("Building segment recommendations")
    print("=" * 60)
    print(f"Users with ratings: {n_users}")
    print(f"Movies: {len(movie_ids)}")
    print(f"Genres: {len(data['genre_names'])}")
    print(f"Ratings processed: {data['total_ratings']}")
    print(f"Clusters (id_type): {clusters}")
    print(f"Top N per segment: {top_n}")
    print(f"Model version: {model_version}")

    kmeans = KMeans(n_clusters=clusters, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(user_matrix)

    # Type profile matrix: mean vector by cluster id
    type_vectors = np.zeros((clusters, user_matrix.shape[1]), dtype=np.float32)
    for t in range(clusters):
        mask = labels == t
        if np.any(mask):
            type_vectors[t] = np.mean(user_matrix[mask], axis=0)

    scores = np.dot(type_vectors, movie_matrix.T)

    # Replace previous results for this model version
    UserRecommendationProfile.query.filter_by(model_version=model_version).delete(synchronize_session=False)
    TypeRecommendation.query.filter_by(model_version=model_version).delete(synchronize_session=False)
    db.session.commit()

    # Save user profiles
    profiles_to_insert = []
    for i, user_id in enumerate(user_ids):
        vec = user_matrix[i].tolist()
        profile = UserRecommendationProfile(
            user_id=user_id,
            id_type=int(labels[i]),
            vector_json=json.dumps(vec),
            model_version=model_version,
        )
        profiles_to_insert.append(profile)

    db.session.bulk_save_objects(profiles_to_insert)
    db.session.commit()

    # Save per-type movie rankings
    rows_to_insert = []
    for t in range(clusters):
        order = np.argsort(-scores[t])  # descending by score
        rank = 1

        for idx in order[:top_n]:
            rows_to_insert.append(
                TypeRecommendation(
                    id_type=int(t),
                    movie_id=int(movie_ids[idx]),
                    score=float(scores[t, idx]),
                    rank=rank,
                    model_version=model_version,
                )
            )
            rank += 1

    batch_size = 5000
    for i in range(0, len(rows_to_insert), batch_size):
        db.session.bulk_save_objects(rows_to_insert[i:i + batch_size])
        db.session.commit()

    print("Build completed successfully.")
    print(f"Inserted profiles: {len(profiles_to_insert)}")
    print(f"Inserted type recommendations: {len(rows_to_insert)}")


def main():
    parser = argparse.ArgumentParser(description='Build segment-based recommendations from DB data')
    parser.add_argument('--clusters', type=int, default=11, help='Number of KMeans clusters')
    parser.add_argument('--top-n', type=int, default=500, help='Top movies per segment to persist')
    parser.add_argument('--model-version', type=str, default='v1', help='Model version label')
    parser.add_argument('--auto-k', action='store_true', help='Select k automatically using silhouette score')
    parser.add_argument('--max-k', type=int, default=20, help='Max k when --auto-k is enabled')
    parser.add_argument('--config', type=str, default='development', help='Flask config name')
    args = parser.parse_args()

    app = create_app(args.config)
    with app.app_context():
        build_segments(
            clusters=args.clusters,
            top_n=args.top_n,
            model_version=args.model_version,
            auto_k=args.auto_k,
            max_k=args.max_k,
        )


if __name__ == '__main__':
    main()
