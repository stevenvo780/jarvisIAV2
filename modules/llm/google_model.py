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
            'timeout': 10,
            'max_retries': 3,
            'backoff_factor': 1,
            'quota_error_delay': 60,
            'max_response_length': 10000,
            'model_name': "gemini-pro",  # Actualizado nombre del modelo
            'logging_level': logging.INFO
        }
        self.config = {**default_config, **(config or {})}
        self._validate_config()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config['logging_level'])
        genai.configure(api_key=self.api_key)  # Cambiado palm por genai

    def _validate_config(self):
        required_keys = ['timeout', 'max_retries', 'backoff_factor', 'quota_error_delay', 'model_name', 'max_response_length']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Configuración inválida: falta {key}")
        if not isinstance(self.config['model_name'], str):
            raise ValueError("model_name debe ser string")
        if not isinstance(self.config['max_response_length'], int) or self.config['max_response_length'] <= 0:
            raise ValueError("max_response_length inválido")
        if not logging.getLevelName(self.config['logging_level']):
            raise ValueError("Nivel de logging inválido")

    def _handle_quota_error(self, error: Exception) -> str:
        self.logger.warning(f"Límite de cuota: {error}")
        time.sleep(self.config['quota_error_delay'])
        return "Error: Límite de cuota excedido"

    def _handle_api_error(self, error: Exception) -> str:
        self.logger.error(f"Error de API: {error}")
        return "Error temporal del servidor"

    def _handle_network_error(self, attempt: int) -> None:
        delay = self.config['backoff_factor'] * (2 ** (attempt - 1))
        self.logger.warning(f"Reintento {attempt} en {delay}s")
        time.sleep(delay)

    def get_response(self, query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Pregunta inválida")

        for attempt in range(1, self.config['max_retries'] + 1):
            try:
                start_time = time.time()
                
                # Inicializar el modelo
                model = genai.GenerativeModel(self.config['model_name'])
                
                # Generar respuesta
                response = model.generate_content(query)
                
                processing_time = time.time() - start_time
                self.logger.info(f"Tiempo respuesta: {processing_time:.2f}s")

                if response.text:
                    return self._validate_response(response.text)
                raise ValueError("Respuesta vacía")

            except Exception as e:
                self.logger.error(f"Error en Google API: {str(e)}")
                if attempt == self.config['max_retries']:
                    return "Error: No se pudo obtener respuesta de Google"
                time.sleep(self.config['backoff_factor'] * attempt)

        return "Error: No se pudo obtener respuesta"

    def _validate_response(self, response: str) -> str:
        if not isinstance(response, str):
            raise TypeError("Tipo de respuesta inválido")
        if len(response) > self.config['max_response_length']:
            truncate_at = response[:self.config['max_response_length']].rfind(' ')
            return response[:truncate_at] + "..." if truncate_at != -1 else response[:self.config['max_response_length']]
        return response

    def extract_command(self, message: str) -> str:
        marker = "COMANDO:"
        if marker in message:
            command_part = message.split(marker, 1)[1].strip()
            end_marker = "FIN_COMANDO"
            return command_part.split(end_marker, 1)[0].strip() if end_marker in command_part else command_part
        return ""

    def execute_os_command(self, command: str) -> str:
        if not command.strip():
            return "Comando vacío"

        blocked_pattern = r'\b(rm|del|shutdown|sudo|chmod|kill|mv|cp|dd|format)\b'
        if re.search(blocked_pattern, command, re.IGNORECASE):
            self.logger.warning(f"Comando bloqueado: {command}")
            return "Error: Comando prohibido"

        try:
            args = split(command)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=15,
                check=True
            )
            output = result.stdout.strip() or "Éxito sin salida"
            return output[:500] + ("..." if len(output) > 500 else "")
        except subprocess.CalledProcessError as e:
            error_msg = f"Error ({e.returncode}): {e.stderr.strip()}"
            return error_msg[:500] + ("..." if len(error_msg) > 500 else "")
        except subprocess.TimeoutExpired:
            return "Error: Tiempo agotado"
        except Exception as e:
            return f"Error crítico: {str(e)}"

    def get_structured_response(self, query: str) -> Dict[str, Union[str, bool]]:
        try:
            raw_response = self.get_response(query)
            extracted_command = self.extract_command(raw_response)
            command_result = self.execute_os_command(extracted_command) if extracted_command else ""
            
            return {
                "raw_response": raw_response,
                "command_detected": bool(extracted_command),
                "command": extracted_command,
                "command_result": command_result,
                "source": "Google Gemini",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            self.logger.error(f"Error en respuesta estructurada: {e}")
            return {
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }