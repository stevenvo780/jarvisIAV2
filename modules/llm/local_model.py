import os
import requests
import logging
import time
from typing import Optional, Dict, Any, Callable
from tqdm.auto import tqdm
from llama_cpp import Llama
from pathlib import Path

class LocalModel:
    DEFAULT_MODEL_FILENAME = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    DEFAULT_MODEL_URL = f"https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/{DEFAULT_MODEL_FILENAME}"
    
    SIMPLE_RESPONSES = {
        "hola": "¡Hola! ¿En qué puedo ayudarte hoy?",
        "hora": lambda: f"Son las {time.strftime('%H:%M:%S')}",
        "fecha": lambda: f"Hoy es {time.strftime('%A, %d de %B de %Y')}",
        "ayuda": "Puedes preguntarme sobre:\n- La hora actual\n- La fecha\n- Temas generales\n¡Intenta hacerme una pregunta!",
        "creditos": "Soy un modelo local LLama-2-7B corriendo en tu dispositivo. Desarrollado por Meta y cuantizado por TheBloke."
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
        if not isinstance(self.config, dict):
            raise ValueError("Configuración debe ser un diccionario")
        
        required_keys = ['timeout', 'max_length', 'download_retries', 'model_dir', 'n_threads']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Falta clave de configuración: '{key}'")
            
        if not isinstance(self.config['timeout'], (int, float)) or self.config['timeout'] <= 0:
            raise ValueError("'timeout' debe ser un número positivo")
        
        if not isinstance(self.config['max_length'], int) or self.config['max_length'] <= 0:
            raise ValueError("'max_length' debe ser un entero positivo")
        
        if not isinstance(self.config['download_retries'], int) or self.config['download_retries'] < 0:
            raise ValueError("'download_retries' debe ser un entero no negativo")
        
        if not isinstance(self.config['model_dir'], str):
            raise ValueError("'model_dir' debe ser una cadena")
        
        if not isinstance(self.config['n_threads'], int) or self.config['n_threads'] <= 0:
            raise ValueError("'n_threads' debe ser un entero positivo")

    def _setup_model_path(self) -> str:
        model_dir = Path(self.config['model_dir'])
        model_dir.mkdir(parents=True, exist_ok=True)
        return str(model_dir / self.DEFAULT_MODEL_FILENAME)

    def _download_model_if_needed(self):
        if not os.path.exists(self.model_path):
            logging.warning(f"Modelo no encontrado en {self.model_path}, iniciando descarga...")
            self._download_model()

    def _download_model(self):
        for attempt in range(1, self.config['download_retries'] + 1):
            try:
                self._download_attempt(attempt)
                return
            except Exception as e:
                logging.error(f"Intento de descarga {attempt} fallido: {str(e)}")
                if attempt == self.config['download_retries']:
                    raise RuntimeError(
                        f"Fallo al descargar modelo tras {attempt} intentos. "
                        f"URL: {self.DEFAULT_MODEL_URL}. Error: {str(e)}"
                    )

    def _download_attempt(self, attempt: int):
        headers = {}
        if hf_token := os.getenv('HUGGINGFACE_TOKEN'):
            headers['Authorization'] = f'Bearer {hf_token}'

        with requests.get(
            self.DEFAULT_MODEL_URL,
            headers=headers,
            stream=True,
            timeout=self.config['timeout']
        ) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            progress_bar = tqdm(
                total=total_size, 
                unit='iB', 
                unit_scale=True, 
                desc="Descargando modelo",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            )
            
            with open(self.model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
            
            progress_bar.close()

    def _initialize_model(self) -> Llama:
        try:
            return Llama(
                model_path=self.model_path,
                n_ctx=1024,  # Contexto más pequeño
                n_batch=128,  # Batch size más pequeño
                n_threads=min(4, os.cpu_count() or 2),  # Limitar threads
                verbose=False
            )
        except Exception as e:
            logging.error(f"Error crítico al inicializar modelo: {str(e)}")
            raise RuntimeError("No se pudo cargar el modelo local. Verifica: "
                             "1. Permisos de archivo\n"
                             "2. Espacio en disco\n"
                             "3. Integridad del modelo descargado")

    def get_response(self, query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            return "Consulta inválida."
        
        query_lower = query.lower().strip()
        simple_response = self.get_simple_response(query_lower)
        if simple_response != "Comando no reconocido":
            return simple_response

        prompt = self._build_prompt(query)
        start_time = time.time()
        
        try:
            response = self.model.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,  # Reducir tokens máximos
                temperature=0.7,
                top_p=0.9,
                stop=["</s>", "[INST]"]
            )
            
            processing_time = time.time() - start_time
            logging.info(f"Tiempo de procesamiento: {processing_time:.2f}s")
            return self._validate_response(response['choices'][0]['message']['content'])
        
        except Exception as e:
            logging.error(f"Error en generación: {str(e)}")
            return f"Error procesando consulta: {str(e)}"

    def _build_prompt(self, query: str) -> str:
        return f"""<s>[INST] <<SYS>>
Responde de manera concisa y precisa en español. Si no sabes la respuesta, dilo claramente.
Evita formato markdown y mantén la respuesta en un párrafo.
<</SYS>>

{query} [/INST]"""

    def _validate_response(self, response: str) -> str:
        response = response.strip()
        
        if not response:
            return "No pude generar una respuesta para esa consulta."
        
        if len(response) > self.config['max_length']:
            last_space = response[:self.config['max_length']].rfind(' ')
            return response[:last_space].strip() + "... [truncada]" if last_space != -1 else response[:self.config['max_length']] + "..."
        
        return response

    def get_simple_response(self, command: str) -> str:
        response = self.SIMPLE_RESPONSES.get(command, "Comando no reconocido")
        return response() if callable(response) else response

    def __repr__(self):
        return f"<LocalModel(path='{self.model_path}', threads={self.config['n_threads']})>"