import os
import logging
import google.generativeai as genai
from typing import Optional, Dict, Any
from .base_model import BaseModel

class GoogleModel(BaseModel):
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada en variables de entorno")
        self.api_key = api_key
        default_config = {
            'model_name': "gemini-2.0-flash-exp",
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(merged_config)
        genai.configure(api_key=self.api_key)

    def get_response(self, query: str) -> str:
        try:
            model = genai.GenerativeModel(self.config['model_name'])
            response = model.generate_content(query)
            if response.text:
                return response.text
            return "No se pudo obtener respuesta del modelo."
        except Exception as e:
            self.logger.error(f"Error en Google API: {str(e)}")
            return "No se pudo obtener respuesta del modelo."

    def analyze_command(self, user_input: str, command_prompt_template: str) -> Optional[str]:
        try:
            model = genai.GenerativeModel(self.config['model_name'])
            prompt = command_prompt_template.format(input=user_input)
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0,
                    'top_p': 1,
                    'top_k': 1,
                }
            )
            
            if response.text:
                result = response.text.strip()
                self.logger.info(f"Command analysis response: {result}")
                return result
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing command: {e}")
            return None

    def get_completion(self, prompt: str, temperature: float = 0.1) -> Optional[str]:
        try:
            model = genai.GenerativeModel(self.config['model_name'])
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': temperature,
                    'top_p': 1,
                    'top_k': 1,
                    'max_output_tokens': 5,
                }
            )
            
            if response.text:
                return response.text.strip()
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting completion: {e}")
            return None

    def format_message(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        try:
            model = genai.GenerativeModel(self.config['model_name'])
            generation_config = {
                'temperature': temperature,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 2048,
                'candidate_count': 1
            }
            
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            
            if response.text:
                text = response.text.strip()
                prefixes = ['Asistente:', 'Sistema:', 'Respuesta:', 'AI:', 'Bot:', 'Assistant:', 'System:']
                text_lower = text.lower()
                for prefix in prefixes:
                    if text_lower.startswith(prefix.lower()):
                        text = text[len(prefix):].strip()
                return text
            return None
            
        except Exception as e:
            self.logger.error(f"Error formateando mensaje: {e}")
            return None