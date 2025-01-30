import logging
import os
import json
from typing import List, Dict, Tuple
from src.modules.llm.google_model import GoogleModel
from src.modules.llm.openai_model import OpenAIModel
from src.modules.llm.local_model import LocalModel

class ModelManager:
    def __init__(self, storage_manager, config_path: str = "src/config/config.json", user_profile_path: str = "src/data/user_profile.json"):
        self.storage = storage_manager
        self.config = self._load_config(config_path)
        self._validate_config(self.config)
        self.models = self._initialize_models()
        self.user_profile = self._load_user_profile(user_profile_path)
        self.difficulty_analyzer = self.models.get('google')
        self.tts = None
        self._setup_logging()
        self._merge_config_with_context()
        logging.info("ModelManager inicializado")

    def _load_user_profile(self, path: str) -> Dict:
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f).get('user_info', {})
            return {}
        except Exception as e:
            logging.error(f"Error cargando perfil de usuario: {e}")
            return {}

    def _build_user_context(self) -> str:
        context_lines = []
        profile = self.user_profile
        
        if profile.get('name'):
            context_lines.append(f"Usuario: {profile['name']}")
        if profile.get('profession'):
            context_lines.append(f"Profesión: {profile['profession']}")
        
        if 'knowledge_base' in profile:
            context_lines.append("\nÁreas de conocimiento:")
            context_lines.extend([f"- {kb}" for kb in profile['knowledge_base']])
        
        if 'philosophical_profile' in profile:
            context_lines.append("\nPerfil filosófico:")
            for key, value in profile['philosophical_profile'].items():
                context_lines.append(f"- {key.capitalize()}: {value}")
        
        if profile.get('personal_site'):
            context_lines.append(f"\nRecurso principal: {profile['personal_site']}")
        
        return "\n".join(context_lines) if context_lines else ""

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
            raise RuntimeError("No se pudo cargar la configuración necesaria")

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
                    instantiated[model_name] = GoogleModel()
                elif model_name == "openai":
                    instantiated[model_name] = OpenAIModel()
                elif model_name == "local":
                    instantiated[model_name] = LocalModel()
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
            context = self.storage.get_context()
            template = context['prompts']['difficulty_analysis']['template']
            prompt = template.format(query=query)
            response = self.difficulty_analyzer.get_response(prompt)
            difficulty = int(''.join(filter(str.isdigit, response)))
            return min(max(difficulty, 1), 10)
        except Exception as e:
            logging.warning(f"Error analizando dificultad: {e}")
            context = self.storage.get_context()
            return context['prompts']['difficulty_analysis']['default_difficulty']

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

    def get_response(self, query: str) -> Tuple[str, str]:
        try:
            if query.lower().strip() in self.config['system']['stop_commands']:
                return "Vale", "system"

            if not self._validate_query(query):
                return self.config['system']['error_messages']['security'], "error"

            logging.info(f"Consulta recibida: {query}")
            difficulty = self._analyze_query_difficulty(query)
            logging.info(f"Dificultad estimada: {difficulty}")
            model_name = self._select_appropriate_model(difficulty)
            
            context = self.storage.get_context()
            history = self.storage.get_recent_history(self.config['system']['history']['default_size'])
            
            system_prompt = self._build_context_prompt(context, history, model_name)
            print(f"System Prompt: {system_prompt}")
            user_prompt = context['prompts']['templates']['query'].format(
                input=query,
                name=context['assistant_profile']['name']
            )
            
            enriched_query = f"{system_prompt}\n\n{user_prompt}"
            response = self.models[model_name].get_response(enriched_query)
            
            self.storage.add_interaction({
                "query": query,
                "response": response,
                "model": model_name,
                "difficulty": difficulty
            })
            
            return response, model_name
            
        except Exception as e:
            logging.error(f"Error procesando consulta: {e}")
            return self.config['system']['error_messages']['general'], "error"

    def _merge_config_with_context(self):
        try:
            context = self.storage.get_context()
            if not context:
                return
            
            # Se elimina la fusión de 'assistant_profile' y 'prompts' para evitar conflictos
                
        except Exception as e:
            logging.error(f"Error fusionando configuración con contexto: {e}")
            logging.debug("Continuando con el contexto actual sin fusionar cambios.")

    def _build_context_prompt(self, context: Dict, history: list, model_name: str) -> str:
        try:
            if (model_name not in context['prompts']['system_context']):
                model_name = 'local'
                
            template = context['prompts']['system_context'][model_name]['template']
            format_type = context['prompts']['system_context'][model_name]['format']
            
            # Tomar solo el historial necesario para cada modelo
            model_config = self.config['models'][model_name]
            history_limit = model_config.get('history_context', 1)
            limited_history = history[-history_limit:] if history_limit > 0 else []
            history_text = self._format_history(limited_history, format_type)
            
            prompt_data = {
                    'name': context['assistant_profile']['name'],
                    'personality': context['assistant_profile']['personality'],
                    'conversation_history': history_text,
                    'core_traits': '\n'.join(f"- {trait}" for trait in context['assistant_profile']['core_traits']),
                    'user_context': self._build_user_context()
                }
                
            
            return template.format(**prompt_data)
        except Exception as e:
            logging.error(f"Error building context prompt: {e}")
            return context['prompts']['system_base'].format(
                name=context['assistant_profile']['name']
            )

    def _format_history(self, history: list, format_type: str) -> str:
        if not history:
            return self.config['system']['history']['empty_message']
            
        entries = []
        for entry in history:
            if format_type == 'chat':
                entries.append(f"Usuario: {entry['query']}\nAsistente: {entry['response']}")
            else:
                entries.append(f"{entry['query']} -> {entry['response']}")
        return "\n".join(entries)

    def get_history(self) -> List[Dict]:
        return list(self.storage.get_recent_history(self.config['max_history']))