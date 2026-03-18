# AiRec API - AI Agent Instructions

## Project Overview
Flask-based movie recommendation API with collaborative filtering, JWT auth, and LLM-powered chatbot. Uses MovieLens dataset with MySQL/SQLAlchemy ORM.

## Architecture & Key Components

### Application Factory Pattern
- Entry point: `app.py` exports `app` singleton via `create_app(config_name)`
- Config loaded from `config.py` classes (Development/Production/Testing)
- Database initialized with `db.init_app(app)` in factory, models in `models/__init__.py`
- Never import `app` before calling `create_app()` - causes circular imports

### Blueprint Structure
All routes follow blueprint pattern registered in `app.py`:
- `routes/auth.py` - Registration, login, logout with JWT blacklist
- `routes/movies.py` - Movie catalog, search, details
- `routes/ratings.py` - User ratings (0.5-5.0 scale in 0.5 increments)
- `routes/recommendations.py` - Collaborative filtering engine
- `routes/chatbot.py` - LLM conversation with movie context
- `routes/categories.py` - Genre-based browsing
- `routes/user.py` - Profile management, preferences

All API routes use `/api/<blueprint_name>` prefix.

### Data Models (models/__init__.py)
- **User**: Email (unique), password_hash, nom/prenom, is_imported flag (for MovieLens users), many-to-many with favorite genres
- **Movie**: Title, release_year, poster_url, tmdb_id, many-to-many with genres via movie_genres table
- **Genre**: Name (unique), many-to-many with movies and users
- **Rating**: user_id, movie_id, rating (float 0.5-5.0), timestamp
- **TokenBlacklist**: JWT revocation via jti tracking
- **ChatbotSession**: Conversation history storage

**Junction tables:**
- `movie_genres` - Links movies to genres
- `user_favorite_genres` - Links users to their favorite genres

All models have `to_dict()` methods for JSON serialization with optional `include_stats` flags.

**Important**: MovieLens imported users have `is_imported=True` and cannot login (blocked in auth route).

### Authentication Pattern
```python
from utils.jwt_handler import token_required, get_current_user

@blueprint.route('/protected')
@token_required  # Custom decorator checking blacklist
def protected_route():
    user_id = get_current_user()  # Returns int(jwt_identity)
```

JWT tokens stored in `Authorization: Bearer <token>` header. Logout adds jti to TokenBlacklist table.

### Recommendation Engine (services/recommendation_engine.py)
Collaborative filtering via `_find_similar_users()`:
1. Find users with overlapping ratings
2. Get their highly-rated movies (≥4.0 stars)
3. Exclude user's already-rated movies
4. Fallback to `get_popular_movies()` if insufficient data

Genre recommendations use Genre model with many-to-many relationships.

### LLM Service (services/llm_service.py)
Singleton `llm_service` initialized in `create_app()` with:
- `LLM_API_KEY`, `LLM_API_URL`, `LLM_MODEL` from config
- OpenAI-compatible API interface (works with Claude, Mistral)
- Stateless requests - conversation history managed by chatbot route

Chatbot route builds movie context string from database queries before LLM call.

## Critical Workflows

### Database Operations
```bash
# Initialize/reset database
python scripts/init_db.py init    # Create tables
python scripts/init_db.py reset   # Drop and recreate
python scripts/init_db.py seed    # Add sample data

# Import MovieLens 1M dataset (.dat files with :: delimiter)
# IMPORTANT: Clears existing MovieLens data before import
# Creates Genre table, movie_genres junction table, flags users as imported
python scripts/import_movielens.py /path/to/ml-1m/
# or specify individual files:
python scripts/import_movielens.py --movies movies.dat --ratings ratings.dat --users users.dat

# Fetch TMDB posters (requires TMDB_API_KEY)
python scripts/fetch_posters.py
```

### Running Locally
```bash
python run.py  # Development server on port 5000
```

### Deployment (Passenger WSGI)
Application exported as `application` in `passenger_wsgi.py` for cPanel/Passenger hosting. Uses `tmp/restart.txt` touch-file for zero-downtime restarts.

### Logging
Rotating logs in `tmp/app.log` (10MB max, 5 backups). Configured per-environment in `config.py`:
- Development: Console + file, DEBUG level, SQL echo enabled
- Production: File only, INFO level, no SQL echo

View logs: `python scripts/view_logs.py`

## Project-Specific Conventions

### Validation Pattern
All user input validated via `utils/validators.py`:
- `validate_email_format()` - Uses email-validator library
- `validate_password_strength()` - Min 8 chars, uppercase, lowercase, digit
- `validate_rating()` - 0.5-5.0 in 0.5 increments only
- `sanitize_string()` - XSS prevention, max_length enforcement

Always validate before database operations, return 400 with error message.

### Error Response Format
```python
return jsonify({'error': 'Descriptive message'}), <status_code>
```

Success responses vary by endpoint but typically:
```python
return jsonify({'data': items, 'total': count}), 200
```

### Configuration
All secrets/environment config via `.env` file loaded by `python-dotenv`. Never hardcode:
- Database credentials (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
- API keys (TMDB_API_KEY, LLM_API_KEY)
- JWT secrets (SECRET_KEY, JWT_SECRET_KEY)

Access via `app.config['KEY_NAME']` or `current_app.config['KEY_NAME']` in routes.

### Swagger Documentation
Flasgger provides `/swagger/` UI. Document endpoints with YAML docstrings:
```python
"""
Endpoint description
---
tags:
  - Tag Name
parameters:
  - in: body
    name: body
    schema:
      type: object
responses:
  200:
    description: Success
"""
```

## External Dependencies
- **TMDB API**: Movie posters/metadata fetch via `scripts/fetch_posters.py`
- **MySQL**: Required (SQLite only for testing config)
- **Redis**: Optional caching layer (USE_REDIS=true in config)
- **LLM APIs**: OpenAI, Claude, or compatible endpoint

## Common Pitfalls
- Genre filtering now uses Genre model with movie.genres_list (many-to-many) - update old code using genres string field
- Rating validation fails silently if not in 0.5 increments (2.3 rejected, 2.5 accepted)
- JWT blacklist check happens in decorator, not Flask-JWT-Extended - don't skip `@token_required`
- LLM service returns error strings on failure, not exceptions - check response content
- MovieLens import expects `.dat` format with `::` delimiter (MovieLens 1M dataset)
- MovieLens 1M uses 1-5 whole star ratings (compatible with API's 0.5-5.0 scale)
- Import script clears MovieLens data before import and flags users with is_imported=True
- Imported users cannot login (blocked with 403 error) - they're for recommendation data only
- Import script uses bulk operations for performance - 6K users + 1M ratings takes ~10 min
