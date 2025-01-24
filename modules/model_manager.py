import logging
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from modules.local_model import LocalModel
from modules.google_model import GoogleModel
from modules.openai_model import OpenAIModel

class ModelManager:
    def __init__(self, priority: List[str] = None, timeout_in_seconds: int = 5,
                 max_retries: int = 3, context_size: int = 5):
        self.priority = priority or ["openai", "google","local"]
        self.timeout = timeout_in_seconds
        self.max_retries = max_retries
        self.conversation_history = []
        self.context_size = context_size
        
        self._setup_logging()
        self._initialize_models()
        
    def _setup_logging(self):
        logging.basicConfig(
            filename="logs/jarvis.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )
    
    def _initialize_models(self):
        # Actualizado para remover referencia a BaseModel
        self.models = {
            "local": LocalModel(),
            "google": GoogleModel(),
            "openai": OpenAIModel()
        }

    def _execute_with_timeout(self, model, query: str) -> Optional[str]:
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(model.get_response, query)
                return future.result(timeout=self.timeout)
            except TimeoutError:
                logging.error(f"Timeout after {self.timeout} seconds")
                return None

    def _try_model_with_retry(self, model_name: str, query: str) -> Optional[str]:
        model = self.models.get(model_name)
        if not model:
            return None

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = self._execute_with_timeout(model, query)
                if response:
                    duration = time.time() - start_time
                    logging.info(
                        f"Model {model_name} responded in {duration:.2f}s"
                    )
                    return response
            except Exception as e:
                logging.error(f"Error with {model_name} (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        return None

    def get_response(self, query: str) -> str:
        # Actualizar historial de conversación
        if len(self.conversation_history) >= self.context_size:
            self.conversation_history.pop(0)
        self.conversation_history.append({"query": query})
        
        for model_name in self.priority:
            response = self._try_model_with_retry(model_name, query)
            if response:
                self.conversation_history[-1]["response"] = response
                return response
        
        return "Lo siento, no pude procesar tu solicitud en este momento."

    def clear_context(self):
        self.conversation_history.clear()