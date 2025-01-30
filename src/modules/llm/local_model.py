import logging
import warnings
from typing import Optional, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

warnings.filterwarnings('ignore', message='Input type into Linear4bit.*')

class LocalModel:
    DEFAULT_MODEL_NAME = "meta-llama/Llama-3.2-3B"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model_name = self.config.get("model_name", self.DEFAULT_MODEL_NAME)
        logging.info(f"Cargando modelo: {self.model_name}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            padding_side="left",
            add_eos_token=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            llm_int8_enable_fp32_cpu_offload=True
        )
        
        device_map = "auto"
        if not torch.cuda.is_available():
            device_map = "cpu"
            logging.warning("GPU no disponible, usando CPU")
        
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map=device_map,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )
            self.model.eval()
            self.model.config.pad_token_id = self.tokenizer.pad_token_id
        except Exception as e:
            logging.error(f"Error al cargar modelo: {e}")
            raise RuntimeError(f"No se pudo inicializar el modelo: {e}")

    def get_response(self, query: str) -> str:
        try:
            prompt = query
            encoded = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
                add_special_tokens=True
            )
            input_ids = encoded["input_ids"].to(self.model.device)
            attention_mask = encoded["attention_mask"].to(self.model.device)
            with torch.inference_mode():
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=128,
                    num_return_sequences=1,
                    temperature=0.3,
                    do_sample=True,
                    top_k=20,
                    top_p=0.85,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True
                )
            
            response = self.tokenizer.decode(
                outputs[0][input_ids.shape[1]:],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            ).strip()

            response = response.split('\n')[0]
            
            prefixes_to_remove = ["Respuesta:", "Jarvis:", "Usuario:", "Asistente:"]
            for prefix in prefixes_to_remove:
                if response.startswith(prefix):
                    response = response.replace(prefix, "", 1).strip()
            
            if not response or len(response) < 2:
                return "¿En qué puedo ayudarte?"

            return response

        except Exception as e:
            logging.error(f"Error en el modelo local: {e}")
            return "Lo siento, hubo un error en el procesamiento. ¿Puedo ayudarte en algo más?"

    def __repr__(self):
        return f"<LocalModel: {self.model_name}>"
