import os
import logging
import time
from typing import Optional, Dict, Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from pathlib import Path

class LocalModel:
    DEFAULT_MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    
    SIMPLE_RESPONSES = {
        "hola": "¡Hola! ¿En qué puedo ayudarte hoy?",
        "hora": lambda: f"Son las {time.strftime('%H:%M:%S')}",
        "fecha": lambda: f"Hoy es {time.strftime('%A, %d de %B de %Y')}",
        "ayuda": "Puedes preguntarme sobre:\n- La hora actual\n- La fecha\n- Temas generales\n¡Intenta hacerme una pregunta!",
        "creditos": "Soy TinyLlama-1.1B ejecutándome localmente. Un modelo pequeño pero capaz."
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            'timeout': 30,
            'max_length': 1000,
            'n_threads': os.cpu_count()
        }
        self._validate_config()
        self.model = self._initialize_model()
        logging.info("LocalModel inicializado")

    def _validate_config(self):
        """Valida la configuración del modelo."""
        if not isinstance(self.config, dict):
            raise ValueError("La configuración debe ser un diccionario")

        required_keys = ['timeout', 'max_length', 'n_threads']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Falta la clave de configuración requerida: {key}")

        if not isinstance(self.config['timeout'], (int, float)) or self.config['timeout'] <= 0:
            raise ValueError("'timeout' debe ser un número positivo")

        if not isinstance(self.config['max_length'], int) or self.config['max_length'] <= 0:
            raise ValueError("'max_length' debe ser un entero positivo")

        if not isinstance(self.config['n_threads'], int) or self.config['n_threads'] <= 0:
            raise ValueError("'n_threads' debe ser un entero positivo")

    def _initialize_model(self):
        try:
            if torch.cuda.is_available():
                logging.info(f"CUDA disponible: {torch.cuda.get_device_name(0)}")
            else:
                logging.warning("CUDA no disponible, usando CPU")

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                padding_side="left",
                truncation_side="left"
            )
            
            # Cargamos el modelo usando accelerate automáticamente
            model = AutoModelForCausalLM.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                low_cpu_mem_usage=True,
                device_map="auto"
            )

            # Creamos el pipeline sin especificar device
            self.pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=self.tokenizer,
                truncation=True,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            return model

        except Exception as e:
            logging.error(f"Error crítico al inicializar modelo: {str(e)}")
            raise RuntimeError(f"No se pudo cargar el modelo local: {str(e)}")

    def get_response(self, query: str) -> str:
        """Genera una respuesta usando el modelo local."""
        query = query.lower().strip()
        
        if response := self._get_simple_response(query):
            return response
        
        try:
            prompt = self._build_prompt(query)
            response = self.pipeline(
                prompt,
                max_new_tokens=256,
                return_full_text=False  # Solo devolver el texto nuevo
            )[0]['generated_text']
            
            return self._process_response(response)
            
        except Exception as e:
            logging.error(f"Error generando respuesta: {str(e)}")
            return "Error procesando tu solicitud"

    def _build_prompt(self, query: str) -> str:
        return f"[INST] {query} [/INST]"

    def _process_response(self, response: str) -> str:
        return response[:self.config['max_length']].strip() + ("..." if len(response) > self.config['max_length'] else "")

    def _get_simple_response(self, command: str) -> Optional[str]:
        response = self.SIMPLE_RESPONSES.get(command)
        return response() if callable(response) else response

    def __repr__(self):
        return f"<LocalModel(model={self.DEFAULT_MODEL_NAME}, device={self.config['device'].upper()})>"