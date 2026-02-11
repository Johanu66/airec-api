# AiRec API - Quick Start Guide

## Setup in 5 Minutes

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Database
Edit `.env` file (or create from `.env.example`):
```bash
cp .env.example .env
```

Update these essential settings:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=airec_db
SECRET_KEY=your-random-secret-key
JWT_SECRET_KEY=your-random-jwt-key
```

### 3. Create Database
```sql
CREATE DATABASE airec_db;
```

### 4. Initialize Database
```bash
python scripts/init_db.py init
```

### 5. Seed Sample Data (Optional)
```bash
python scripts/init_db.py seed
```

This creates:
- 3 test users (alice@example.com, bob@example.com, charlie@example.com)
- 5 sample movies
- Sample ratings
- Password for all users: `Password123`

### 6. Run the Application
```bash
python run.py
```

Visit http://localhost:5000 to see the API running!

## Test the API

### Using Swagger UI
Open http://localhost:5000/swagger/ in your browser for interactive API documentation.

### Using curl

**1. Register a user:**
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123",
    "nom": "Test",
    "prenom": "User"
  }'
```

**2. Login:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123"
  }'
```

Copy the `access_token` from the response.

**3. Get movies:**
```bash
curl http://localhost:5000/api/movies
```

**4. Get recommendations (requires token):**
```bash
curl http://localhost:5000/api/recommendations/user \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Import Real Data (Optional)

### MovieLens Dataset

**1. Download dataset:**
```bash
wget https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
unzip ml-latest-small.zip
```

**2. Import data:**
```bash
python scripts/import_movielens.py \
  --movies ml-latest-small/movies.csv \
  --ratings ml-latest-small/ratings.csv \
  --format csv
```

**3. Fetch movie posters (requires TMDB API key):**

Get a free API key from https://www.themoviedb.org/settings/api

Add to `.env`:
```env
TMDB_API_KEY=your-tmdb-api-key
```

Then run:
```bash
python scripts/fetch_posters.py --limit 100
```

## Enable AI Chatbot (Optional)

To enable the AI-powered chatbot feature:

**1. Get an API key:**
- OpenAI: https://platform.openai.com/api-keys
- Or use another LLM provider (Claude, Mistral, Gemini, etc.)

**2. Add to `.env`:**
```env
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-3.5-turbo
LLM_API_URL=https://api.openai.com/v1/chat/completions
```

**3. Test chatbot:**
```bash
curl -X POST http://localhost:5000/api/chatbot/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want a fun action movie"
  }'
```

## Common Issues

### MySQL Connection Error
- Ensure MySQL is running: `sudo systemctl start mysql`
- Check credentials in `.env`
- Verify database exists: `SHOW DATABASES;`

### Import Permission Error
- Make sure scripts are executable: `chmod +x scripts/*.py`
- Use `python` or `python3` depending on your system

### Port Already in Use
- Change port in `.env`: `PORT=8000`
- Or kill process using port 5000: `lsof -ti:5000 | xargs kill`

## Next Steps

1. Explore the Swagger documentation: http://localhost:5000/swagger/
2. Import MovieLens data for realistic recommendations
3. Configure TMDB API for movie posters
4. Set up LLM API for chatbot features
5. Customize recommendation algorithms in `services/recommendation_engine.py`

## Production Deployment

For production deployment:
1. Set `FLASK_ENV=production` in `.env`
2. Use a production WSGI server (Gunicorn, uWSGI, or Passenger)
3. Set up HTTPS
4. Configure proper CORS origins
5. Enable Redis for caching (optional)
6. Set strong SECRET_KEY and JWT_SECRET_KEY

Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Support

- Check README.md for full documentation
- API docs at /swagger/
- GitHub issues for bugs

Happy coding! 🎬🍿
