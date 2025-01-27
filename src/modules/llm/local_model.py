import logging
import warnings
from typing import Optional, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

warnings.filterwarnings('ignore', message='Input type into Linear4bit.*')

class LocalModel:
    DEFAULT_MODEL_NAME = "meta-llama/Llama-3.2-3B"
    SYSTEM_PROMPT = """Eres Jarvis, un asistente que responde siempre en español, de forma concisa y amable. 
No incluyas roles ni menciones innecesarias. Contesta únicamente con el mensaje final."""

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
            prompt = f"{self.SYSTEM_PROMPT}\n\nPregunta: {query}\nRespuesta:"
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
                    max_new_tokens=80,
                    num_return_sequences=1,
                    temperature=0.2,
                    do_sample=True,
                    top_k=20,
                    top_p=0.9,
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
            for sep in ["Pregunta:", "Respuesta:", "Usuario:", "Jarvis:"]:
                if sep in response:
                    response = response.split(sep)[0].strip()
            return response if response else "¿En qué puedo ayudarte?"
        except Exception as e:
            logging.error(f"Error: {e}")
            return "¿En qué puedo ayudarte?"

    def __repr__(self):
        return f"<LocalModel: {self.model_name}>"
