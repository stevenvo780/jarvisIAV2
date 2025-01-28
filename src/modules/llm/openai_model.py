import os
import logging
import time
from typing import Optional, Dict, Any
from openai import OpenAI
from utils.prompt_builder import PromptBuilder

class OpenAIModel:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key or not self.api_key.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY no encontrada o inválida")
        
        default_config = {
            'model_name': 'gpt-4o',
            'temperature': 0.7,
            'max_tokens': 1024,
            'logging_level': logging.INFO
        }
        self.config = {**default_config, **(config or {})}
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config['logging_level'])
        self.client = OpenAI(api_key=self.api_key, timeout=25.0, max_retries=3)
        self.prompt_builder = PromptBuilder()

    def get_response(self, query: str) -> str:
        if not isinstance(query, str) or len(query.strip()) < 3:
            return "La consulta debe ser un texto no vacío (>3 caracteres)"
        
        try:
            prompt_data = self.prompt_builder.build_prompt(query, 'openai')
            response = self.client.chat.completions.create(
                model=self.config['model_name'],
                messages=prompt_data['messages'],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            if response.choices and response.choices[0].message:
                return self._sanitize_response(response.choices[0].message.content)
            return "No se recibió una respuesta válida de OpenAI"
        except Exception as e:
            self.logger.error(f"Error al obtener respuesta de OpenAI: {e}")
            return "Error al procesar la consulta"

    def _sanitize_response(self, response: str) -> str:
        clean_response = response.strip().replace('\x00', '')
        max_len = self.config.get('max_response_chars', 3000)
        if len(clean_response) > max_len:
            return clean_response[:max_len].rsplit(' ', 1)[0] + " […]"
        return clean_response

    def validate_connection(self) -> bool:
        try:
            self.client.models.retrieve(self.config['model_name'], timeout=10)
            return True
        except Exception as e:
            self.logger.error(f"Validación de conexión fallida: {e}")
            return False
