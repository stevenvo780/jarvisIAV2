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
                'triggers': ['terminal', 'consola'],
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
