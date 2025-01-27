import subprocess
import logging
from typing import Dict, Callable, Any
import webbrowser

logger = logging.getLogger(__name__)

class UbuntuCommander:
    def __init__(self):
        self.commands = {
            'abrir_calculadora': self._open_calculator,
            'abrir_navegador': self._open_browser,
            'reproducir_musica': self._play_music,
            'abrir_terminal': self._open_terminal,
            'abrir_configuracion': self._open_settings,
        }

    def execute_command(self, command_name: str, **kwargs) -> bool:
        command = self.commands.get(command_name)
        if command:
            try:
                return command(**kwargs)
            except Exception as e:
                logger.error(f"Error ejecutando comando {command_name}: {e}")
                return False
        return False

    def register_command(self, command_name: str, command_func: Callable) -> None:
        """Registra un nuevo comando dinámicamente"""
        self.commands[command_name] = command_func

    def _open_calculator(self) -> bool:
        try:
            subprocess.Popen(['gnome-calculator'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo calculadora: {e}")
            return False

    def _open_browser(self, url: str = "https://www.google.com") -> bool:
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Error abriendo navegador: {e}")
            return False

    def _play_music(self) -> bool:
        try:
            subprocess.Popen(['rhythmbox'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo reproductor de música: {e}")
            return False

    def _open_terminal(self) -> bool:
        try:
            subprocess.Popen(['gnome-terminal'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo terminal: {e}")
            return False

    def _open_settings(self) -> bool:
        try:
            subprocess.Popen(['gnome-control-center'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo configuración: {e}")
            return False
