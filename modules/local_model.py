class LocalModel:
    def __init__(self, model_path=None):
        self.model_path = model_path or "path/to/local/model"

    def generate_response(self, query: str) -> str:
        return f"[Local Model Response]: This is a stub for '{query}'."
