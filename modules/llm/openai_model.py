import os
import logging
import time
from typing import Optional, Dict, Any
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError, OpenAIError

class OpenAIModel:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.config = self._merge_config(config)
        if not self.api_key:
            logging.error("No se encontró OPENAI_API_KEY")
            raise ValueError("OPENAI_API_KEY no encontrada")
        self._validate_credentials()
        self.client = self._initialize_client()
        self.logger = self._configure_logger()
        
    def _merge_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        default_config = {
            'timeout': 25.0,
            'max_retries': 3,
            'backoff_base': 1.8,
            'max_tokens': 1024,
            'max_response_chars': 3000,
            'model_name': 'gpt-4o-2024-05-13',
            'temperature': 0.7,
            'log_level': 'INFO'
        }
        return {**default_config, **(config or {})}

    def _validate_credentials(self) -> None:
        """Validates API key format."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no encontrada en variables de entorno")
        if not self.api_key.startswith("sk-"):
            raise ValueError("Formato de API key de OpenAI inválido")

    def _initialize_client(self) -> OpenAI:
        return OpenAI(
            api_key=self.api_key,
            timeout=self.config['timeout'],
            max_retries=self.config['max_retries']
        )

    def _configure_logger(self) -> logging.Logger:
        logger = logging.getLogger("OpenAIModel")
        logger.setLevel(self.config['log_level'].upper())
        return logger

    def get_response(self, query: str) -> str:
        if not isinstance(query, str) or len(query.strip()) < 3:
            return "Query debe ser texto no vacío (>3 caracteres)"

        for attempt in range(self.config['max_retries'] + 1):
            try:
                return self._process_request(query)
            except RateLimitError as e:
                self._handle_rate_limit(attempt, e)
            except APIConnectionError as e:
                self._handle_connection_error(attempt, e)
            except AuthenticationError as e:
                return self._handle_auth_error(e)
            except APIError as e:
                self.logger.error(f"Error API: {str(e)}")
                return "Error en la API de OpenAI"
            except Exception as e:
                self.logger.error(f"Error inesperado: {str(e)}")
                if attempt == self.config['max_retries']:
                    return "Error procesando la consulta"
                
        return "No se pudo obtener respuesta de OpenAI"

    def _process_request(self, query: str) -> str:
        start_time = time.monotonic()
        try:
            # Extraer pregunta del usuario
            if "Pregunta:" in query:
                parts = query.split("Pregunta:", 1)
                system_content = parts[0].strip()
                user_content = parts[1].strip()
            else:
                system_content = "Eres Jarvis, un asistente virtual profesional y preciso."
                user_content = query.strip()

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Usar modelo correcto
                messages=messages,
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens'],
                stream=False
            )

            if not response.choices or not response.choices[0].message:
                raise ValueError("Respuesta vacía de OpenAI")

            processing_time = time.monotonic() - start_time
            self.logger.info(f"Respuesta en {processing_time:.2f}s | Tokens: {response.usage.total_tokens}")
            return self._sanitize_response(response.choices[0].message.content)

        except Exception as e:
            self.logger.error(f"Error en process_request: {str(e)}")
            raise

    def _sanitize_response(self, response: str) -> str:
        clean_response = response.strip().replace('\x00', '')
        max_len = self.config['max_response_chars']
        return clean_response[:max_len] if len(clean_response) <= max_len else clean_response[:max_len].rsplit(' ', 1)[0] + " […]"

    def _handle_rate_limit(self, attempt: int, error: RateLimitError) -> None:
        backoff = self.config['backoff_base'] ** (attempt + 1)
        self.logger.warning(f"Rate limit (Intento {attempt+1}): Esperando {backoff:.1f}s")
        time.sleep(backoff)

    def _handle_connection_error(self, attempt: int, error: APIConnectionError) -> None:
        self.logger.error(f"Error conexión: {error.message}")
        if attempt >= self.config['max_retries']:
            raise TimeoutError("Fallo persistente de conexión") from error

    def _handle_auth_error(self, error: AuthenticationError) -> None:
        self.logger.critical("Error de autenticación irreversible")
        # Aquí no relanzamos el error, solo lo logueamos
        return "Error de autenticación con OpenAI"

    def _handle_api_error(self, error: APIError) -> None:
        self.logger.error(f"Error API: {error.code} - {error.message}")
        time.sleep(2 ** self.config['max_retries'])

    def _final_error_message(self) -> str:
        self.logger.error("Máximos reintentos alcanzados")
        return "Error: No se pudo procesar la solicitud después de múltiples intentos"

    def validate_connection(self) -> bool:
        try:
            self.client.models.retrieve(self.config['model_name'], timeout=10)
            return True
        except Exception as e:
            self.logger.error(f"Validación fallida: {str(e)}")
            return False