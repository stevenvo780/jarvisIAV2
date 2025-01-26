import logging
import time
import threading
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Deque
from collections import deque
from .google_model import GoogleModel
from .openai_model import OpenAIModel
from .local_model import LocalModel

class ModelManager:
    CONFIG_DEFAULTS = {
        "models": {
            "google": {"difficulty_range": [4, 7]},
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
        self.context = self._load_context()
        self.config = self._load_config(config_path)
        self._validate_config(self.config)
        self.models = self._initialize_models()
        self._setup_logging()
        self.conversation_history = deque(maxlen=self.config["max_history"])
        self.processing_lock = threading.Lock()
        self.difficulty_analyzer = self.models.get('google')
        self.tts = None
        logging.info("ModelManager inicializado")

    def _load_context(self) -> Dict:
        context_path = Path(__file__).parent.parent.parent / "data" / "jarvis_context.json"
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando contexto: {e}")
            return {}

    def _load_config(self, config_path: str) -> Dict:
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
        if not isinstance(config.get("models"), dict):
            raise ValueError("Configuración inválida: 'models' debe ser un diccionario")
        
        for model_name, model_config in config["models"].items():
            if "difficulty_range" not in model_config:
                raise ValueError(f"Configuración inválida: falta difficulty_range para {model_name}")
            
            diff_range = model_config["difficulty_range"]
            if not isinstance(diff_range, list) or len(diff_range) != 2:
                raise ValueError(f"difficulty_range inválido para {model_name}")
            
            if diff_range[0] > diff_range[1] or diff_range[0] < 0 or diff_range[1] > 10:
                raise ValueError(f"Rango de dificultad inválido para {model_name}")
        
        if not isinstance(config.get("security", {}).get("blocked_terms", []), list):
            raise ValueError("Configuración inválida: blocked_terms debe ser una lista")
        
        return config

    def _initialize_models(self) -> Dict[str, object]:
        instantiated = {}
        for model_name in self.config['models']:
            try:
                if model_name == "google":
                    try:
                        instantiated[model_name] = GoogleModel()
                    except Exception as e:
                        logging.error(f"Error inicializando Google: {e}")
                        continue
                elif model_name == "openai":
                    try:
                        instantiated[model_name] = OpenAIModel()
                    except Exception as e:
                        logging.error(f"Error inicializando OpenAI: {e}")
                        continue
                elif model_name == "local":
                    try:
                        instantiated[model_name] = LocalModel()
                    except Exception as e:
                        logging.error(f"Error inicializando Local: {e}")
                        continue
                else:
                    logging.warning(f"Modelo '{model_name}' no reconocido")
            except Exception as e:
                logging.error(f"Error inicializando {model_name}: {str(e)}")
        if not instantiated:
            raise RuntimeError("No se pudo inicializar ningún modelo")
        return instantiated

    def _setup_logging(self):
        logger = logging.getLogger('ModelManager')
        logger.setLevel(self.config.get('log_level', 'INFO'))
        if not logger.handlers:
            handler = logging.FileHandler('logs/jarvis.log', encoding='utf-8')
            fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(fmt)
            logger.addHandler(handler)

    def _validate_query(self, query: str) -> bool:
        lower_query = query.lower()
        for term in self.config['security']['blocked_terms']:
            if term.lower() in lower_query:
                logging.warning(f"Término bloqueado detectado en consulta: {term}")
                return False
        return True

    def _analyze_query_difficulty(self, query: str) -> int:
        try:
            prompt = f"""
            Por favor analiza la siguiente consulta y califica su dificultad del 1 al 10,
            donde 1 es muy simple y 10 es muy compleja. Responde solo con el número.
            
            Consulta: {query}
            """
            
            response = self.difficulty_analyzer.get_response(prompt)
            difficulty = int(''.join(filter(str.isdigit, response)))
            return min(max(difficulty, 1), 10)
        except Exception as e:
            logging.warning(f"Error analizando dificultad: {e}")
            return 5

    def _select_appropriate_model(self, difficulty: int) -> str:
        available_models = self.models.keys()
        
        for model_name, config in self.config['models'].items():
            diff_range = config['difficulty_range']
            if diff_range[0] <= difficulty <= diff_range[1] and model_name in available_models:
                return model_name
        
        if difficulty >= 7 and "google" in available_models:
            return "google"
        elif "local" in available_models:
            return "local"
        
        return next(iter(available_models))

    def set_tts_manager(self, tts_manager):
        self.tts = tts_manager

    def get_response(self, query: str) -> str:
        try:
            if query.lower().strip() in ['stop', 'para', 'detente', 'silencio']:
                return "He detenido la reproducción.", "system"

            if not self._validate_query(query):
                return "Lo siento, tu consulta no puede ser procesada por razones de seguridad.", "error"
            
            difficulty = self._analyze_query_difficulty(query)
            logging.info(f"Dificultad detectada: {difficulty}/10")
            
            model_name = self._select_appropriate_model(difficulty)
            logging.info(f"Modelo seleccionado: {model_name}")
            
            system_prompt = self._build_context_prompt()
            user_prompt = self.context['prompts']['templates']['query'].format(
                input=query,
                name=self.context['assistant_profile']['name']
            )
            
            enriched_query = f"{system_prompt}\n\n{user_prompt}"
            
            response = self.models[model_name].get_response(enriched_query)
            
            self._update_context(query, response)
            
            self.conversation_history.append({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model": model_name,
                "difficulty": difficulty,
                "query": query,
                "response": response
            })
            
            return response, model_name
            
        except Exception as e:
            logging.error(f"Error procesando consulta: {e}")
            return "Lo siento, ha ocurrido un error procesando tu consulta.", "error"

    def _update_context(self, query: str, response: str):
        try:
            self.context["interaction_stats"]["total_interactions"] += 1
            self.context["interaction_stats"]["last_interaction"] = time.strftime("%Y-%m-%dT%H:%M:%S.%f")
            
            topic = query.split()[0].lower()
            self.context["interaction_stats"]["frequent_topics"][topic] = \
                self.context["interaction_stats"]["frequent_topics"].get(topic, 0) + 1

            context_path = Path(__file__).parent.parent.parent / "data" / "jarvis_context.json"
            with open(context_path, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error actualizando contexto: {e}")

    def _build_context_prompt(self) -> str:
        profile = self.context.get("assistant_profile", {})
        model_name = self._select_appropriate_model(0)
        
        model_template = self.context['prompts']['system_context'][model_name]['template']
        
        traits = "\n".join(f"- {trait}" for trait in profile.get('core_traits', []))
        
        return model_template.format(
            name=profile.get('name', 'Jarvis'),
            personality=profile.get('personality', 'profesional y servicial'),
            traits=traits
        )

    def get_history(self) -> List[Dict]:
        return list(self.conversation_history)