import logging
from typing import Dict, List
from modules.base_model import BaseModel
from modules.local_model import LocalModel
from modules.google_model import GoogleModel
from modules.openai_model import OpenAIModel

class ModelManager:
    def __init__(self, priority: List[str] = None, timeout_in_seconds: int = 5):
        self.priority = priority or ["local", "google", "openai"]
        self.timeout = timeout_in_seconds
        
        logging.basicConfig(filename="logs/jarvis.log",
                          level=logging.INFO,
                          format="%(asctime)s %(levelname)s %(message)s")
        
        self.models: Dict[str, BaseModel] = {
            "local": LocalModel(),
            "google": GoogleModel(),
            "openai": OpenAIModel()
        }

    def get_response(self, query: str) -> str:
        for model_name in self.priority:
            try:
                model = self.models.get(model_name)
                if not model:
                    logging.error(f"Modelo {model_name} no encontrado")
                    continue
                    
                response = model.get_response(query)
                logging.info(f"Respuesta exitosa de {model_name}")
                return response
                
            except Exception as e:
                logging.error(f"Error con modelo {model_name}: {str(e)}")
                continue
                
        return "No response available"