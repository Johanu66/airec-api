# AiRec API

Flask REST API for movie discovery, ratings, personalized recommendations, and an AI-assisted movie chatbot.

This README reflects the current codebase structure in `app.py`, `routes/`, `services/`, `scripts/`, and `models/__init__.py`.

## What The API Does

- JWT authentication with token blacklist support
- Movie catalog browsing with filtering, pagination, and rating stats
- User profile and favorite genre management
- Movie rating CRUD for authenticated users
- Recommendation engine with three layers:
  - collaborative filtering from overlapping user ratings
  - precomputed segment recommendations from KMeans clustering
  - popularity and genre fallbacks
- Chatbot endpoints with:
  - rule-based intent detection
  - SQL retrieval
  - optional semantic RAG over the movie catalog
  - optional LLM generation constrained to retrieved movies
- Swagger UI served by Flasgger
- Utility scripts for database setup, MovieLens import, TMDB enrichment, segment builds, RAG rebuild, and log inspection

## Stack

- Flask 3
- SQLAlchemy + Flask-Migrate
- MySQL via `PyMySQL`
- JWT via `Flask-JWT-Extended`
- Swagger via `flasgger`
- Optional RAG via `chromadb` + `sentence-transformers`
- Optional LLM backends:
  - OpenAI-compatible chat-completions endpoint
  - Google Gemini fallback

## Repository Layout

- `app.py`: application factory, logging, Swagger, blueprint registration, root and health endpoints
- `config.py`: environment-driven configuration
- `models/__init__.py`: SQLAlchemy models and association tables
- `routes/`: API blueprints
- `services/`: recommendation, chatbot retrieval, orchestration, LLM, and RAG services
- `utils/`: JWT helpers and input validators
- `scripts/`: operational and data-loading scripts
- `postman_collection.json`: partial Postman collection for the API
- `tmp/`: logs and local Chroma persistence

## Setup

### Prerequisites

- Python 3.8+
- MySQL 5.7+ or MySQL 8+
- `pip`

### Install

```bash
git clone <repository-url>
cd airec-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure Environment

Start from the example file:

```bash
cp .env.example .env
```

Core variables already expected by the app:

```env
SECRET_KEY=change-me
FLASK_ENV=development

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=airec_db

JWT_SECRET_KEY=change-me-too
CORS_ORIGINS=*
LOG_LEVEL=INFO

TMDB_API_KEY=

LLM_API_KEY=
LLM_MODEL=gpt-3.5-turbo
LLM_API_URL=https://api.openai.com/v1/chat/completions
```

Additional optional variables used by the current code but not listed in `.env.example` by default:

```env
GOOGLE_API_KEY=
GOOGLE_LLM_MODEL=gemini-2.5-flash

RAG_ENABLED=true
RAG_CHROMA_PATH=/absolute/or/relative/path/to/chroma_db
RAG_COLLECTION_NAME=airec_movies
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_TOP_K=8
RAG_MIN_RATINGS=5

USE_REDIS=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Create The Database

