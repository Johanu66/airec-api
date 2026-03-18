import requests
import json
from flask import current_app

try:
    import google.generativeai as genai
except Exception:
    genai = None


class LLMService:
    """Service for interacting with LLM APIs (OpenAI, Claude, etc.)"""
    
    def __init__(self):
        self.api_key = None
        self.api_url = None
        self.model = None
        self.google_api_key = None
        self.google_model = None
        self.google_client = None
    
    def initialize(self, api_key, api_url, model, google_api_key=None, google_model='gemini-2.5-flash'):
        """Initialize the LLM service with configuration"""
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.google_api_key = google_api_key
        self.google_model = google_model

        if self.google_api_key and genai is not None:
            try:
                genai.configure(api_key=self.google_api_key)
                self.google_client = genai.GenerativeModel(self.google_model)
            except Exception:
                self.google_client = None
    
    def generate_response(self, messages, max_tokens=500):
        """
        Generate a response from the LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
        
        Returns:
            str: Generated response text
        """
        if self.api_key:
            return self._generate_openai_compatible_response(messages, max_tokens=max_tokens)

        if self.google_api_key and self.google_client:
            return self._generate_google_response(messages)

        return "LLM service not configured. Please set LLM_API_KEY or GOOGLE_API_KEY in environment."

    def _generate_openai_compatible_response(self, messages, max_tokens=500):
        """Call OpenAI-compatible chat completion APIs."""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                'model': self.model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': 0.7
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            return f"Error: LLM API returned status {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "Error: LLM API request timed out"
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to LLM API - {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _generate_google_response(self, messages):
        """Call Google Gemini API using the SDK."""
        try:
            prompt_parts = []
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'system':
                    prompt_parts.append(f"Instructions:\n{content}")
                elif role == 'assistant':
                    prompt_parts.append(f"Assistant:\n{content}")
                else:
                    prompt_parts.append(f"User:\n{content}")

            prompt = "\n\n".join(prompt_parts)
            response = self.google_client.generate_content(prompt)
            text = getattr(response, 'text', None)
            return text or "Error: Empty response from Gemini"
        except Exception as e:
            return f"Error: Gemini request failed - {str(e)}"
    
    def get_movie_recommendations_from_prompt(self, prompt, movie_context=""):
        """
        Get movie recommendations based on a conversational prompt
        
        Args:
            prompt: User's message
            movie_context: Context about available movies
        
        Returns:
            str: LLM response with recommendations
        """
        system_message = {
            'role': 'system',
            'content': '''You are a helpful movie recommendation assistant. 
Your role is to understand users' movie preferences and suggest appropriate films.
You can ask clarifying questions about their mood, favorite genres, actors, or themes.
Be conversational and friendly. When suggesting movies, provide brief reasons why they might enjoy them.
If you have context about available movies, use that information in your recommendations.'''
        }
        
        user_message = {
            'role': 'user',
            'content': prompt
        }
        
        if movie_context:
            user_message['content'] += f"\n\nAvailable movies context:\n{movie_context}"
        
        messages = [system_message, user_message]
        
        return self.generate_response(messages)
    
    def extract_movie_preferences(self, prompt):
        """
        Extract movie preferences (genres, mood, themes) from user prompt
        
        Args:
            prompt: User's message
        
        Returns:
            dict: Extracted preferences
        """
        system_message = {
            'role': 'system',
            'content': '''Analyze the user's message and extract movie preferences.
Return a JSON object with these fields:
- genres: array of genre names (Action, Comedy, Drama, etc.)
- mood: string describing the mood (happy, sad, exciting, relaxing, etc.)
- themes: array of themes (family, romance, adventure, etc.)
- year_preference: string (recent, classic, 90s, etc.) or null

Only include fields that are clearly mentioned or strongly implied.'''
        }
        
        user_message = {
            'role': 'user',
            'content': prompt
        }
        
        messages = [system_message, user_message]
        
        try:
            response = self.generate_response(messages, max_tokens=200)
            # Try to parse as JSON
            preferences = json.loads(response)
            return preferences
        except:
            # If parsing fails, return empty preferences
            return {
                'genres': [],
                'mood': None,
                'themes': [],
                'year_preference': None
            }


# Global instance
llm_service = LLMService()
