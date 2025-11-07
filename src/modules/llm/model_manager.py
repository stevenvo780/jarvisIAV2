import logging
import os
import json
import re
from typing import List, Dict, Tuple, Optional
from src.modules.llm.google_model import GoogleModel
from src.modules.llm.openai_model import OpenAIModel
from src.modules.llm.local_model import LocalModel
from src.modules.llm.deepinfra_model import DeepInfraModel
from src.utils.query_validator import QueryValidator

class ModelManager:
    def __init__(self,storage_manager, tts):
        self.tts = tts
        self.storage = storage_manager
        self.config = self._load_config('src/config/config.json')
        self._validate_config(self.config)
        self.models = self._initialize_models()
        self.user_profile = self._load_user_profile('src/config/config.json')
        self.difficulty_analyzer = self.models.get('google')
        self.tts = None
        self._setup_logging()
        
        # Initialize enhanced query validator
        self.query_validator = QueryValidator(
            max_length=self.config.get('security', {}).get('max_query_length', 5000),
            blocked_terms=self.config.get('security', {}).get('blocked_terms', []),
            strict_mode=self.config.get('security', {}).get('strict_input_validation', True)
        )
        
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
            
            if diff_range[0] > diff_range[1] or diff_range[0] < 1 or diff_range[1] > 100:
                raise ValueError(f"Rango de dificultad inválido para {model_name} (debe estar entre 1 y 100)")
        
        if not isinstance(config.get("security", {}).get("blocked_terms", []), list):
            raise ValueError("Configuración inválida: blocked_terms debe ser una lista")
        
        return config

    def _initialize_models(self) -> Dict[str, object]:
        instantiated = {}
        errors = []
        
        for model_name in self.config['models']:
            try:
                if model_name == "google":
                    instantiated[model_name] = GoogleModel()
                elif model_name == "openai":
                    instantiated[model_name] = OpenAIModel()
                elif model_name == "local":
                    instantiated[model_name] = LocalModel()
                elif model_name == "deepinfra":
                    instantiated[model_name] = DeepInfraModel()
                else:
                    errors.append(f"Modelo no reconocido: {model_name}")
                    continue
                logging.info(f"Modelo {model_name} inicializado correctamente")
            except ImportError as ie:
                error_msg = f"Error importando módulo {model_name}: {str(ie)}"
                logging.error(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error inicializando modelo {model_name}: {e.__class__.__name__} - {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)

        if not instantiated:
            error_summary = "\n".join(errors)
            error_msg = f"Fallo crítico: No se pudo inicializar ningún modelo.\nDetalles:\n{error_summary}"
            logging.critical(error_msg)
            raise RuntimeError(error_msg)
            
        if len(instantiated) < len(self.config['models']):
            error_summary = "\n".join(errors)
            logging.warning(f"Algunos modelos fallaron en inicializar:\n{error_summary}")
            
        return instantiated

    def _setup_logging(self):
        logger = logging.getLogger('ModelManager')
        logger.setLevel(self.config.get('log_level', 'INFO'))
        if not logger.handlers:
            handler = logging.FileHandler('logs/jarvis.log', encoding='utf-8')
            fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(fmt)
            logger.addHandler(handler)

    def _validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Enhanced query validation with security checks
        
        Returns:
            (is_valid, error_message)
        """
        return self.query_validator.validate(query)

    def _analyze_query_difficulty(self, query: str) -> int:
        """
        Robust difficulty analysis with fallback
        
        Returns:
            Difficulty score (1-100)
        """
        try:
            context = self.storage.get_context()
            template = context['prompts']['difficulty_analysis']['template']
            prompt = template.format(query=query)
            
            if self.difficulty_analyzer is None:
                logging.warning("difficulty_analyzer no configurado, utilizando dificultad predeterminada")
                return context['prompts']['difficulty_analysis'].get('default_difficulty', 50)
            
            response = self.difficulty_analyzer.get_response(prompt)
            
            # Extract number with regex (more robust)
            match = re.search(r'\b(\d{1,3})\b', response)
            
            if match:
                difficulty = int(match.group(1))
                # Clamp to valid range
                return min(max(difficulty, 1), 100)
            else:
                logging.warning(f"No difficulty found in response: {response[:100]}")
                return context['prompts']['difficulty_analysis'].get('default_difficulty', 50)
        
        except ValueError as e:
            logging.error(f"Difficulty parsing error: {e}")
            return 50  # Conservative default
        except KeyError as e:
            logging.error(f"Configuration key missing: {e}")
            return 50
        except Exception as e:
            logging.error(f"Difficulty analysis failed: {e}")
            return 50  # Fail-safe default

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

    def get_response(self, query: str) -> Tuple[str, str]:
        try:
            # Enhanced validation
            is_valid, error_msg = self._validate_query(query)
            if not is_valid:
                logging.warning(f"Query validation failed: {error_msg}")
                return f"Query rejected: {error_msg}", "error"
            
            # Sanitize query
            query = self.query_validator.sanitize(query)

            logging.info(f"Consulta recibida: {query}")
            difficulty = self._analyze_query_difficulty(query)
            logging.info(f"Dificultad estimada: {difficulty}")
            model_name = self._select_appropriate_model(difficulty)
            
            context = self.storage.get_context()
            history = self.storage.get_recent_history(self.config['system']['history']['default_size'])
            
            system_prompt = self._build_context_prompt(context, history, model_name)
            
            user_prompt = context['prompts']['templates']['query'].format(
                input=query,
                name=context['assistant_profile']['name']
            )
            
            enriched_query = f"{system_prompt}\n\n{user_prompt}"
            
            response = self.models[model_name].get_response(enriched_query)
            response = self._filter_response(response)
            
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

    def _filter_response(self, response: str) -> str:
        import re
        filtered = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        filtered = re.sub(r'^PENSAMIENTO:.*(?:\n|$)', '', filtered, flags=re.MULTILINE)
        return filtered.strip()

    def _build_context_prompt(self, context: Dict, history: list, model_name: str) -> str:
        try:
            template = context['prompts']['system_context'][model_name]['template']
            
            model_config = self.config['models'][model_name]
            history_limit = model_config.get('history_context', 1)
            limited_history = history[-history_limit:] if history_limit > 0 else []
            history_text = self._format_history(limited_history)
            
            prompt_data = {
                    'name': context['assistant_profile']['name'],
                    'personality': context['assistant_profile']['personality'],
                    'conversation_history': history_text,
                    'format_response': context['prompts']['system_context'][model_name]['format_response'],
                    'core_traits': '\n'.join(f"- {trait}" for trait in context['assistant_profile']['core_traits']),
                    'user_context': self._build_user_context()
                }
                
            
            return template.format(**prompt_data)
        except Exception as e:
            logging.error(f"Error building context prompt: {e}")
            return context['prompts']['system_base'].format(
                name=context['assistant_profile']['name']
            )

    def _format_history(self, history: list) -> str:
        if not history:
            return self.config['system']['history']['empty_message']
        entries = []
        for entry in history:
            entries.append(f"Usuario: {entry['query']}\nAsistente: {entry['response']}")
        return "\n".join(entries)

    def get_history(self) -> List[Dict]:
        return list(self.storage.get_recent_history(self.config['max_history']))