```sql
CREATE DATABASE airec_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Start The API

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

Useful built-in endpoints:

- `GET /`
- `GET /health`
- `GET /swagger/`
- `GET /apispec.json`

Notes:

- `app.py` calls `db.create_all()` at startup, so missing tables are created automatically.
- `run.py` and `passenger_wsgi.py` are provided for WSGI/Passenger deployment.

## API Surface

### System

- `GET /`: API metadata
- `GET /health`: health check

### Authentication

- `POST /api/auth/register`: create a user with optional `favorite_genres`
- `POST /api/auth/login`: returns `access_token`, `refresh_token`, and user payload
- `POST /api/auth/logout`: revoke current JWT
- `POST /api/auth/refresh`: generate a fresh access token

Registration rules enforced by the API:

- valid email format
- password minimum 8 chars
- at least one uppercase letter
- at least one lowercase letter
- at least one digit

### User

- `GET /api/user/profile`: current user profile with recent ratings
- `PUT /api/user/profile`: update `nom`, `prenom`, and `favorite_genres`
- `GET /api/user/ratings`: paginated ratings by current user
- `GET /api/user/preferences`: favorite genres for current user
- `PUT /api/user/preferences`: replace favorite genres list

### Movies

- `GET /api/movies`
  - filters: `page`, `per_page`, `genre`, `year`, `min_rating`, `search`, `sort_by`, `order`
  - `sort_by` supports `title`, `year`, `rating`
- `GET /api/movies/<movie_id>`: single movie with stats
- `GET /api/movies/featured`: top rated, heavily rated movies
- `GET /api/movies/<movie_id>/ratings`: paginated ratings for a movie

### Categories

- `GET /api/categories`: MovieLens-style genre list
- `GET /api/categories/<genre>/movies`
  - filters: `page`, `per_page`, `sort_by`
  - `sort_by` supports `popularity`, `rating`, `title`, `year`

### Ratings

- `POST /api/movies/<movie_id>/ratings`: create or update the authenticated user's rating
- `GET /api/movies/<movie_id>/ratings/user`: get the authenticated user's rating for that movie
- `DELETE /api/movies/<movie_id>/ratings/<rating_id>`: delete the authenticated user's rating

Rating validation:

- numeric value only
- range `0.5` to `5.0`
- increments of `0.5`

### Recommendations

- `GET /api/recommendations/user`: hybrid personalized recommendations for current user
- `GET /api/recommendations/user-segment`: recommendations from precomputed user segment data
- `GET /api/recommendations/segments/status`: status of segment profile tables
- `GET /api/recommendations/category/<genre>`: genre recommendations
- `GET /api/recommendations/home`: `personalized`, `popular`, and `trending` sections
- `GET /api/recommendations/similar/<movie_id>`: similar movies based on overlapping genres

Recommendation behavior in the current code:

- `/user` first tries collaborative filtering
- it then merges segment recommendations when available
- it falls back to popular movies when needed
- `/home` optionally personalizes results when a JWT is present

### Chatbot

- `POST /api/chatbot/query`
  - accepts `message`
  - optional `session_id`
  - works anonymously or with JWT
  - stores conversation history in `chatbot_sessions`
- `GET /api/chatbot/history`: authenticated history listing, with optional `session_id`
- `DELETE /api/chatbot/session/<session_id>`: delete one authenticated user's session
- `POST /api/chatbot/search`: search by natural-language description
- `GET /api/chatbot/rag/status`: whether semantic RAG is available
- `POST /api/chatbot/rag/reindex`: rebuild the Chroma index from database content

Chatbot behavior in the current code:

- intent detection is rule-based and supports French and English keywords
- the orchestrator can use:
  - SQL filtering by genre/year/rating
  - popularity retrieval
  - "similar to" lookup
  - semantic search through RAG when enabled
- the LLM is instructed to recommend only movies from the retrieved catalog
- if the LLM is unavailable, the service returns a fallback French response

## Data Model

Current SQLAlchemy tables and relationships:

- `users`
  - fields: `id`, `email`, `password_hash`, `nom`, `prenom`, `is_imported`, timestamps
- `genres`
  - normalized genre catalog
- `movies`
  - fields: `id`, `title`, `release_year`, `description`, `poster_url`, `backdrop_url`, `tmdb_id`, `imdb_id`, `created_at`
- `ratings`
  - fields: `id`, `user_id`, `movie_id`, `rating`, `timestamp`
  - unique constraint on `(user_id, movie_id)`
- `movie_genres`
  - many-to-many association between `movies` and `genres`
- `user_favorite_genres`
  - many-to-many association between `users` and `genres`
- `chatbot_sessions`
  - stores conversation history as JSON text
- `token_blacklist`
  - revoked JWT identifiers
- `user_recommendation_profiles`
  - one row per user segment assignment and profile vector
- `type_recommendations`
  - precomputed ranked movie recommendations per segment and model version

Important model notes:

- favorite genres are no longer stored in a `user_preferences` table
- imported MovieLens users are marked with `is_imported=True`
- imported users are blocked from authenticating through `/api/auth/login`

## Services Overview

### `services/recommendation_engine.py`

- collaborative filtering from overlapping ratings
- segment-based fallback via `user_recommendation_profiles` and `type_recommendations`
- genre recommendations with rating-count thresholds
- home feed composition

### `services/chat_retrieval_service.py`

- SQL retrieval with rating stats subqueries
- search by criteria, title, popularity, similarity, and IDs

### `services/chat_orchestrator.py`

- detects user intent from text
- routes requests to retrieval or RAG
- builds a constrained prompt for the LLM

### `services/llm_service.py`

- OpenAI-compatible HTTP client
- Google Gemini fallback if configured
- fallback text if no provider is available

### `services/rag_service.py`

- optional Chroma persistent store in `tmp/chroma_db` by default
- embeddings via `sentence-transformers`
- semantic search over movie title, genres, year, and description

## Operational Scripts

### Database Management

```bash
python scripts/init_db.py init
python scripts/init_db.py reset
python scripts/init_db.py seed
```

- `init`: create all tables
- `reset`: drop and recreate all tables after interactive confirmation
- `seed`: insert sample users, genres, movies, and ratings

### Import MovieLens Data

The importer currently targets MovieLens 1M style `.dat` files, not CSV.

```bash
python scripts/import_movielens.py /path/to/ml-1m
```

Or:

```bash
python scripts/import_movielens.py \
  --movies /path/to/movies.dat \
  --ratings /path/to/ratings.dat \
  --users /path/to/users.dat \
  --limit-ratings 100000
