import os
import openai
import logging
from typing import Optional

class OpenAIModel:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("No se encontró OPENAI_API_KEY en las variables de entorno")
        openai.api_key = self.api_key
        
    def get_response(self, query: str) -> str:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": query}],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message['content']
        except Exception as e:
            logging.error(f"Error OpenAI: {e}")
            return f"Error al procesar la solicitud: {str(e)}"
