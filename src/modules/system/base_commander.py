from typing import Dict, Tuple, List, Callable
import logging

logger = logging.getLogger(__name__)

class BaseCommander:
    def __init__(self):
        self.command_prefix = ""
        self.commands = {}
        self.initialize_commands()

    def initialize_commands(self):
        raise NotImplementedError

    def register_command(self, name: str, description: str, examples: List[str], triggers: List[str], handler: Callable):
        self.commands[name] = {
            'description': description,
            'examples': examples,
            'triggers': triggers,
            'handler': handler
        }

    def get_command_descriptions(self) -> List[Dict]:
        descriptions = []
        for cmd_name, cmd_info in self.commands.items():
            descriptions.append({
                'prefix': self.command_prefix,
                'command': cmd_name,
                'description': cmd_info.get('description', ''),
                'examples': cmd_info.get('examples', []),
                'triggers': cmd_info.get('triggers', [])
            })
        return descriptions

    def get_rules_text(self) -> str:
        return ""

    def execute_command(self, command: str, **kwargs) -> Tuple[str, bool]:
        if command not in self.commands:
            return f"Comando {command} no encontrado", False
            
        try:
            handler = self.commands[command]['handler']
            return handler(**kwargs)
        except Exception as e:
            logger.error(f"Error executing {command}: {e}")
            return f"Error ejecutando {command}: {str(e)}", False

    def process_command_parameters(self, command: str, user_input: str, additional_info: str) -> dict:
        """Procesa los parámetros específicos para cada comando"""
        return {}

    def should_handle_command(self, user_input: str) -> bool:
        """Determina si este commander debe manejar el comando"""
        return False

    def extract_command_info(self, user_input: str) -> tuple:
        """Extrae información específica del comando (ej: títulos, fechas, etc)"""
        return None, None

    def format_command_response(self, command: str, additional_info: str = "") -> str:
        """Formatea el comando para la respuesta del AI"""
        return f"{self.command_prefix}_{command}"
