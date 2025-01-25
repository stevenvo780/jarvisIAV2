import json
import logging
import time
import itertools
import threading
import sys
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from .local_model import LocalModel
from .google_model import GoogleModel
from .openai_model import OpenAIModel
from ..storage_manager import StorageManager

class ModelManager:
    def __init__(self, config_path: str, timeout_in_seconds: int = 5,
                 max_retries: int = 3, context_size: int = 5):
        self.timeout = timeout_in_seconds
        self.max_retries = max_retries
        self.context_size = context_size
        self.thinking_animation = None
        self.stop_thinking = False
        self.is_processing = False
        
        self._setup_logging()
        self._initialize_models()
        self.storage = StorageManager()
        self.conversation_history = self.storage.load_conversation()
        
        # Load configuration from JSON
        self.model_order = []
        self.model_levels = {}
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                for model_info in config_data.get('modelos', []):
                    model_name = model_info['nombre'].lower()
                    nivel = model_info['nivel_capacitacion'].lower()
                    if model_name in self.models:
                        self.model_levels[model_name] = nivel
                        self.model_order.append(model_name)
                    else:
                        logging.warning(f"Model {model_name} not found in available models")
        except Exception as e:
            logging.error(f"Error loading config file: {e}")
            # Default configuration
            self.model_order = ["openai", "google", "local"]
            self.model_levels = {
                "openai": "alto",
                "google": "medio",
                "local": "bajo"
            }

    def _setup_logging(self):
        logging.basicConfig(
            filename="logs/jarvis.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )
    
    def _initialize_models(self):
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
                logging.error(f"Timeout after {self.timeout} seconds with {model}")
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
                    logging.info(f"Model {model_name} responded in {duration:.2f}s")
                    return response
            except Exception as e:
                logging.error(f"Error with {model_name} (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        return None

    def _evaluate_complexity(self, query: str) -> str:
        evaluator_model = self.models.get('local')
        if not evaluator_model:
            logging.error("Local model not available for complexity evaluation")
            return 'medio'
        prompt = f"Clasifica la complejidad de la siguiente pregunta como 'bajo', 'medio' o 'alto'. Responde solo con una de esas palabras en minúsculas. Pregunta: {query}"
        try:
            response = evaluator_model.get_response(prompt)
            response = response.strip().lower()
            if response in ['bajo', 'medio', 'alto']:
                return response
            else:
                logging.warning(f"Invalid complexity evaluation: {response}, defaulting to 'medio'")
                return 'medio'
        except Exception as e:
            logging.error(f"Error evaluating complexity: {e}, defaulting to 'medio'")
            return 'medio'

    def _generate_priority_list(self, evaluated_complexity: str) -> List[str]:
        level_order = {'alto': 3, 'medio': 2, 'bajo': 1}
        evaluated_level = level_order.get(evaluated_complexity.lower(), 2)
        
        model_info_list = []
        for idx, model_name in enumerate(self.model_order):
            model_level = self.model_levels.get(model_name, 'bajo')
            model_level_order = level_order.get(model_level, 1)
            model_info_list.append((model_name, model_level_order, idx))
        
        group_exact = []
        group_higher = []
        group_lower = []
        for model_name, level, idx in model_info_list:
            if level == evaluated_level:
                group_exact.append((model_name, level, idx))
            elif level > evaluated_level:
                group_higher.append((model_name, level, idx))
            else:
                group_lower.append((model_name, level, idx))
        
        group_exact_sorted = sorted(group_exact, key=lambda x: (-x[1], x[2]))
        group_higher_sorted = sorted(group_higher, key=lambda x: (x[1], x[2]))
        group_lower_sorted = sorted(group_lower, key=lambda x: (-x[1], x[2]))
        
        priority_list = [x[0] for x in group_exact_sorted + group_higher_sorted + group_lower_sorted]
        return priority_list

    def get_response(self, query: str) -> str:
        self.is_processing = True
        self._start_thinking_animation()
        
        try:
            evaluated_complexity = self._evaluate_complexity(query)
            logging.info(f"Evaluated complexity: {evaluated_complexity}")
            priority_list = self._generate_priority_list(evaluated_complexity)
            logging.info(f"Using priority list: {priority_list}")
            
            if len(self.conversation_history) >= self.context_size:
                self.conversation_history.pop(0)
            self.conversation_history.append({
                "query": query,
                "complexity": evaluated_complexity
            })
            
            for model_name in priority_list:
                response = self._try_model_with_retry(model_name, query)
                if response:
                    self.conversation_history[-1]["response"] = response
                    self.conversation_history[-1]["model"] = model_name
                    self.storage.save_conversation(self.conversation_history)
                    return response
            
            default_response = "Lo siento, no pude procesar tu solicitud en este momento."
            self.conversation_history[-1]["response"] = default_response
            self.storage.save_conversation(self.conversation_history)
            return default_response
        finally:
            self._stop_thinking_animation()
            self.is_processing = False

    def clear_context(self):
        self.conversation_history.clear()
        self.storage.clear_history()

    def get_conversation_history(self) -> List[dict]:
        return self.conversation_history

    def is_busy(self) -> bool:
        return self.is_processing