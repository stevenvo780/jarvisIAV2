import time
import os

class OpenAIModel:
    def __init__(self, openai_api_key=None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("No se encontró OPENAI_API_KEY en las variables de entorno")

    def get_response(self, query: str) -> str:
        time.sleep(0.5)  # simulate latency
        return f"[OpenAI Model Response]: Stub for '{query}'."
