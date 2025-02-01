from abc import ABC, abstractmethod
import logging

class BaseModel(ABC):
    def __init__(self, config: dict = None):
        default_config = {
            'logging_level': logging.INFO,
            'max_response_chars': 3000
        }
        self.config = {**default_config, **(config or {})}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(self.config.get('logging_level', logging.INFO))
    
    @abstractmethod
    def get_response(self, query: str) -> str:
        """Ejecuta la consulta y retorna la respuesta del modelo."""
        pass

    def sanitize_response(self, response: str) -> str:
        """Elimina caracteres no deseados y limita el tamaño de la respuesta."""
        clean_response = response.strip().replace('\x00', '')
        max_len = self.config.get('max_response_chars', 3000)
        if len(clean_response) > max_len:
            return clean_response[:max_len].rsplit(' ', 1)[0] + " […]"
        return clean_response
