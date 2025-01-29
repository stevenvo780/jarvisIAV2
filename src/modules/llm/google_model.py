import os
import logging
import google.generativeai as genai
from typing import Optional, Dict, Any
from utils.prompt_builder import PromptBuilder  # Cambiado a importación absoluta

class GoogleModel:
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada en variables de entorno")

        default_config = {
            'model_name': "gemini-2.0-flash-exp",
            'logging_level': logging.INFO
        }
        self.config = {**default_config, **(config or {})}
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config['logging_level'])
        genai.configure(api_key=self.api_key)
        self.prompt_builder = PromptBuilder()

    def get_response(self, query: str) -> str:
        try:
            model = genai.GenerativeModel(self.config['model_name'])
            prompt_data = self.prompt_builder.build_prompt(query, 'google')
            response = model.generate_content(prompt_data['prompt'])
            
            if response.text:
                return response.text
            return self.prompt_builder.get_error_message('no_response')
            
        except Exception as e:
            self.logger.error(f"Error en Google API: {str(e)}")
            return self.prompt_builder.get_error_message('api_error', message=str(e))

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
                # Limpiar prefijos de forma más robusta
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