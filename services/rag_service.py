import os
from flask import current_app

try:
    import chromadb
except Exception:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

from services.chat_retrieval_service import chat_retrieval_service


class RAGService:
    """Semantic retrieval service over real API database content."""

    def __init__(self):
        self._initialized = False
        self._client = None
        self._collection = None
        self._embedding_model = None

    def _is_enabled(self):
        return bool(current_app.config.get('RAG_ENABLED', False))

    def _initialize(self):
        if self._initialized:
            return

        self._initialized = True
        if not self._is_enabled() or chromadb is None or SentenceTransformer is None:
            return

        chroma_path = current_app.config.get('RAG_CHROMA_PATH')
        collection_name = current_app.config.get('RAG_COLLECTION_NAME', 'airec_movies')
        embedding_model_name = current_app.config.get('RAG_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

        os.makedirs(chroma_path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=chroma_path)
        self._embedding_model = SentenceTransformer(embedding_model_name)

        try:
            self._collection = self._client.get_collection(collection_name)
        except Exception:
            self._collection = self._client.create_collection(
                name=collection_name,
                metadata={'domain': 'movies', 'source': 'airec-api'}
            )

        if self._collection.count() == 0:
            self.rebuild_index()

    def is_available(self):
        self._initialize()
        return self._collection is not None and self._embedding_model is not None

    def _build_document(self, movie):
        genres = ', '.join(movie.get('genres') or [])
        year = movie.get('release_year') or 'Unknown'
        description = movie.get('description') or ''
        return f"{movie.get('title', '')}. Year: {year}. Genres: {genres}. Description: {description}".strip()

    def rebuild_index(self):
        self._initialize()
        if not self._collection or not self._embedding_model:
            return {'indexed': 0, 'status': 'disabled'}

        min_ratings = int(current_app.config.get('RAG_MIN_RATINGS', 5))
        # Pull a broad set then filter in memory on rating count
        candidates = chat_retrieval_service.popular_movies(limit=100000, min_ratings=0, min_rating=0.0)
        movies = [m for m in candidates if m.get('ratings_count', 0) >= min_ratings]

        try:
            self._client.delete_collection(current_app.config.get('RAG_COLLECTION_NAME', 'airec_movies'))
        except Exception:
            pass

        self._collection = self._client.create_collection(
            name=current_app.config.get('RAG_COLLECTION_NAME', 'airec_movies'),
            metadata={'domain': 'movies', 'source': 'airec-api'}
        )

        batch_size = 128
        total = 0

        for i in range(0, len(movies), batch_size):
            batch = movies[i:i + batch_size]
            ids = [str(m['id']) for m in batch]
            documents = [self._build_document(m) for m in batch]
            embeddings = self._embedding_model.encode(documents).tolist()
            metadatas = [
                {
                    'title': m.get('title') or '',
                    'release_year': str(m.get('release_year') or ''),
                    'genres': ', '.join(m.get('genres') or [])
                }
                for m in batch
            ]

            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            total += len(batch)

        return {'indexed': total, 'status': 'ok'}

    def semantic_search(self, query_text, n_results=None):
        self._initialize()
        if not self.is_available():
            return []

        top_k = n_results or int(current_app.config.get('RAG_TOP_K', 8))
        query_embedding = self._embedding_model.encode([query_text])[0].tolist()

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['distances', 'metadatas']
        )

        ids = [int(movie_id) for movie_id in results.get('ids', [[]])[0] if str(movie_id).isdigit()]
        movies = chat_retrieval_service.get_movies_by_ids(ids)
        by_id = {m['id']: m for m in movies}

        distances = results.get('distances', [[]])[0] if results.get('distances') else []
        ranked = []
        for idx, movie_id in enumerate(ids):
            if movie_id not in by_id:
                continue
            item = dict(by_id[movie_id])
            distance = distances[idx] if idx < len(distances) else None
            item['semantic_score'] = round(1 - float(distance), 4) if distance is not None else None
            ranked.append(item)

        return ranked


rag_service = RAGService()
