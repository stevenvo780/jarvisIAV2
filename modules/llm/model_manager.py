import json
import logging
import time
import itertools
import threading
import sys
import os
from typing import List, Dict, Optional, Deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from collections import deque
import psutil

class SecurityError(Exception):
    pass

class GoogleModel:
    def __init__(self, config):
        pass
    def get_response(self, query):
        time.sleep(1)
        return f"Respuesta de Google: {query}"

class OpenAIModel:
    def __init__(self, config):
        pass
    def get_response(self, query):
        time.sleep(2)
        return f"Respuesta de OpenAI: {query}"

class LocalModel:
    def __init__(self, config):
        pass
    def get_response(self, query):
        time.sleep(3)
        return f"Respuesta del Modelo Local: {query}"

class ModelManager:
    CONFIG_DEFAULTS = {
        "models": ["google", "openai", "local"],
        "timeouts": {"google": 15, "openai": 20, "local": 30},
        "retry_policy": {"max_retries": 3, "backoff_base": 2, "max_delay": 60},
        "fallback_order": ["google", "openai", "local"],
        "max_history": 10,
        "security": {"max_query_length": 2000, "blocked_terms": [";", "&&", "|", "`", "$("]},
    }

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._validate_config(self.config)  # Pasando config como argumento
        self.models = self._initialize_models()
        self._setup_logging()
        self._validate_system()
        self.conversation_history: Deque[Dict] = deque(maxlen=self.config["max_history"])
        self.thinking_animation_active = False
        self.thinking_thread: Optional[threading.Thread] = None
        self.processing_lock = threading.Lock()
        logging.info("ModelManager inicializado")

    def _load_config(self, config_path: str) -> Dict:
        if not os.path.exists(config_path):
            return self.CONFIG_DEFAULTS
        try:
            with open(config_path, 'r') as f:
                return self._validate_config(json.load(f))
        except (json.JSONDecodeError, ValueError):
            return self.CONFIG_DEFAULTS

    def _validate_config(self, config: Dict) -> Dict:
        config = {**self.CONFIG_DEFAULTS, **config}
        if not all(m in config["models"] for m in config["fallback_order"]):
            raise ValueError("Configuración inválida: fallback_order")
        if any(term.strip() == "" for term in config["security"]["blocked_terms"]):
            raise ValueError("Términos bloqueados inválidos")
        return config

    def _initialize_models(self) -> Dict:
        models = {}
        for model_name in self.config['models']:
            try:
                if model_name == "google":
                    models[model_name] = GoogleModel(config={})
                elif model_name == "openai":
                    models[model_name] = OpenAIModel(config={})
                elif model_name == "local":
                    models[model_name] = LocalModel(config={})
            except Exception:
                logging.exception(f"Error inicializando {model_name}")
        if not models:
            raise RuntimeError("Ningún modelo inicializado")
        return models

    def _setup_logging(self):
        logger = logging.getLogger('ModelManager')
        logger.setLevel(self.config.get('log_level', 'INFO'))
        if not logger.handlers:
            handler = logging.FileHandler('logs/jarvis.log', encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)

    def _validate_system(self):
        if psutil.virtual_memory().percent > 90:
            logging.warning("Memoria del sistema baja")
        if psutil.cpu_percent(interval=1) > 90:
            logging.warning("Uso de CPU alto")

    def _start_thinking_animation(self):
        with self.processing_lock:
            self.thinking_animation_active = True
            self.thinking_thread = threading.Thread(target=self._animate_loading, daemon=True)
            self.thinking_thread.start()

    def _animate_loading(self):
        for frame in itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']):
            with self.processing_lock:
                if not self.thinking_animation_active:
                    return
            sys.stdout.write(f'\rProcesando {frame}')
            sys.stdout.flush()
            time.sleep(0.1)

    def _stop_thinking_animation(self):
        with self.processing_lock:
            self.thinking_animation_active = False
        if self.thinking_thread:
            self.thinking_thread.join(timeout=0.5)

    def _validate_query(self, query: str):
        if len(query) > self.config['security']['max_query_length']:
            raise SecurityError("Consulta demasiado larga")
        lower_query = query.lower()
        if any(term.lower() in lower_query for term in self.config['security']['blocked_terms']):
            raise SecurityError("Consulta contiene términos bloqueados")

    def _process_with_model(self, model_name: str, query: str) -> Optional[str]:
        retries = self.config['retry_policy']['max_retries']
        backoff_base = self.config['retry_policy']['backoff_base']
        max_delay = self.config['retry_policy']['max_delay']

        for attempt in range(retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=len(self.models)) as executor:
                    future = executor.submit(self.models[model_name].get_response, query)
                    return future.result(timeout=self.config['timeouts'][model_name])
            except Exception as e:
                logging.warning(f"Intento {attempt+1} en {model_name}: {str(e)}")
                if attempt < retries:
                    time.sleep(min(backoff_base ** attempt, max_delay))
        return None

    def get_response(self, query: str) -> str:
        try:
            self._validate_query(query)
        except SecurityError as e:
            logging.warning(f"Consulta bloqueada: {str(e)}")
            return "Consulta rechazada por seguridad."

        self._start_thinking_animation()
        try:
            for model_name in self.config['fallback_order']:
                if response := self._process_with_model(model_name, query):
                    self.conversation_history.append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": query,
                        "response": response
                    })
                    return response
            return "Error: Todos los modelos fallaron"
        finally:
            self._stop_thinking_animation()

    def get_history(self) -> List[Dict]:
        return list(self.conversation_history)