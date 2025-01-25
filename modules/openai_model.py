import time
import os
from openai import OpenAI

class OpenAIModel:
    def __init__(self, openai_api_key=None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("No se encontró OPENAI_API_KEY en las variables de entorno")
        self.client = OpenAI(api_key=self.openai_api_key)
        
    def get_response(self, query: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=1500,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error al procesar la solicitud: {str(e)}"
