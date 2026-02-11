# AiRec API - Movie Recommendation System

A comprehensive Flask-based REST API for movie recommendations with AI-powered chatbot integration.

## Features

- **User Authentication**: JWT-based authentication with secure password hashing
- **Movie Database**: Complete movie catalog with ratings and metadata
- **Rating System**: User movie ratings (0.5 to 5.0 scale)
- **Recommendation Engine**: 
  - Collaborative filtering based on user similarities
  - Genre-based recommendations
  - Personalized home page recommendations
- **AI Chatbot**: LLM-powered conversational movie recommendations
- **RESTful API**: Complete REST API with Swagger documentation
- **MySQL Database**: Optimized database schema with indexes
- **Comprehensive Logging**: Automatic log rotation and tracking in `tmp/` directory

## Technology Stack

- **Framework**: Flask 3.0
- **Database**: MySQL (via SQLAlchemy ORM)
- **Authentication**: JWT (Flask-JWT-Extended)
- **Documentation**: Swagger/Flasgger
- **External APIs**: TMDB for movie posters/metadata
- **AI/LLM**: OpenAI/Claude/Mistral integration for chatbot

## Installation

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- pip

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd airec-api
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Create MySQL database**
```sql
CREATE DATABASE airec_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. **Initialize database**
```bash
python app.py
```

## Configuration

Edit `.env` file with your settings:

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=airec_db

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# External APIs
TMDB_API_KEY=your-tmdb-api-key
LLM_API_KEY=your-llm-api-key
LLM_MODEL=gpt-3.5-turbo

# Logging
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=*
```

## Running the Application

### Development Mode
```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Production Mode (with Passenger)
The application is configured to work with Passenger WSGI. The `passenger_wsgi.py` and `run.py` files are configured for deployment.

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:5000/swagger/
- **API Spec**: http://localhost:5000/apispec.json

## Data Import

### Import MovieLens Dataset

1. **Download MovieLens dataset**
```bash
wget https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
unzip ml-latest-small.zip
```

2. **Import movies and ratings**
```bash
python scripts/import_movielens.py \
  --movies ml-latest-small/movies.csv \
  --ratings ml-latest-small/ratings.csv \
  --format csv
```

For large datasets, limit ratings:
```bash
python scripts/import_movielens.py \
  --movies movies.csv \
  --ratings ratings.csv \
  --limit-ratings 100000
```

### Fetch Movie Posters from TMDB

After importing movies, fetch posters and metadata:
```bash
python scripts/fetch_posters.py --limit 100
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/refresh` - Refresh access token

### User Profile
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update profile
- `GET /api/user/ratings` - Get user ratings
- `GET /api/user/preferences` - Get preferences
- `PUT /api/user/preferences` - Update preferences

### Movies
- `GET /api/movies` - List movies (with filters)
- `GET /api/movies/:id` - Get movie details
- `GET /api/movies/featured` - Get featured movies
- `GET /api/movies/:id/ratings` - Get movie ratings

### Categories
- `GET /api/categories` - List all genres
- `GET /api/categories/:genre/movies` - Get movies by genre

### Ratings
- `POST /api/movies/:id/ratings` - Create/update rating
- `GET /api/movies/:id/ratings/user` - Get user's rating
- `DELETE /api/movies/:id/ratings/:rating_id` - Delete rating

### Recommendations
- `GET /api/recommendations/user` - Personalized recommendations
- `GET /api/recommendations/category/:genre` - Genre recommendations
- `GET /api/recommendations/home` - Home page recommendations
- `GET /api/recommendations/similar/:id` - Similar movies

### Chatbot
- `POST /api/chatbot/query` - Send message to chatbot
- `GET /api/chatbot/history` - Get conversation history
- `DELETE /api/chatbot/session/:id` - Delete session
- `POST /api/chatbot/search` - Search movies by description

## Database Schema

### Tables

**users**
- id, email, password_hash, nom, prenom
- created_at, updated_at

**movies**
- id, title, genres, release_year
- description, poster_url, backdrop_url
- tmdb_id, imdb_id, created_at

**ratings**
- id, user_id, movie_id, rating, timestamp
- Unique constraint: (user_id, movie_id)

**user_preferences**
- id, user_id, favorite_genres (JSON)
- created_at, updated_at

**chatbot_sessions**
- id, user_id, conversation_history (JSON)
- created_at, updated_at

**token_blacklist**
- id, jti, created_at

## Example Usage

### Register User
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

### Get Recommendations
```bash
curl -X GET http://localhost:5000/api/recommendations/user \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Rate a Movie
```bash
curl -X POST http://localhost:5000/api/movies/1/ratings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rating": 4.5}'
```

### Chat with AI
```bash
curl -X POST http://localhost:5000/api/chatbot/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want a fun action movie for tonight"
  }'
```

## Project Structure

```
airec-api/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── run.py                      # WSGI entry point
├── passenger_wsgi.py           # Passenger WSGI config
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── models/
│   └── __init__.py            # Database models
├── routes/
│   ├── auth.py                # Authentication routes
│   ├── user.py                # User profile routes
│   ├── movies.py              # Movie routes
│   ├── categories.py          # Category routes
│   ├── ratings.py             # Rating routes
│   ├── recommendations.py     # Recommendation routes
│   └── chatbot.py             # Chatbot routes
├── services/
│   ├── recommendation_engine.py  # Recommendation logic
│   └── llm_service.py            # LLM integration
├── utils/
│   ├── jwt_handler.py         # JWT utilities
│   └── validators.py          # Input validation
└── scripts/
    ├── import_movielens.py    # Data import script
    ├── fetch_posters.py       # Poster fetching script
    ├── init_db.py             # Database initialization
    └── view_logs.py           # Log viewer utility
```

## Logging

### Overview
All application logs are automatically saved to `tmp/app.log` with automatic rotation:
- **Log location**: `tmp/app.log`
- **Rotation**: Automatic at 10MB
- **Backups**: 5 files retained (~50MB total)
- **Levels**: DEBUG, INFO, WARNING, ERROR

### Configuration
Set log level in `.env`:
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### View Logs
```bash
# Follow live logs
tail -f tmp/app.log

# View last 100 lines
python scripts/view_logs.py --lines 100

# Show only errors
python scripts/view_logs.py --errors

# Follow in real-time
python scripts/view_logs.py --tail

# Show statistics
python scripts/view_logs.py --stats

# Search for specific term
python scripts/view_logs.py --search "user@example.com"
```

### What Gets Logged
- ✅ Application startup and configuration
- ✅ All authentication events
- ✅ HTTP requests and responses (DEBUG level)
- ✅ Database operations
- ✅ Error stack traces
- ✅ External API calls
- ✅ User actions

For detailed logging documentation, see [LOGGING.md](LOGGING.md)

## Security Features

- Password hashing with bcrypt
- JWT token authentication
- Token blacklisting for logout
- Input validation and sanitization
- SQL injection protection (SQLAlchemy ORM)
- CORS configuration
- Rate limiting ready

## Performance Optimization

- Database indexes on frequently queried fields
- Pagination for large result sets
- Batch processing for imports
- Optional Redis caching (configurable)
- Optimized SQL queries with proper joins

## Future Enhancements

- [ ] Redis caching for recommendations
- [ ] Rate limiting implementation
- [ ] Advanced ML recommendation models
- [ ] Social features (follow users, share lists)
- [ ] Email verification
- [ ] Password reset functionality
- [ ] Admin panel
- [ ] Movie watchlists
- [ ] User reviews (text)

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.

## Contributors

- Backend API development
- Database design and optimization
- ML recommendation engine
- Swagger API documentation
