import os
import logging
import google.generativeai as genai
import subprocess
import time
import re
from typing import Optional, Dict, Any, Union
from shlex import split

class GoogleModel:
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada en variables de entorno")

        default_config = {
            'model_name': "gemini-2.0-flash-exp",
            'max_response_length': 10000,
            'logging_level': logging.INFO
        }
        self.config = {**default_config, **(config or {})}
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config['logging_level'])
        genai.configure(api_key=self.api_key)

    # Solo mantener los métodos esenciales
    def get_response(self, query: str) -> str:
        try:
            model = genai.GenerativeModel(self.config['model_name'])
            response = model.generate_content(query)
            
            if response.text:
                return self._validate_response(response.text)
            return "No se pudo generar una respuesta"
            
        except Exception as e:
            self.logger.error(f"Error en Google API: {str(e)}")
            return "Error: No se pudo obtener respuesta de Google"

    def _validate_response(self, response: str) -> str:
        if len(response) > self.config['max_response_length']:
            return response[:self.config['max_response_length']] + "..."
        return response