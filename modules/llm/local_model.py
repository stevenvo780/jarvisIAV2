import os
import logging
import time
from typing import Optional, Dict, Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from pathlib import Path

class LocalModel:
    DEFAULT_MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    
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
        try:
            prompt = self._build_prompt(query)
            response = self.pipeline(
                prompt,
                max_new_tokens=256,
                num_return_sequences=1,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.2,  # Evitar repeticiones
                return_full_text=False
            )[0]['generated_text']
            
            return self._process_response(response)
            
        except Exception as e:
            logging.error(f"Error generando respuesta: {str(e)}")
            return "Error procesando tu solicitud"

    def _build_prompt(self, query: str) -> str:
        """Formatea el prompt para TinyLlama."""
        # Extraer solo la pregunta del usuario si existe
        if "Pregunta:" in query:
            query = query.split("Pregunta:", 1)[1].strip()
            
        # Construir prompt simplificado
        return f"[INST] Como Jarvis, responde de forma concisa y profesional a esta pregunta:\n{query} [/INST]"

    def _process_response(self, response: str) -> str:
        """Limpia y procesa la respuesta."""
        # Limpiar marcadores especiales
        response = response.replace("[INST]", "").replace("[/INST]", "")
        
        # Tomar solo la primera respuesta coherente
        response_parts = response.split("\n")
        clean_response = response_parts[0] if response_parts else response
        
        # Remover repeticiones y prompts
        for unwanted in ["Pregunta:", "Respuesta:", "Como Jarvis,", "responde de forma concisa"]:
            clean_response = clean_response.replace(unwanted, "")
        
        # Limpiar y truncar
        clean_response = clean_response.strip()
        return clean_response[:self.config['max_length']]

    def __repr__(self):
        return f"<LocalModel(model={self.DEFAULT_MODEL_NAME}, device={self.config['device'].upper()})>"