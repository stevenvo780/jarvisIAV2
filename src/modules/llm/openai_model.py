import os
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from .base_model import BaseModel

class OpenAIModel(BaseModel):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if not (os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY").startswith("sk-")):
            raise ValueError("OPENAI_API_KEY no encontrada o inválida")
        self.api_key = os.getenv("OPENAI_API_KEY")
        default_config = {
            'model_name': 'gpt-4o',
            'temperature': 0.7,
            'max_tokens': 1024,
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(merged_config)
        self.client = OpenAI(api_key=self.api_key, timeout=25.0, max_retries=3)

    def get_response(self, query: str) -> str:
        if not isinstance(query, str) or len(query.strip()) < 3:
            return "La consulta debe ser un texto no vacío (>3 caracteres)"
        try:
            response = self.client.chat.completions.create(
                model=self.config['model_name'],
                messages=[{'role': 'user', 'content': query}],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            if response.choices and response.choices[0].message:
                return self.sanitize_response(response.choices[0].message.content)
            return "No se recibió una respuesta válida de OpenAI"
        except Exception as e:
            self.logger.error(f"Error al obtener respuesta de OpenAI: {e}")
            return "Error al procesar la consulta"
