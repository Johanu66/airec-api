# API Testing Guide

## Overview

This guide provides examples for testing all AiRec API endpoints using curl, Python, and JavaScript.

## Base URL
```
http://localhost:5000
```

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## 1. Authentication Endpoints

### Register User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "Password123",
    "nom": "Doe",
    "prenom": "John",
    "favorite_genres": ["Action", "Sci-Fi"]
  }'
```

**Python:**
```python
import requests

response = requests.post(
    'http://localhost:5000/api/auth/register',
    json={
        'email': 'john@example.com',
        'password': 'Password123',
        'nom': 'Doe',
        'prenom': 'John',
        'favorite_genres': ['Action', 'Sci-Fi']
    }
)
print(response.json())
```

**JavaScript:**
```javascript
fetch('http://localhost:5000/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'john@example.com',
    password: 'Password123',
    nom: 'Doe',
    prenom: 'John',
    favorite_genres: ['Action', 'Sci-Fi']
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "Password123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "john@example.com",
    "nom": "Doe",
    "prenom": "John",
    "ratings_count": 0
  }
}
```

### Logout
```bash
TOKEN="your_access_token"
curl -X POST http://localhost:5000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

---

## 2. Movie Endpoints

### Get All Movies
```bash
curl "http://localhost:5000/api/movies?page=1&per_page=20"
```

**With filters:**
```bash
curl "http://localhost:5000/api/movies?genre=Action&year=2020&min_rating=4.0&sort_by=rating&order=desc"
```

**Python:**
```python
params = {
    'page': 1,
    'per_page': 20,
    'genre': 'Action',
    'min_rating': 4.0,
    'sort_by': 'rating'
}
response = requests.get('http://localhost:5000/api/movies', params=params)
movies = response.json()
```

### Get Movie Details
```bash
curl http://localhost:5000/api/movies/1
```

### Search Movies
```bash
curl "http://localhost:5000/api/movies?search=Matrix"
```

### Get Featured Movies
```bash
curl "http://localhost:5000/api/movies/featured?limit=10"
```

---

## 3. Rating Endpoints

### Rate a Movie
```bash
TOKEN="your_access_token"
curl -X POST http://localhost:5000/api/movies/1/ratings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rating": 4.5}'
```

**Python:**
```python
headers = {'Authorization': f'Bearer {token}'}
response = requests.post(
    'http://localhost:5000/api/movies/1/ratings',
    headers=headers,
    json={'rating': 4.5}
)
```

### Get Movie Ratings
```bash
curl "http://localhost:5000/api/movies/1/ratings?page=1"
```

### Get User's Rating for Movie
```bash
TOKEN="your_access_token"
curl http://localhost:5000/api/movies/1/ratings/user \
  -H "Authorization: Bearer $TOKEN"
```

---

## 4. User Profile Endpoints

### Get Profile
```bash
TOKEN="your_access_token"
curl http://localhost:5000/api/user/profile \
  -H "Authorization: Bearer $TOKEN"
```

### Update Profile
```bash
TOKEN="your_access_token"
curl -X PUT http://localhost:5000/api/user/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Smith",
    "prenom": "Jane",
    "favorite_genres": ["Comedy", "Drama", "Romance"]
  }'
```

### Get User Ratings
```bash
TOKEN="your_access_token"
curl "http://localhost:5000/api/user/ratings?page=1&per_page=20" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. Category Endpoints

### Get All Genres
```bash
curl http://localhost:5000/api/categories
```

**Response:**
```json
{
  "genres": [
    "Action", "Adventure", "Animation", "Children's",
    "Comedy", "Crime", "Documentary", "Drama",
    "Fantasy", "Film-Noir", "Horror", "Musical",
    "Mystery", "Romance", "Sci-Fi", "Thriller",
    "War", "Western"
  ]
}
```

### Get Movies by Genre
```bash
curl "http://localhost:5000/api/categories/Action/movies?page=1&sort_by=rating"
```

**Python:**
```python
genre = 'Action'
params = {'page': 1, 'sort_by': 'rating'}
response = requests.get(
    f'http://localhost:5000/api/categories/{genre}/movies',
    params=params
)
```

---

## 6. Recommendation Endpoints

### Get Personalized Recommendations
```bash
TOKEN="your_access_token"
curl "http://localhost:5000/api/recommendations/user?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**JavaScript:**
```javascript
const token = 'your_access_token';
fetch('http://localhost:5000/api/recommendations/user?limit=10', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(res => res.json())
.then(data => console.log(data.recommendations));
```

### Get Home Page Recommendations
```bash
curl http://localhost:5000/api/recommendations/home
```

**Response structure:**
```json
{
  "personalized": [...],
  "popular": [...],
  "trending": [...]
}
```

### Get Genre Recommendations
```bash
curl http://localhost:5000/api/recommendations/category/Sci-Fi?limit=10
```

