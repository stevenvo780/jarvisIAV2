import logging
import warnings
from typing import Optional, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

warnings.filterwarnings('ignore', message='Input type into Linear4bit.*')

class LocalModel:
    # DEFAULT_MODEL_NAME = "meta-llama/Llama-2-7b-hf"
    # DEFAULT_MODEL_NAME = "meta-llama/Llama-3.2-1B"
    # DEFAULT_MODEL_NAME = "meta-llama/Llama-3.2-2B"
    DEFAULT_MODEL_NAME = "meta-llama/Llama-3.2-3B"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model_name = self.config.get("model_name", self.DEFAULT_MODEL_NAME)
        
        logging.info(f"Loading model: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            padding_side="left",
            add_eos_token=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config={"load_in_4bit": True},
            device_map="auto",
            torch_dtype=torch.float16
        )
        self.model.eval()
        self.model.config.pad_token_id = self.tokenizer.pad_token_id

    def get_response(self, query: str) -> str:
        try:
            # Tokenización con attention mask
            encoded = self.tokenizer(
                query,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
                add_special_tokens=True
            )
            
            # Mover todo a CUDA
            input_ids = encoded["input_ids"].to(self.model.device)
            attention_mask = encoded["attention_mask"].to(self.model.device)

            with torch.inference_mode():
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=150,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95,
                    repetition_penalty=1.2,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True
                )

            # Decodificar solo la respuesta nueva
            response = self.tokenizer.decode(
                outputs[0][input_ids.shape[1]:],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            ).strip()

            return response if response else "Lo siento, no pude generar una respuesta."

        except Exception as e:
            logging.error(f"Error en generación: {e}")
            return "Lo siento, hubo un error al procesar tu solicitud."

    def __repr__(self):
        return f"<LocalModel: {self.model_name}>"
