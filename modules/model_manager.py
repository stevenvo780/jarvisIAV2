import logging
import concurrent.futures
from modules.local_model import LocalModel
from modules.google_model import GoogleModel
from modules.openai_model import OpenAIModel

class ModelManager:
    def __init__(self, priority=None, timeout_in_seconds=5):
        self.priority = priority or ["local", "google", "openai"]
        self.timeout = timeout_in_seconds

        logging.basicConfig(filename="logs/jarvis.log",
                          level=logging.INFO,
                          format="%(asctime)s %(levelname)s %(message)s")

        self.local_model = LocalModel()
        self.google_model = GoogleModel()
        self.openai_model = OpenAIModel()

    def get_response(self, query):
        # Intentar con el modelo local, si falla pasar a Google, etc.
        for model in self.priority:
            try:
                if model == "local":
                    return self.local_model.get_response(query)
                elif model == "google":
                    return self.google_model.get_response(query)
                elif model == "openai":
                    return self.openai_model.get_response(query)
            except Exception as e:
                logging.error(f"Error with {model} model: {e}")
        return "No response available"