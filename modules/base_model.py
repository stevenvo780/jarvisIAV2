
from abc import ABC, abstractmethod

class BaseModel(ABC):
    @abstractmethod
    def get_response(self, query: str) -> str:
        pass