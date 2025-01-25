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
        # Config por defecto, ajusta según tus necesidades (4GB VRAM, etc.)
        self.config = config or {
            'timeout': 30,
            'max_length': 1000,
            'n_threads': os.cpu_count(),
            'quantization': 'none',  # '4bit' si deseas un modelo cuantizado
        }
        self._validate_config()
        self.model = self._initialize_model()
        logging.info("LocalModel inicializado correctamente")

    def _validate_config(self):
        """Valida la configuración del modelo."""
        if not isinstance(self.config, dict):
            raise ValueError("La configuración debe ser un diccionario")
    
        required_keys = ['timeout', 'max_length', 'n_threads', 'quantization']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Falta la clave de configuración requerida: {key}")
    
        if not isinstance(self.config['timeout'], (int, float)) or self.config['timeout'] <= 0:
            raise ValueError("'timeout' debe ser un número positivo")
    
        if not isinstance(self.config['max_length'], int) or self.config['max_length'] <= 0:
            raise ValueError("'max_length' debe ser un entero positivo")
    
        if not isinstance(self.config['n_threads'], int) or self.config['n_threads'] <= 0:
            raise ValueError("'n_threads' debe ser un entero positivo")
        
        if self.config['quantization'] not in ['none', '4bit']:
            raise ValueError("'quantization' debe ser 'none' o '4bit'")

    def _initialize_model(self):
        """Inicializa el modelo y el tokenizer con (opcional) accelerate."""
        try:
            if torch.cuda.is_available():
                logging.info(f"CUDA disponible: {torch.cuda.get_device_name(0)}")
            else:
                logging.warning("CUDA no disponible, usando CPU")

            # Cargar tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                padding_side="left",
                truncation_side="left"
            )

            # Cargar modelo
            # Nota: 'device_map="auto"' usa accelerate para asignar el modelo de forma eficiente
            #       'low_cpu_mem_usage=True' reduce la RAM al cargar
            #       'load_in_8bit' o 'load_in_4bit' según la cuantización deseada.
            model = AutoModelForCausalLM.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                device_map="auto",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                low_cpu_mem_usage=True,
                load_in_8bit=True if self.config['quantization'] == '4bit' else False
            )

            # Aquí NO pasamos 'device=...' para evitar conflictos con accelerate
            self.pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=self.tokenizer,
                truncation=True,
                max_new_tokens=128,  # Reducido para respuestas más concisas
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                num_beams=1,
                early_stopping=False,
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.eos_token_id
            )

            return model

        except Exception as e:
            logging.error(f"Error crítico al inicializar el modelo local: {str(e)}")
            raise RuntimeError(f"No se pudo cargar el modelo local: {str(e)}")

    def get_response(self, query: str) -> str:
        """Genera una respuesta usando el modelo local."""
        try:
            prompt = self._build_prompt(query)
            logging.debug(f"Generando respuesta con el prompt:\n{prompt}")
            
            outputs = self.pipeline(
                prompt,
                max_new_tokens=512,  # Aumentado para permitir respuestas más largas
                num_return_sequences=1,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                repetition_penalty=1.1,
                no_repeat_ngram_size=3,
            )
            
            response = outputs[0]['generated_text']
            return self._process_response(response)

        except Exception as e:
            logging.error(f"Error generando respuesta local: {str(e)}")
            return "Lo siento, ha ocurrido un error procesando tu consulta."

    def _build_prompt(self, query: str) -> str:
        """Formatea el prompt para guiar adecuadamente el modelo local."""
        system_context = (
            "Eres Jarvis, un asistente virtual que proporciona respuestas precisas y relevantes.\n"
            "Debes responder de manera natural, sin limitaciones artificiales de longitud.\n"
            "Si la pregunta requiere una respuesta extensa, proporciónala.\n"
            "Si requiere una respuesta corta, sé conciso.\n"
        )
        user_prompt = f"Usuario: {query}\nJarvis:"
        return f"{system_context}{user_prompt}"

    def _process_response(self, response: str) -> str:
        """Limpia y procesa la respuesta generada por el modelo."""
        try:
            if "Jarvis:" in response:
                parts = response.split("Jarvis:", 1)
                response = parts[1].strip() if len(parts) > 1 else parts[0]

            return response.strip()

        except Exception as e:
            logging.error(f"Error procesando la respuesta local: {e}")
            return "Lo siento, ha ocurrido un error procesando tu consulta."

    def __repr__(self):
        device = "CUDA" if torch.cuda.is_available() else "CPU"
        quant = self.config.get('quantization', 'none')
        return f"<LocalModel(model={self.DEFAULT_MODEL_NAME}, device={device}, quantization={quant})>"
