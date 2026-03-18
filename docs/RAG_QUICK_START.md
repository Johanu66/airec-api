# AiRec RAG Integration - Quick Reference

## What Changed?

The chatbot now has **Retrieval-Augmented Generation (RAG)** with semantic search:

```
❌ OLD: Simple recommendation_engine → Random results
✅ NEW: Intent Analysis → Smart Retrieval (SQL or RAG) → LLM Response
```

---

## Key Features

### 1. **Intent-Aware Routing**
Automatically detects what user wants:
- **Criteria Search**: "Action movies from 2020" → Filters by genre + year
- **Popular**: "Show me good movies" → Top-rated movies
- **Similar**: "Like Die Hard?" → Similar genre movies  
- **Semantic**: "Something intense" → RAG embeddings search
- **General**: "What's new?" → Popular movies + LLM commentary

### 2. **Dual LLM Support**
- **Primary**: Google Gemini 2.5-flash (faster, better)
- **Fallback**: OpenAI gpt-3.5-turbo (if Gemini unavailable)

### 3. **Graceful Degradation**
If anything breaks:
- No movies in DB? → Returns empty list
- RAG unavailable? → Falls back to SQL queries
- LLM fails? → Returns error message politely

---

## Configuration

### Environment Variables (`.env`)
```bash
# LLM Provider
GOOGLE_API_KEY=your-google-api-key  # Your Gemini API key
GOOGLE_LLM_MODEL=gemini-2.5-flash

# RAG Settings
RAG_ENABLED=true                                        # Enable/disable RAG
RAG_CHROMA_PATH=/home/tqffjfwm/airec-api/tmp/chroma_db # Where to store embeddings
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2                   # Embedding model
RAG_TOP_K=8                                             # Number of results
RAG_MIN_RATINGS=5                                       # Min ratings to index
```

---

## API Endpoints

### Chat Query (Your Main Endpoint)
```bash
POST /api/chatbot/query
Content-Type: application/json

{
  "message": "Show me action movies from 2020"
}

Response:
{
  "response": "Here are some action movies from 2020...",
  "session_id": 1,
  "intent": { "type": "criteria", "genre": "Action", ... },
  "recommendations": [
    { "id": 123, "title": "Movie", "genres": ["Action"], ... },
    ...
  ]
}
```

### Search Only (No LLM)
```bash
POST /api/chatbot/search
{
  "query": "intense action thrillers"
}

Response:
{
  "movies": [...]
}
```

### Check RAG Status
```bash
GET /api/chatbot/rag/status

Response:
{
  "rag_available": true
}
```

### Rebuild RAG Index (Admin)
```bash
POST /api/chatbot/rag/reindex

Response:
{
  "indexed": 1250,
  "status": "ok"
}
```

Or via terminal:
```bash
python scripts/rebuild_rag_index.py
```

---

## Testing

### Quick Test
```bash
# Start server
python run.py

# In another terminal
curl -X POST http://localhost:5000/api/chatbot/query \
  -H "Content-Type: application/json" \
  -d '{"message": "action movies"}'
```

### Programmatic Test
```python
from app import create_app

app = create_app('development')
with app.app_context():
    client = app.test_client()
    response = client.post('/api/chatbot/query', 
        json={"message": "action movies 2020"})
    print(response.get_json())
```

---

## Common Use Cases

### Add Database of Movies
```bash
# Option 1: Import MovieLens (large dataset)
python scripts/import_movielens.py /path/to/ml-1m/

# Option 2: Manual SQL insert (small dataset)
# See database schema in models/__init__.py
```

### Rebuild Embeddings
```bash
python scripts/rebuild_rag_index.py
# Takes ~5 minutes for 1000 movies
```

### Disable RAG (Use SQL Only)
```bash
# In .env:
RAG_ENABLED=false

# Queries still work but only via SQL filters
```

### Switch to OpenAI Only
```bash
# In .env:
# Remove or comment out GOOGLE_API_KEY
# System will automatically use gpt-3.5-turbo
```

---

## Architecture

### Services
- **`ChatOrchestrator`**: Intent detection + routing
- **`ChatRetrievalService`**: Database queries (SQL-based)
- **`RAGService`**: Semantic search (embeddings-based)
- **`LLMService`**: Response generation (Gemini or OpenAI)

### Data Flow
```
Message → Orchestrator → Retrieval (SQL or RAG) → LLM → Response
                ↓
          ChatbotSession (persisted)
```

### Database Tables Used
- `chatbot_sessions` - Conversation history
- `movies` - Movie catalog
- `genres` - Genre list
- `movie_genres` - Movie-genre relationships
- `ratings` - User ratings (for popularity ranking)

---

## Performance Tips

### 1. Faster Responses
- Use Gemini API (faster than OpenAI)
- Reduce `RAG_TOP_K` from 8 to 5
- Disable RAG if not needed

### 2. Better Results
- Import real MovieLens data
- Increase `RAG_TOP_K` to 10-15
- Keep `RAG_MIN_RATINGS` reasonable (5-10)

### 3. Monitor Performance
```bash
tail -f tmp/app.log | grep "duration"
```

---

## Troubleshooting

### "No movies found"
**Cause**: Database is empty  
**Fix**:
```bash
python scripts/import_movielens.py /path/to/ml-1m/
```

### "RAG unavailable"
**Cause**: Chroma database not initialized  
**Fix**:
```bash
python scripts/rebuild_rag_index.py
```

### Slow responses (10+ seconds)
**Cause**: LLM API latency or RAG embedding computation  
**Fix**:
1. Check internet connection
2. Reduce `RAG_TOP_K` to 5
3. Switch to Gemini if using OpenAI

### API Key errors
```bash
# Check .env exists
ls -la .env

# Check key is set
grep GOOGLE_API_KEY .env

# Test key validity
curl -H "Authorization: Bearer YOUR_KEY" \
  https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash
```

---

## File Locations

```
📁 /home/tqffjfwm/airec-api/
  ├── services/
  │   ├── chat_orchestrator.py      ← Intent routing
  │   ├── chat_retrieval_service.py ← SQL queries
  │   ├── rag_service.py             ← Embeddings
  │   └── llm_service.py             ← LLM calls
  ├── routes/
  │   └── chatbot.py                 ← HTTP endpoints
  ├── scripts/
  │   └── rebuild_rag_index.py       ← Index rebuild
  ├── tmp/
  │   └── chroma_db/                 ← Vector store (persistent)
  ├── .env                           ← Secrets & config
  └── config.py                      ← App config
```

---

## Support

- **Full docs**: See `IMPLEMENTATION_COMPLETE.md`
- **Code comments**: Inline documentation in each service
- **Test examples**: See `/home/tqffjfwm/airec-api/tmp/movie-chatbot-1/` for POC
- **API docs**: Visit `http://localhost:5000/swagger/` (when running)

---

## What's Included

✅ Intent analysis with genre/year extraction  
✅ SQL-based criteria search (genre, year, rating)  
✅ Semantic search via RAG (optional)  
✅ Graceful fallbacks (no RAG → SQL, no SQL → popular)  
✅ Anti-hallucination system prompt  
✅ Session persistence  
✅ Dual LLM providers (Gemini + OpenAI)  
✅ Comprehensive logging  
✅ Error handling  

---

**Status**: ✅ **Production Ready**  
**Last Updated**: March 18, 2026  
**Created By**: AI Assistant
