import logging
import warnings
from typing import Optional, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer

warnings.filterwarnings('ignore', message='Input type into Linear4bit.*')

class LocalModel:
    DEFAULT_MODEL_NAME = "meta-llama/Llama-2-7b-hf"
    # DEFAULT_MODEL_NAME = "meta-llama/Llama-3.2-1B"
    # DEFAULT_MODEL_NAME = "meta-llama/Llama-3.2-2B"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model_name = self.config.get("model_name", self.DEFAULT_MODEL_NAME)
        self.max_length = self.config.get("max_length", 128)
        self.max_new_tokens = self.config.get("max_new_tokens", 50)

        logging.info(f"Loading quantized model: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config={"load_in_4bit": True},
            device_map="auto",
        )
        logging.info("Quantized model loaded successfully!")

    def get_response(self, query: str) -> str:
        try:
            inputs = self.tokenizer(
                query,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length,
                padding=False
            )

            gen_out = self.model.generate(
                inputs["input_ids"].to("cuda"),
                max_new_tokens=self.max_new_tokens,
                use_cache=True,
            )

            return self.tokenizer.decode(
                gen_out[0], skip_special_tokens=True
            )
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "Error processing request"


    def __repr__(self):
        return f"<LocalModelSmall: {self.model_name}>"

    def __repr__(self):
        return f"<LocalModelSmall: {self.model_name}>"
