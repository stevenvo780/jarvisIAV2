import os
import logging
import wolframalpha
from typing import Tuple
from .base_commander import BaseCommander

logger = logging.getLogger(__name__)

class MathCommander(BaseCommander):
    def __init__(self):
        self.app_id = os.getenv("WOLFRAM_APP_ID")
        if not self.app_id:
            raise ValueError("WOLFRAM_APP_ID no está configurado")
        super().__init__()
        self.command_prefix = "MATH"

    def initialize_commands(self):
        # Usando register_command para simplificar el registro del comando SOLVE
        self.register_command(
            'SOLVE',
            'Resuelve expresiones matemáticas usando WolframAlpha',
            ['calcular 2+2', 'resolver integral de x^2', 'wolfram 5*7'],
            ['calcular', 'resolver', 'wolfram'],
            self.solve_math
        )

    def solve_math(self, text: str, **kwargs) -> Tuple[str, bool]:
        try:
            # Extraer la consulta removiendo palabras clave
            query = text.replace("calcular", "").replace("resolver", "").replace("wolfram", "").strip()
            client = wolframalpha.Client(self.app_id)
            res = client.query(query)
            answer = next(res.results).text if res.results else "No se encontró respuesta"
            return answer, True
        except Exception as e:
            logger.error(f"Error en solve_math: {e}")
            return str(e), False

    def process_command_parameters(self, command: str, user_input: str, additional_info: str) -> dict:
        return {"text": user_input}

    def should_handle_command(self, user_input: str) -> bool:
        return any(word in user_input.lower() for word in ['calcular', 'resolver', 'wolfram'])

    def extract_command_info(self, user_input: str) -> tuple:
        query = user_input.replace("calcular", "").replace("resolver", "").replace("wolfram", "").strip()
        return 'SOLVE', query

    def format_command_response(self, command: str, additional_info: str = "") -> str:
        return f"{self.command_prefix}_{command}:{additional_info}"
