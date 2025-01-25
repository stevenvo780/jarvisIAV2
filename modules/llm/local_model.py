import os
import requests
import logging
import time
from typing import Optional, Dict, Any
from tqdm.auto import tqdm
from llama_cpp import Llama
from pathlib import Path

class LocalModel:
    DEFAULT_MODEL_FILENAME = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    DEFAULT_MODEL_URL = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    
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
            'download_retries': 3,
            'model_dir': os.path.join(Path.home(), ".local/share/jarvis/models"),
            'n_threads': os.cpu_count()
        }
        self._validate_config()
        self.model_path = self._setup_model_path()
        self._download_model_if_needed()
        self.model = self._initialize_model()
        logging.info("LocalModel inicializado")

    def _validate_config(self):
        """Valida la configuración del modelo."""
        if not isinstance(self.config, dict):
            raise ValueError("La configuración debe ser un diccionario")

        required_keys = ['timeout', 'max_length', 'download_retries', 'model_dir', 'n_threads']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Falta la clave de configuración requerida: {key}")

        if not isinstance(self.config['timeout'], (int, float)) or self.config['timeout'] <= 0:
            raise ValueError("'timeout' debe ser un número positivo")

        if not isinstance(self.config['max_length'], int) or self.config['max_length'] <= 0:
            raise ValueError("'max_length' debe ser un entero positivo")

        if not isinstance(self.config['download_retries'], int) or self.config['download_retries'] < 0:
            raise ValueError("'download_retries' debe ser un entero no negativo")

        if not isinstance(self.config['model_dir'], str):
            raise ValueError("'model_dir' debe ser una cadena de texto")

        if not isinstance(self.config['n_threads'], int) or self.config['n_threads'] <= 0:
            raise ValueError("'n_threads' debe ser un entero positivo")

    def _setup_model_path(self) -> str:
        """Define la ruta local donde se guardará/leerá el modelo."""
        model_path = os.path.join(self.config['model_dir'], self.DEFAULT_MODEL_FILENAME)
        return model_path

    def _download_model_if_needed(self):
        """Descarga el modelo si no existe en la ruta especificada."""
        if os.path.exists(self.model_path):
            logging.info("Modelo disponible localmente. No se requiere descarga.")
            return
        logging.info("Descargando modelo TinyLlama-1.1B-Chat...")
        try:
            import requests
            with requests.get(self.DEFAULT_MODEL_URL, stream=True) as r:
                r.raise_for_status()
                with open(self.model_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logging.info("Descarga completada con éxito")
        except Exception as e:
            logging.error(f"Error descargando modelo: {e}")
            raise RuntimeError("No se pudo descargar el modelo")

    def _initialize_model(self) -> Llama:
        try:
            gpu_params = {
                "n_gpu_layers": -1,
                "n_threads": min(4, os.cpu_count() or 1),
                "n_batch": 512,
                "n_ctx": 2048,
                "verbose": False
            }
            
            try:
                import torch
                if torch.cuda.is_available():
                    logging.info(f"CUDA disponible: {torch.cuda.get_device_name(0)}")
                    # Parámetros optimizados para modelo pequeño
                    gpu_params.update({
                        "n_gqa": 4,  # Reducido para modelo más pequeño
                        "rms_norm_eps": 1e-5,
                        "mul_mat_q": True,
                    })
                else:
                    logging.warning("CUDA no disponible, usando CPU")
                    gpu_params["n_gpu_layers"] = 0
            except ImportError:
                logging.warning("PyTorch no instalado, usando CPU")
                gpu_params["n_gpu_layers"] = 0

            return Llama(
                model_path=self.model_path,
                seed=42,
                use_mmap=True,
                use_mlock=False,
                embedding=True,
                **gpu_params
            )
        except Exception as e:
            logging.error(f"Error crítico al inicializar modelo: {str(e)}")
            raise RuntimeError(f"No se pudo cargar el modelo local: {str(e)}")

    def get_response(self, query: str) -> str:
        query = query.lower().strip()
        
        if response := self._get_simple_response(query):
            return response
        
        try:
            prompt = self._build_prompt(query)
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.config['device'])
            
            outputs = self.model.generate(
                inputs.input_ids,
                max_new_tokens=256,
                temperature=self.config['temperature'],
                do_sample=True
            )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return self._process_response(response.split("[/INST]")[-1].strip())
            
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