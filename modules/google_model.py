import os

class GoogleModel:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("No se encontró GOOGLE_API_KEY en las variables de entorno")

    def generate_response(self, query: str) -> str:
        return f"[Google Model Response]: Stub for '{query}'."
