import os
import logging
import requests
from typing import Optional, Dict, Any

class DeepInfraModel:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = {
            'model_name': "deepseek-ai/DeepSeek-R1",
            'logging_level': logging.INFO
        }
        self.config = {**default_config, **(config or {})}
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config['logging_level'])
        self.DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
        if not self.DEEPINFRA_API_KEY:
            raise ValueError("DEEPINFRA_API_KEY no encontrada en variables de entorno")

    def get_response(self, query: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.DEEPINFRA_API_KEY}"
        }
        data = {
            "model": self.config['model_name'],
            "stream": False,
            "messages": [{
                "role": "user",
                "content": query
            }]
        }
        try:
            response = requests.post("https://api.deepinfra.com/v1/openai/chat/completions",
                                     headers=headers, json=data)
            if response.ok:
                response_json = response.json()
                if "choices" in response_json and response_json["choices"]:
                    message = response_json["choices"][0]["message"]
                    if "content" in message:
                        return message["content"].strip()
                return "No se pudo obtener respuesta del modelo."
            else:
                self.logger.error(f"DeepInfra API error: {response.status_code} {response.text}")
                return "Error en DeepInfra API."
        except Exception as e:
            self.logger.error(f"Error al conectar con DeepInfra API: {e}")
            return "Error en DeepInfra API."
