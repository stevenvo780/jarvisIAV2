import logging
import time
import threading
import sys
import os
from typing import List, Dict, Optional, Deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from collections import deque
import psutil

# Importar las clases reales en lugar de los stubs
from .google_model import GoogleModel
from .openai_model import OpenAIModel
from .local_model import LocalModel


class SecurityError(Exception):
    pass


class ModelManager:
    CONFIG_DEFAULTS = {
        "models": ["google", "openai", "local"],
        "timeouts": {"google": 15, "openai": 20, "local": 30},
        "retry_policy": {"max_retries": 3, "backoff_base": 2, "max_delay": 60},
        "fallback_order": ["google", "openai", "local"],
        "max_history": 10,
        "security": {
            "max_query_length": 2000,
            "blocked_terms": [";", "&&", "|", "`", "$("]
        },
        # Nivel de log (INFO, DEBUG, etc.)
        "log_level": "INFO"
    }

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._validate_config(self.config)
        self.models = self._initialize_models()
        self._setup_logging()
        self._validate_system()
        self.conversation_history: Deque[Dict] = deque(maxlen=self.config["max_history"])
        self.processing_lock = threading.Lock()
        logging.info("ModelManager inicializado")

    def _load_config(self, config_path: str) -> Dict:
        """Loads or merges JSON config if exists."""
        import json
        if not os.path.exists(config_path):
            return dict(self.CONFIG_DEFAULTS)
        try:
            with open(config_path, 'r') as f:
                file_conf = json.load(f)
        except (json.JSONDecodeError, ValueError):
            file_conf = {}
        merged_conf = dict(self.CONFIG_DEFAULTS)
        merged_conf.update(file_conf)
        return merged_conf

    def _validate_config(self, config: Dict) -> Dict:
        """Validates essential config fields."""
        # Ensure all fallback_order models are in 'models'
        if not all(m in config["models"] for m in config["fallback_order"]):
            raise ValueError("Configuración inválida: fallback_order contiene modelos no declarados")
        # Validate security
        if any(term.strip() == "" for term in config["security"]["blocked_terms"]):
            raise ValueError("Términos bloqueados inválidos en configuración")
        # Validate timeouts
        for model in config["timeouts"]:
            if config["timeouts"][model] <= 0:
                raise ValueError(f"Timeout inválido para modelo {model}")
        return config

    def _initialize_models(self) -> Dict[str, object]:
        """Instantiates models defined in 'models' list."""
        instantiated = {}
        for model_name in self.config['models']:
            try:
                if model_name == "google":
                    instantiated[model_name] = GoogleModel()
                elif model_name == "openai":
                    instantiated[model_name] = OpenAIModel()
                elif model_name == "local":
                    instantiated[model_name] = LocalModel()
                else:
                    logging.warning(f"Modelo '{model_name}' no reconocido")
            except Exception as e:
                logging.exception(f"Error inicializando {model_name}: {str(e)}")
        if not instantiated:
            raise RuntimeError("No se pudo inicializar ningún modelo")
        return instantiated

    def _setup_logging(self):
        """Configures the logger."""
        logger = logging.getLogger('ModelManager')
        logger.setLevel(self.config.get('log_level', 'INFO'))
        if not logger.handlers:
            handler = logging.FileHandler('logs/jarvis.log', encoding='utf-8')
            fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(fmt)
            logger.addHandler(handler)

    def _validate_system(self):
        """Checks system resources like memory and CPU usage."""
        if psutil.virtual_memory().percent > 90:
            logging.warning("Memoria del sistema alta (>90%)")
        if psutil.cpu_percent(interval=1) > 90:
            logging.warning("Uso de CPU alto (>90%)")

    def _validate_query(self, query: str):
        """Prevents excessively long queries or blocked terms."""
        if len(query) > self.config['security']['max_query_length']:
            raise SecurityError("Consulta demasiado larga")
        lower_query = query.lower()
        if any(term.lower() in lower_query for term in self.config['security']['blocked_terms']):
            raise SecurityError("Consulta contiene términos potencialmente peligrosos")

    def _process_with_model(self, model_name: str, query: str) -> Optional[str]:
        """
        Calls the model using ThreadPoolExecutor and handles retries/backoff.
        Returns response or None if fails.
        """
        retries = self.config['retry_policy']['max_retries']
        backoff_base = self.config['retry_policy']['backoff_base']
        max_delay = self.config['retry_policy']['max_delay']
        model_timeout = self.config['timeouts'].get(model_name, 15)

        for attempt in range(retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.models[model_name].get_response, query)
                    return future.result(timeout=model_timeout)
            except Exception as e:
                logging.warning(f"Fallo en '{model_name}' (Intento {attempt+1}/{retries}): {str(e)}")
                if attempt < retries:
                    backoff_time = min(backoff_base ** attempt, max_delay)
                    time.sleep(backoff_time)
        return None

    def get_response(self, query: str) -> str:
        """
        Attempts to get a response using fallback_order (e.g. Google -> OpenAI -> Local).
        Returns the first valid response found.
        """
        # Validate query
        try:
            self._validate_query(query)
        except SecurityError as e:
            logging.warning(f"Consulta bloqueada: {str(e)}")
            return "Consulta rechazada por motivos de seguridad."

        # (Animaciones deshabilitadas, se removieron por completo)
        try:
            for model_name in self.config['fallback_order']:
                # Skip if model wasn't initialized
                if model_name not in self.models:
                    continue

                response = self._process_with_model(model_name, query)
                if response:
                    # Save to history
                    self.conversation_history.append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "model": model_name,
                        "query": query,
                        "response": response
                    })
                    return response

            return "Error: Ningún modelo pudo responder."
        finally:
            # No spinner/animation cleanup needed
            pass

    def get_history(self) -> List[Dict]:
        """Returns conversation history."""
        return list(self.conversation_history)