```

Behavior:

- clears imported MovieLens data after confirmation
- imports normalized genres
- imports movies
- imports synthetic imported users
- imports ratings with timestamp preservation

### Enrich Movies With TMDB

```bash
python scripts/fetch_posters.py --limit 100
```

This fills missing values such as:

- `tmdb_id`
- `description`
- `poster_url`
- `backdrop_url`
- optionally `release_year`

### Build Segment Recommendations

```bash
python scripts/build_segment_recommendations.py --clusters 11 --top-n 500 --model-version v1
```

Optional automatic cluster search:

```bash
python scripts/build_segment_recommendations.py --auto-k --max-k 20
```

This script:

- computes user genre-preference vectors from ratings
- clusters users with KMeans
- ranks movies per segment
- stores results in `user_recommendation_profiles` and `type_recommendations`

### Rebuild The RAG Index

```bash
python scripts/rebuild_rag_index.py
```

### Inspect Logs

```bash
python scripts/view_logs.py --tail
python scripts/view_logs.py --errors
python scripts/view_logs.py --stats
python scripts/view_logs.py --search "GET /api/recommendations"
```

Logs are written to `tmp/app.log` with rotation.

## API Examples

### Register

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "Password123",
    "nom": "Doe",
    "prenom": "John",
    "favorite_genres": ["Action", "Sci-Fi"]
  }'
```

### Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "Password123"
  }'
```

### Browse Movies

```bash
curl "http://localhost:5000/api/movies?genre=Sci-Fi&min_rating=4&sort_by=rating&order=desc"
```

### Create Or Update A Rating

```bash
curl -X POST http://localhost:5000/api/movies/1/ratings \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"rating": 4.5}'
```

### Personalized Recommendations

```bash
curl http://localhost:5000/api/recommendations/user \
  -H "Authorization: Bearer <access_token>"
```

### Chatbot Query

```bash
curl -X POST http://localhost:5000/api/chatbot/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Je cherche un film d action recent et bien note"
  }'
```

## Swagger And Postman

- Swagger UI: `http://localhost:5000/swagger/`
- OpenAPI spec JSON: `http://localhost:5000/apispec.json`
- Postman collection: `postman_collection.json`

The Postman collection currently covers the main flows, but it does not yet include every newer endpoint exposed by the codebase, especially some segment and RAG maintenance routes.

## Current Behavior Notes

- Segment-based recommendation endpoints only become useful after running `scripts/build_segment_recommendations.py`.
- RAG endpoints only become useful when `RAG_ENABLED=true` and embedding dependencies are installed.
- Anonymous chatbot requests create sessions with `user_id = null`.
- The codebase includes Redis configuration, but no route currently uses Redis directly.

## Additional Docs

More implementation notes are available under `docs/`, especially:

- `docs/QUICKSTART.md`
- `docs/API_TESTING.md`
- `docs/RAG_QUICK_START.md`
- `docs/LOGGING.md`