### Get Similar Movies
```bash
curl http://localhost:5000/api/recommendations/similar/1?limit=10
```

---

## 7. Chatbot Endpoints

### Send Query to Chatbot
```bash
curl -X POST http://localhost:5000/api/chatbot/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want a fun action movie for tonight"
  }'
```

**With session continuation:**
```bash
curl -X POST http://localhost:5000/api/chatbot/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What about something with comedy?",
    "session_id": 1
  }'
```

**Python:**
```python
response = requests.post(
    'http://localhost:5000/api/chatbot/query',
    json={
        'message': 'I want a fun action movie for tonight'
    }
)
data = response.json()
session_id = data['session_id']
recommendations = data.get('recommendations', [])
```

### Search Movies by Natural Language
```bash
curl -X POST http://localhost:5000/api/chatbot/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "movies about space exploration",
    "limit": 10
  }'
```

### Get Chatbot History (Authenticated)
```bash
TOKEN="your_access_token"
curl http://localhost:5000/api/chatbot/history \
  -H "Authorization: Bearer $TOKEN"
```

---

## Complete Workflow Example

### Python Complete Workflow
```python
import requests

BASE_URL = 'http://localhost:5000'

# 1. Register
register_data = {
    'email': 'test@example.com',
    'password': 'Password123',
    'nom': 'Test',
    'prenom': 'User'
}
response = requests.post(f'{BASE_URL}/api/auth/register', json=register_data)
print("Registered:", response.json())

# 2. Login
login_data = {'email': 'test@example.com', 'password': 'Password123'}
response = requests.post(f'{BASE_URL}/api/auth/login', json=login_data)
token = response.json()['access_token']
print("Token obtained")

# 3. Get movies
response = requests.get(f'{BASE_URL}/api/movies?per_page=5')
movies = response.json()['movies']
print(f"Found {len(movies)} movies")

# 4. Rate a movie
headers = {'Authorization': f'Bearer {token}'}
movie_id = movies[0]['id']
response = requests.post(
    f'{BASE_URL}/api/movies/{movie_id}/ratings',
    headers=headers,
    json={'rating': 4.5}
)
print("Rated movie:", response.json())

# 5. Get recommendations
response = requests.get(
    f'{BASE_URL}/api/recommendations/user',
    headers=headers
)
recommendations = response.json()['recommendations']
print(f"Got {len(recommendations)} recommendations")

# 6. Chat with bot
response = requests.post(
    f'{BASE_URL}/api/chatbot/query',
    json={'message': 'I want a comedy movie'}
)
chat_response = response.json()
print("Chatbot:", chat_response['response'])
```

### JavaScript Complete Workflow
```javascript
const BASE_URL = 'http://localhost:5000';
let token = '';

// 1. Register and Login
async function authenticate() {
  const registerRes = await fetch(`${BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'test@example.com',
      password: 'Password123',
      nom: 'Test',
      prenom: 'User'
    })
  });
  
  const loginRes = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'test@example.com',
      password: 'Password123'
    })
  });
  
  const data = await loginRes.json();
  token = data.access_token;
  return token;
}

// 2. Get and rate movies
async function rateMovies() {
  const moviesRes = await fetch(`${BASE_URL}/api/movies?per_page=5`);
  const moviesData = await moviesRes.json();
  const firstMovie = moviesData.movies[0];
  
  const ratingRes = await fetch(`${BASE_URL}/api/movies/${firstMovie.id}/ratings`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ rating: 4.5 })
  });
  
  return await ratingRes.json();
}

// 3. Get recommendations
async function getRecommendations() {
  const res = await fetch(`${BASE_URL}/api/recommendations/user`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await res.json();
}

// Run workflow
authenticate()
  .then(rateMovies)
  .then(getRecommendations)
  .then(data => console.log('Recommendations:', data))
  .catch(err => console.error('Error:', err));
```

---

## Error Handling

### Common HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Not authorized for this resource
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists (e.g., duplicate email)
- `500 Internal Server Error` - Server error

### Error Response Format
```json
{
  "error": "Description of the error"
}
```

---

## Tips for Testing

1. **Use Postman Collection**: Import `postman_collection.json` for easy testing
2. **Save Token**: Store the access token from login to use in subsequent requests
3. **Check Swagger**: Visit `/swagger/` for interactive API documentation
4. **Use Variables**: Store base URL and token in environment variables
5. **Rate Limiting**: Be mindful of rate limits when making many requests

## Troubleshooting

### 401 Unauthorized
- Token expired (valid for 24 hours)
- Token not included in Authorization header
- Token format incorrect (should be "Bearer TOKEN")

### 404 Not Found
- Wrong endpoint URL
- Resource ID doesn't exist
- Check API documentation for correct paths

### 500 Internal Server Error
- Check server logs
- Database connection issues
- Missing environment variables

---

For more details, check:
- README.md - Full documentation
- /swagger/ - Interactive API docs
- QUICKSTART.md - Quick setup guide
