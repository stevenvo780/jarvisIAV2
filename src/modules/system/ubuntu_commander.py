import subprocess
import logging
import webbrowser
from typing import Dict, Tuple
from .base_commander import BaseCommander

logger = logging.getLogger(__name__)

class UbuntuCommander(BaseCommander):
    def __init__(self):
        self.command_prefix = "SYSTEM"
        super().__init__()

    def initialize_commands(self):
        self.commands = {
            'CALCULATOR': {
                'description': 'Abre la calculadora',
                'examples': ['abrir calculadora', 'necesito calcular algo'],
                'triggers': ['calculadora', 'calcular'],
                'handler': self._open_calculator
            },
            'BROWSER': {
                'description': 'Abre el navegador web',
                'examples': ['abrir navegador', 'necesito buscar algo'],
                'triggers': ['navegador', 'internet', 'web'],
                'handler': self._open_browser
            },
            'MUSIC': {
                'description': 'Reproduce música',
                'examples': ['reproducir música', 'poner música'],
                'triggers': ['música', 'canciones', 'reproductor'],
                'handler': self._play_music
            },
            'TERMINAL': {
                'description': 'Abre una terminal',
                'examples': ['abrir terminal', 'abrir consola'],
                'triggers': ['terminal', 'consola', 'shell'],
                'handler': self._open_terminal
            },
            'SETTINGS': {
                'description': 'Abre la configuración del sistema',
                'examples': ['abrir configuración', 'ajustes del sistema'],
                'triggers': ['configuración', 'ajustes', 'opciones'],
                'handler': self._open_settings
            }
        }

    def get_rules_text(self) -> str:
        return """
        - Para el módulo SYSTEM (UbuntuCommander), si la entrada menciona abrir/ejecutar/iniciar aplicaciones:
          Retornar SYSTEM_nombredelcomando
        """

    def _open_calculator(self, **kwargs) -> Tuple[str, bool]:
        try:
            subprocess.Popen(['gnome-calculator'])
            return "Calculadora abierta", True
        except Exception as e:
            logger.error(f"Error abriendo calculadora: {e}")
            return f"Error abriendo calculadora: {str(e)}", False

    def _open_browser(self, **kwargs) -> Tuple[str, bool]:
        try:
            url = kwargs.get('url', "https://www.google.com")
            webbrowser.open(url)
            return "Navegador abierto", True
        except Exception as e:
            logger.error(f"Error abriendo navegador: {e}")
            return f"Error abriendo navegador: {str(e)}", False

    def _play_music(self, **kwargs) -> Tuple[str, bool]:
        try:
            subprocess.Popen(['rhythmbox'])
            return "Reproductor de música abierto", True
        except Exception as e:
            logger.error(f"Error abriendo reproductor: {e}")
            return f"Error abriendo reproductor: {str(e)}", False

    def _open_terminal(self, **kwargs) -> Tuple[str, bool]:
        try:
            subprocess.Popen(['gnome-terminal'])
            return "Terminal abierta", True
        except Exception as e:
            logger.error(f"Error abriendo terminal: {e}")
            return f"Error abriendo terminal: {str(e)}", False

    def _open_settings(self, **kwargs) -> Tuple[str, bool]:
        try:
            subprocess.Popen(['gnome-control-center'])
            return "Configuración del sistema abierta", True
        except Exception as e:
            logger.error(f"Error abriendo configuración: {e}")
            return f"Error abriendo configuración: {str(e)}", False

    def process_command_parameters(self, command: str, user_input: str, additional_info: str) -> dict:
        return {}

    def should_handle_command(self, user_input: str) -> bool:
        input_lower = user_input.lower()
        action_words = ['abrir', 'ejecutar', 'iniciar', 'mostrar', 'abre', 'nueva', 'quiero']
        has_action = any(word in input_lower for word in action_words)
        
        has_trigger = False
        for cmd_info in self.commands.values():
            if any(trigger in input_lower for trigger in cmd_info['triggers']):
                has_trigger = True
                break
        
        return has_action and has_trigger

    def extract_command_info(self, user_input: str) -> tuple:
        input_lower = user_input.lower()
        input_words = input_lower.split()
        
        for cmd_name, cmd_info in self.commands.items():
            for trigger in cmd_info['triggers']:
                if trigger in input_words:
                    return cmd_name, None
        
        for cmd_name, cmd_info in self.commands.items():
            for trigger in cmd_info['triggers']:
                if trigger in input_lower:
                    return cmd_name, None
        
        return None, None

    def format_command_response(self, command: str, additional_info: str) -> str:
        return f"{self.command_prefix}_{command.upper()}" + (f":{additional_info}" if additional_info else "")