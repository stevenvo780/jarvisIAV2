import logging
import time
import itertools
import threading
import sys
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from modules.local_model import LocalModel
from modules.google_model import GoogleModel
from modules.openai_model import OpenAIModel
from modules.storage_manager import StorageManager

class ModelManager:
    def __init__(self, priority: List[str] = None, timeout_in_seconds: int = 5,
                 max_retries: int = 3, context_size: int = 5):
        self.priority = priority or ["openai", "google","local"]
        self.timeout = 10  # Ajustar a un valor menor o mayor según lo requieras
        self.max_retries = max_retries
        self.context_size = context_size
        self.thinking_animation = None
        self.stop_thinking = False
        self.is_processing = False  # Nuevo flag para controlar el estado de procesamiento
        
        self._setup_logging()
        self._initialize_models()
        self.storage = StorageManager()
        self.conversation_history = self.storage.load_conversation()
        
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

    def _show_thinking_animation(self):
        animation = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        while not self.stop_thinking:
            sys.stdout.write('\rPensando ' + next(animation))
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' '*20 + '\r')
        sys.stdout.flush()

    def _start_thinking_animation(self):
        self.stop_thinking = False
        self.thinking_animation = threading.Thread(target=self._show_thinking_animation)
        self.thinking_animation.start()

    def _stop_thinking_animation(self):
        if self.thinking_animation:
            self.stop_thinking = True
            self.thinking_animation.join()

    def _execute_with_timeout(self, model, query: str) -> Optional[str]:
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(model.get_response, query)
                return future.result(timeout=self.timeout)
            except TimeoutError:
                logging.error(f"Timeout después de {self.timeout} segundos en {model}")
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
        self.is_processing = True  # Indicar que está procesando
        self._start_thinking_animation()
        
        try:
            # Actualizar historial de conversación
            if len(self.conversation_history) >= self.context_size:
                self.conversation_history.pop(0)
            self.conversation_history.append({"query": query})
            
            for model_name in self.priority:
                response = self._try_model_with_retry(model_name, query)
                if response:
                    self.conversation_history[-1]["response"] = response
                    self.storage.save_conversation(self.conversation_history)
                    return response
            
            default_response = "Lo siento, no pude procesar tu solicitud en este momento."
            self.conversation_history[-1]["response"] = default_response
            self.storage.save_conversation(self.conversation_history)
            return default_response
            
        finally:
            self._stop_thinking_animation()
            self.is_processing = False  # Indicar que terminó de procesar

    def clear_context(self):
        self.conversation_history.clear()
        self.storage.clear_history()

    def get_conversation_history(self) -> List[dict]:
        """Retorna el historial de la conversación"""
        return self.conversation_history

    def is_busy(self) -> bool:
        """Retorna True si el manager está procesando una respuesta"""
        return self.is_processing