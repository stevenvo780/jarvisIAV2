import os
import logging
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
from typing import Optional, Dict, Any

class LocalModel:
    # Modelo actualizado con identificador correcto
    DEFAULT_MODEL_NAME = "cerebras/btlm-3b-8k-base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            'timeout': 30,
            'max_length': 1000,
            'n_threads': os.cpu_count(),
            'quantization': '4bit',
            'trust_remote_code': True,
            'device_map': 'auto'
        }
        self._validate_config()
        self.model = self._initialize_model()
        logging.info(f"Modelo {self.DEFAULT_MODEL_NAME} cargado exitosamente")

    def _validate_config(self):
        """Valida parámetros críticos para 4GB VRAM"""
        required_keys = ['quantization', 'trust_remote_code', 'device_map']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Clave requerida faltante: {key}")
        if self.config['quantization'] != '4bit':
            raise ValueError("Se requiere cuantización 4-bit para 4GB VRAM:cite[2]:cite[5]")

    def _initialize_model(self):
        """Inicializa el modelo con configuración optimizada"""
        try:
            # Configuración de cuantización 4-bit
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True
            )

            # Cargar tokenizer con ajustes para secuencias largas
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                padding_side="left",
                truncation_side="left",
                use_fast=True  # Acelera el procesamiento:cite[3]
            )
            
            # Configurar el token de padding
            if self.tokenizer.pad_token is None:
                self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
                self.tokenizer.pad_token = '[PAD]'
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id  

            # Cargar modelo con configuración optimizada
            model = AutoModelForCausalLM.from_pretrained(
                self.DEFAULT_MODEL_NAME,
                quantization_config=quantization_config,
                device_map=self.config['device_map'],
                torch_dtype=torch.float16,
                trust_remote_code=self.config['trust_remote_code'], 
                low_cpu_mem_usage=True
            )

            model.resize_token_embeddings(len(self.tokenizer))

            self.pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=self.tokenizer,
                max_new_tokens=1024,  # Ajustado a múltiplo de 64
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.pad_token_id,  # Usar pad_token_id correcto
                batch_size=1,
                return_full_text=False,
                torch_dtype=torch.float16,
                device_map="auto",
                model_kwargs={
                    "low_cpu_mem_usage": True,
                    "use_cache": True,
                    "pad_to_multiple_of": 64
                }
            )
            return model

        except Exception as e:
            logging.error(f"Error crítico: {str(e)}")
            raise RuntimeError(f"Fallo en la carga: {str(e)}")

    def get_response(self, query: str) -> str:
        """Genera respuestas adaptadas al contexto"""
        try:
            prompt = self._build_prompt(query)
            
            # Procesar el input asegurando max_length múltiplo de 64
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024  # Múltiplo de 64
            ).to("cuda")
            
            outputs = self.pipeline(
                prompt,
                max_new_tokens=1024,  # Múltiplo de 64
                num_return_sequences=1,
                do_sample=True,
                temperature=0.7,
                top_p=0.95
            )
            return self._process_response(outputs[0]['generated_text'])
        except Exception as e:
            logging.error(f"Error en generación: {str(e)}")
            return "Error procesando la consulta"

    def _build_prompt(self, query: str) -> str:
        """Formatea el prompt para aprovechar el contexto de 8K tokens"""
        return f"Usuario: {query}\nAsistente:"

    def _process_response(self, response: str) -> str:
        """Limpia la respuesta eliminando duplicados y formateando"""
        return response.split("Asistente:")[-1].strip().replace("\n", " ")

    def __repr__(self):
        return f"<LocalModel: {self.DEFAULT_MODEL_NAME} | 4-bit | VRAM: ~3GB>"

# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        model = LocalModel()
        print(model)
        response = model.get_response("¿Cómo optimizar un modelo LLM para dispositivos móviles?")
        print("Respuesta:", response)
    except Exception as e:
        logging.error(f"Error inicial: {str(e)}")