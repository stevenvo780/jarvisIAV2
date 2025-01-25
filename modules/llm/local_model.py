import os
import logging
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
    BitsAndBytesConfig
)
from typing import Optional, Dict, Any

class LocalModel:
    DEFAULT_MODEL_NAME = "cerebras/btlm-3b-8k-base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            'max_new_tokens': 1024,
            'temperature': 0.7,
            'top_p': 0.95,
            'repetition_penalty': 1.1,
            'device_map': "auto",  # Usar mapeo automático
            'quantization': '4bit',
            'trust_remote_code': True,
            'max_memory': {0: "3GB", "cpu": "12GB"}  # Asignación flexible
        }
        self._validate_config()
        self.model, self.tokenizer = self._initialize_model()
        logging.info(f"Modelo {self.DEFAULT_MODEL_NAME} cargado | VRAM: ~3GB")

    def _validate_config(self):
        required_keys = ['quantization', 'trust_remote_code', 'device_map']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Clave requerida faltante: {key}")
        if self.config['quantization'] != '4bit':
            raise ValueError("Se requiere cuantización 4-bit para 4GB VRAM")

    def _initialize_model(self):
        try:
            # Configuración de cuantización optimizada
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True
            )

            # Cargar tokenizer con padding izquierdo
            tokenizer = AutoTokenizer.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                padding_side="left",
                truncation_side="left",
                use_fast=True
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # Cargar modelo con device_map automático
            model = AutoModelForCausalLM.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                quantization_config=quantization_config,
                device_map=self.config['device_map'],
                max_memory=self.config['max_memory'],
                torch_dtype=torch.float16,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )

            # Configurar pipeline con optimizaciones
            self.pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=self.config['max_new_tokens'],
                do_sample=True,
                temperature=self.config['temperature'],
                top_p=self.config['top_p'],
                repetition_penalty=self.config['repetition_penalty'],
                pad_token_id=tokenizer.pad_token_id,
                return_full_text=False,
                model_kwargs={
                    "use_cache": True,
                    "pad_to_multiple_of": 64
                }
            )

            return model, tokenizer

        except Exception as e:
            logging.error(f"Error de carga: {str(e)}")
            raise RuntimeError(f"Fallo en la inicialización: {str(e)}")

    def get_response(self, query: str) -> str:
        try:
            prompt = f"Usuario: {query}\nAsistente:"
            
            outputs = self.pipeline(
                prompt,
                max_new_tokens=self.config['max_new_tokens'],
                temperature=self.config['temperature'],
                top_p=self.config['top_p']
            )
            
            return self._clean_response(outputs[0]['generated_text'])
        
        except Exception as e:
            logging.error(f"Error en generación: {str(e)}")
            return "Error procesando tu consulta"

    def _clean_response(self, response: str) -> str:
        return response.split("Asistente:")[-1].strip().replace("  ", " ")

    def __repr__(self):
        return f"<LocalModel: {self.DEFAULT_MODEL_NAME} | 4-bit | VRAM: ~3GB>"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        chatbot = LocalModel()
        print("Chatbot inicializado (escribe 'salir' para terminar)\n")
        while True:
            user_input = input("Usuario: ")
            if user_input.lower() in ["salir", "exit"]:
                break
            response = chatbot.get_response(user_input)
            print(f"\nAsistente: {response}\n")
            
    except Exception as e:
        logging.error(f"Error inicial: {str(e)}")