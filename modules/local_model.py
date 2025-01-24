import os
import requests
import logging
from typing import Optional
from tqdm import tqdm
from llama_cpp import Llama

class LocalModel:
    MODEL_URL = "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.path.join(
            os.path.expanduser("~"),
            ".local/share/jarvis/models/llama-2-7b-chat.Q4_K_M.gguf"
        )
        
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        if not os.path.exists(self.model_path):
            print("\nModelo no encontrado. Iniciando descarga automática...")
            self._download_model()
            
        self.model = Llama(
            model_path=self.model_path,
            n_ctx=2048,
            n_batch=8
        )

    def _download_model(self):
        """Descarga el modelo desde HuggingFace"""
        headers = {}
        hf_token = os.getenv('HUGGINGFACE_TOKEN')
        if hf_token:
            headers['Authorization'] = f'Bearer {hf_token}'

        try:
            response = requests.get(
                self.MODEL_URL,
                headers=headers,
                stream=True
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024  # 1 Kibibyte
            
            print(f"\nDescargando modelo ({total_size/1024/1024:.1f} MB)...")
            
            with open(self.model_path, 'wb') as f, \
                 tqdm(total=total_size, unit='iB', unit_scale=True) as pbar:
                for data in response.iter_content(block_size):
                    size = f.write(data)
                    pbar.update(size)
                    
            print("\n¡Descarga completada!")
            
        except Exception as e:
            logging.error(f"Error descargando modelo: {e}")
            if os.path.exists(self.model_path):
                os.remove(self.model_path)
            raise RuntimeError(f"No se pudo descargar el modelo: {e}")

    def get_response(self, query: str) -> str:
        try:
            prompt = f"### Humano: {query}\n### Asistente:"
            response = self.model(
                prompt,
                max_tokens=128,
                temperature=0.7,
                top_p=0.9,
                stop=["### Humano:", "\n\n"],
                echo=False
            )
            
            return response['choices'][0]['text'].strip()
            
        except Exception as e:
            return f"Error con modelo local: {str(e)}"
