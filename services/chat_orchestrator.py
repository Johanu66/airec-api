import re
from services.llm_service import llm_service
from services.rag_service import rag_service
from services.chat_retrieval_service import chat_retrieval_service


GENRE_ALIASES = {
    'action': 'Action',
    'comedy': 'Comedy',
    'comedie': 'Comedy',
    'comédie': 'Comedy',
    'drama': 'Drama',
    'drame': 'Drama',
    'horror': 'Horror',
    'horreur': 'Horror',
    'romance': 'Romance',
    'thriller': 'Thriller',
    'crime': 'Crime',
    'adventure': 'Adventure',
    'aventure': 'Adventure',
    'animation': 'Animation',
    'fantasy': 'Fantasy',
    'fantastique': 'Fantasy',
    'mystery': 'Mystery',
    'science-fiction': 'Sci-Fi',
    'sci-fi': 'Sci-Fi',
    'sf': 'Sci-Fi'
}


class ChatOrchestrator:
    """Intent analysis + retrieval orchestration + anti-hallucination response generation."""

    def _extract_years(self, text):
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if not years:
            return None, None

        if any(token in text.lower() for token in ['depuis', 'after', 'après']):
            return int(years[0]), None

        if len(years) > 1:
            return int(years[0]), int(years[1])

        year = int(years[0])
        return year, year

    def analyze_intent(self, message):
        text = message.lower().strip()
        intent = {
            'type': 'general',
            'genre': None,
            'year_min': None,
            'year_max': None,
            'rating_min': None,
            'title_ref': None
        }

        for key, canonical in GENRE_ALIASES.items():
            if key in text:
                intent['genre'] = canonical
                intent['type'] = 'criteria'
                break

        y_min, y_max = self._extract_years(message)
        if y_min is not None:
            intent['year_min'] = y_min
            intent['year_max'] = y_max
            intent['type'] = 'criteria'

        if any(k in text for k in ['récent', 'recent', 'nouveau', 'latest']):
            intent['year_min'] = max(intent['year_min'] or 0, 2020)
            intent['type'] = 'criteria'

        if any(k in text for k in ['bien noté', 'bonne note', 'top rated', 'highly rated']):
            intent['rating_min'] = 4.0
            intent['type'] = 'criteria'

        if any(k in text for k in ['populaire', 'popular', 'tendance', 'trending']):
            intent['type'] = 'popular'

        if any(k in text for k in ['comme', 'similaire', 'similar', 'like']):
            intent['type'] = 'similar'
            if '"' in message:
                parts = message.split('"')
                if len(parts) >= 2:
                    intent['title_ref'] = parts[1].strip()
            if not intent['title_ref']:
                match = re.search(r'(comme|like|similaire à|similar to)\s+(.+)$', text)
                if match:
                    intent['title_ref'] = match.group(2).strip()

        semantic_triggers = [
            'émouvant', 'emouvant', 'profond', 'intense', 'relaxant', 'qui fait réfléchir',
            'atmosphère', 'ambiance', 'theme', 'thème', 'vibe'
        ]
        if any(k in text for k in semantic_triggers):
            intent['type'] = 'semantic'

        return intent

    def _build_system_prompt(self, movies):
        movie_lines = []
        for idx, m in enumerate(movies[:10], start=1):
            genres = ', '.join(m.get('genres') or [])
            movie_lines.append(
                f"{idx}. {m['title']} ({m.get('release_year') or 'N/A'}) - {genres} - rating {m.get('average_rating', 0)}/5"
            )

        catalog = '\n'.join(movie_lines) if movie_lines else 'Aucun film trouvé.'

        return (
            "You are an assistant for movie recommendations. "
            "Never invent movies. Recommend only from the catalog below. "
            "If a requested movie is not in the catalog, say it is unavailable in the current database.\n\n"
            "Catalog:\n"
            f"{catalog}\n\n"
            "Response style: short, friendly, and practical."
        )

    def _build_user_message(self, message, conversation_history):
        history_window = conversation_history[-8:] if conversation_history else []
        history_text = []
        for h in history_window:
            role = h.get('role', 'user')
            content = h.get('content', '')
            history_text.append(f"{role}: {content}")

        history_block = '\n'.join(history_text) if history_text else 'No prior context.'
        return f"Conversation history:\n{history_block}\n\nUser request: {message}"

    def _generate_response_text(self, message, movies, conversation_history):
        system_prompt = self._build_system_prompt(movies)
        user_prompt = self._build_user_message(message, conversation_history)

        response = llm_service.generate_response([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ], max_tokens=420)

        if isinstance(response, str) and response.lower().startswith('error:'):
            if movies:
                return "Voici des films recommandés selon ta demande."
            return "Je n'ai pas trouvé de films pertinents pour cette demande pour le moment."

        return response

    def _retrieve_movies(self, message, intent, limit, user_id=None):
        if intent['type'] == 'criteria':
            return chat_retrieval_service.search_by_criteria(
                genre=intent.get('genre'),
                year_min=intent.get('year_min'),
                year_max=intent.get('year_max'),
                rating_min=intent.get('rating_min'),
                limit=limit
            )

        if intent['type'] == 'popular':
            return chat_retrieval_service.popular_movies(
                genre=intent.get('genre'),
                limit=limit
            )

        if intent['type'] == 'similar' and intent.get('title_ref'):
            return chat_retrieval_service.similar_movies(
                movie_title=intent.get('title_ref'),
                limit=limit
            )

        if intent['type'] == 'semantic' and rag_service.is_available():
            semantic_movies = rag_service.semantic_search(message, n_results=limit)
            if semantic_movies:
                return semantic_movies

        # fallback
        return chat_retrieval_service.popular_movies(
            genre=intent.get('genre'),
            limit=limit
        )

    def process_message(self, message, conversation_history=None, user_id=None, session_id=None, limit=10):
        intent = self.analyze_intent(message)
        movies = self._retrieve_movies(message, intent, limit=limit, user_id=user_id)
        response_text = self._generate_response_text(message, movies, conversation_history or [])

        return {
            'response': response_text,
            'intent': intent,
            'recommendations': movies[:limit]
        }

    def search_movies(self, query, limit=10, user_id=None):
        intent = self.analyze_intent(query)
        movies = self._retrieve_movies(query, intent, limit=limit, user_id=user_id)
        return {
            'intent': intent,
            'movies': movies[:limit]
        }


chat_orchestrator = ChatOrchestrator()
