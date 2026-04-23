import re
from services.llm_service import llm_service
from services.rag_service import rag_service
from services.chat_retrieval_service import chat_retrieval_service


GENRE_ALIASES = {
    # Anglais
    'action': 'Action',
    'comedy': 'Comedy',
    'drama': 'Drama',
    'horror': 'Horror',
    'romance': 'Romance',
    'thriller': 'Thriller',
    'crime': 'Crime',
    'adventure': 'Adventure',
    'animation': 'Animation',
    'fantasy': 'Fantasy',
    'mystery': 'Mystery',
    'science-fiction': 'Sci-Fi',
    'science fiction': 'Sci-Fi',
    'sci-fi': 'Sci-Fi',
    'scifi': 'Sci-Fi',
    'sf': 'Sci-Fi',
    'war': 'War',
    'western': 'Western',
    'musical': 'Musical',
    # Français
    'comedie': 'Comedy',
    'comédie': 'Comedy',
    'comique': 'Comedy',
    'drame': 'Drama',
    'horreur': 'Horror',
    'romantique': 'Romance',
    'aventure': 'Adventure',
    'animé': 'Animation',
    'anime': 'Animation',
    'fantastique': 'Fantasy',
    'mystère': 'Mystery',
    'policier': 'Crime',
    'guerre': 'War',
    'documentaire': 'Documentary',
    # Termes familiers / sous-genres
    'comics': 'Action',
    'comic': 'Action',
    'superhero': 'Action',
    'super-héros': 'Action',
    'super héros': 'Action',
    'marvel': 'Action',
    'effrayant': 'Horror',
    'peur': 'Horror',
    'amour': 'Romance',
    'drôle': 'Comedy',
    'rigoler': 'Comedy',
    'rire': 'Comedy',
    'violent': 'Action',
    'suspense': 'Thriller',
    'espionnage': 'Thriller',
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

        if any(k in text for k in ['populaire', 'popular', 'tendance', 'trending',
                                    'propose', 'proposes', 'proposer',
                                    'recommande', 'recommandes', 'recommander',
                                    'suggestion', 'conseil', 'conseille',
                                    'quoi regarder', 'quoi voir', 'que voir',
                                    'quoi comme film', 'quoi comme']):
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
            'atmosphère', 'ambiance', 'theme', 'thème', 'vibe',
            'touchant', 'inspirant', 'feel good', 'feel-good', 'réconfortant',
            'triste', 'joyeux', 'stressant', 'détente', 'poignant',
        ]
        if any(k in text for k in semantic_triggers):
            intent['type'] = 'semantic'

        return intent

    def _build_system_prompt(self, movies):
        movie_lines = []
        for idx, m in enumerate(movies[:10], start=1):
            genres = ', '.join(m.get('genres') or [])
            movie_lines.append(
                f"{idx}. {m['title']} ({m.get('release_year') or 'N/A'}) - {genres} - note {m.get('average_rating', 0)}/5"
            )

        catalog = '\n'.join(movie_lines) if movie_lines else 'Aucun film trouvé dans cette catégorie.'

        return (
            "Tu es un assistant sympathique spécialisé dans les recommandations de films. "
            "Réponds TOUJOURS en français, de manière chaleureuse et concise (3-4 lignes max). "
            "Ne recommande JAMAIS un film qui n'est pas dans le catalogue ci-dessous. "
            "Si le genre demandé n'existe pas en tant que tel (ex: 'comics', 'superhéros'), "
            "propose des films d'Action/Aventure du catalogue qui peuvent correspondre. "
            "Si vraiment aucun film ne correspond, dis-le clairement et propose une alternative.\n\n"
            "Catalogue disponible :\n"
            f"{catalog}\n\n"
            "Réponds directement à la demande en citant uniquement des films du catalogue."
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
            return self._fallback_response(message, movies)

        return response

    def _fallback_response(self, message, movies):
        """Réponse contextuelle dynamique quand le LLM est indisponible."""
        import random
        text = message.lower()

        if any(k in text for k in ['triste', 'déprime', 'déprimé', 'mal', 'sad']):
            intro = random.choice([
                "Je comprends... Un bon film peut aider ! Voici mes suggestions :",
                "Les moments difficiles passent mieux avec un film. Voici ce que je te recommande :",
            ])
        elif any(k in text for k in ['heureux', 'content', 'envie', 'happy', 'bonne humeur', 'joyeux']):
            intro = random.choice([
                "Super ambiance ! Voici mes recommandations pour ce soir :",
                "Parfait pour une bonne soirée ! Voici mes suggestions :",
            ])
        elif any(k in text for k in ['action']):
            intro = random.choice([
                "Pour une dose d'adrénaline, voici les meilleurs films d'action :",
                "Tu veux du rythme et de l'action ? Voici mes recommandations :",
            ])
        elif any(k in text for k in ['comédie', 'comedy', 'rire', 'drôle', 'fun']):
            intro = random.choice([
                "Pour bien rire, voici mes comédies préférées :",
                "Tu veux te marrer ? Voici ce que je te propose :",
            ])
        elif any(k in text for k in ['horreur', 'horror', 'peur', 'effrayant']):
            intro = random.choice([
                "Pour frissonner ce soir, voici mes sélections :",
                "Tu aimes avoir peur ? Voici mes recommandations :",
            ])
        elif any(k in text for k in ['drame', 'drama', 'émouvant', 'profond']):
            intro = random.choice([
                "Pour quelque chose d'intense et émouvant, voici mes suggestions :",
                "Voici des films forts qui vont te marquer :",
            ])
        elif movies:
            intro = random.choice([
                "Voici les films qui correspondent à ta demande :",
                "J'ai trouvé ces films pour toi :",
                "Voici ce que je te recommande :",
            ])
        else:
            intro = "Je n'ai pas trouvé de films correspondant exactement à ta demande, mais voici des suggestions populaires :"

        return intro

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

        # Pour les requêtes générales, tenter la recherche sémantique pour varier les résultats
        if intent['type'] in ('general', 'popular') and rag_service.is_available():
            semantic_movies = rag_service.semantic_search(message, n_results=limit)
            if semantic_movies:
                return semantic_movies

        # fallback : films populaires (avec genre si détecté)
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
