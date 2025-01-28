from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)

class BaseCommander:
    def __init__(self):
        self.command_prefix = ""
        self.commands = {}
        self.initialize_commands()

    def initialize_commands(self):
        raise NotImplementedError

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

    def execute_command(self, command: str, **kwargs) -> Tuple[str, bool]:
        if command not in self.commands:
            return f"Comando {command} no encontrado", False
            
        try:
            handler = self.commands[command]['handler']
            return handler(**kwargs)
        except Exception as e:
            logger.error(f"Error executing {command}: {e}")
            return f"Error ejecutando {command}: {str(e)}", False
