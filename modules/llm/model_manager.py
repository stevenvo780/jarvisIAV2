import logging
import time
import threading
import os
from typing import List, Dict, Optional, Deque
from collections import deque

from .google_model import GoogleModel
from .openai_model import OpenAIModel
from .local_model import LocalModel

class ModelManager:
    CONFIG_DEFAULTS = {
        "models": {
            "google": {"difficulty_range": [0, 10]},
            "openai": {"difficulty_range": [7, 10]},
            "local": {"difficulty_range": [0, 6]}
        },
        "max_history": 10,
        "security": {
            "blocked_terms": [";", "&&", "|", "`", "$("]
        },
        "log_level": "INFO"
    }

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._validate_config(self.config)
        self.models = self._initialize_models()
        self._setup_logging()
        self.conversation_history = deque(maxlen=self.config["max_history"])
        self.processing_lock = threading.Lock()
        self.difficulty_analyzer = self.models.get('google')  # Usamos Google para analizar dificultad
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

    def _validate_query(self, query: str) -> bool:
        """Validates blocked terms. Returns True if valid."""
        lower_query = query.lower()
        for term in self.config['security']['blocked_terms']:
            if term.lower() in lower_query:
                logging.warning(f"Término bloqueado detectado en consulta: {term}")
                return False
        return True

    def _analyze_query_difficulty(self, query: str) -> int:
        """Analiza la dificultad de la consulta usando el modelo de Google."""
        try:
            prompt = f"""
            Por favor analiza la siguiente consulta y califica su dificultad del 1 al 10,
            donde 1 es muy simple y 10 es muy compleja. Responde solo con el número.
            
            Consulta: {query}
            """
            
            response = self.difficulty_analyzer.get_response(prompt)
            # Extraer el número de la respuesta
            difficulty = int(''.join(filter(str.isdigit, response)))
            return min(max(difficulty, 1), 10)  # Asegurar rango 1-10
        except Exception as e:
            logging.warning(f"Error analizando dificultad: {e}")
            return 5  # Dificultad media por defecto

    def _select_appropriate_model(self, difficulty: int) -> str:
        """Selecciona el modelo más apropiado según la dificultad."""
        for model_name, config in self.config['models'].items():
            diff_range = config['difficulty_range']
            if diff_range[0] <= difficulty <= diff_range[1]:
                if model_name in self.models:
                    return model_name
        
        return next(iter(self.models.keys()))  # Retorna el primer modelo disponible como fallback

    def get_response(self, query: str) -> str:
        """Obtiene respuesta seleccionando el modelo según dificultad."""
        try:
            if not self._validate_query(query):
                return "Lo siento, tu consulta no puede ser procesada por razones de seguridad."
            
            # Analizar dificultad
            difficulty = self._analyze_query_difficulty(query)
            logging.info(f"Dificultad detectada: {difficulty}/10")
            
            # Seleccionar modelo
            model_name = self._select_appropriate_model(difficulty)
            logging.info(f"Modelo seleccionado: {model_name}")
            
            # Obtener respuesta
            response = self.models[model_name].get_response(query)
            
            # Guardar en historial
            self.conversation_history.append({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model": model_name,
                "difficulty": difficulty,
                "query": query,
                "response": response
            })
            
            return response
            
        except Exception as e:
            logging.error(f"Error procesando consulta: {e}")
            return "Lo siento, ha ocurrido un error procesando tu consulta."

    def get_history(self) -> List[Dict]:
        """Returns conversation history."""
        return list(self.conversation_history)
