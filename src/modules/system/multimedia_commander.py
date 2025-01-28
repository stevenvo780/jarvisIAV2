import logging
import subprocess
import webbrowser
from typing import Dict, Tuple
from .base_commander import BaseCommander

logger = logging.getLogger(__name__)

class MultimediaCommander(BaseCommander):
    def __init__(self, model_manager=None):
        super().__init__()  # Llamar a super() primero
        self.command_prefix = "MEDIA"
        self.model_manager = model_manager
        self.initialize_commands()  # Asegurarnos que los comandos se inicializan

    def initialize_commands(self):
        """Inicializa los comandos disponibles."""
        self.commands = {
            'VOLUME': {
                'description': 'Ajusta el volumen del sistema',
                'examples': ['subir volumen', 'bajar volumen'],
                'triggers': ['volumen', 'subir', 'bajar', 'sube', 'baja'],
                'handler': self._adjust_volume
            }
        }

    def get_rules_text(self) -> str:
        return """
        - Para el módulo MEDIA (MultimediaCommander):
          * Control de volumen -> MEDIA_VOLUME
          * Reproducir contenido -> MEDIA_PLAY:plataforma:búsqueda
        """

    def process_command_parameters(self, command: str, user_input: str, additional_info: str) -> dict:
        """Procesa los parámetros del comando."""
        logger.debug(f"Procesando parámetros: command={command}, input={user_input}")
        if command == 'VOLUME':
            lower_input = user_input.lower()
            if any(w in lower_input for w in ['subir', 'sube', 'más', 'aumenta']):
                return {'direction': 'up'}
            return {'direction': 'down'}
        return {}

    def should_handle_command(self, user_input: str) -> bool:
        """Verifica si debe manejar el comando."""
        lower_input = user_input.lower()
        volume_keywords = ['volumen', 'subir', 'bajar', 'sube', 'baja']
        result = any(k in lower_input for k in volume_keywords)
        logger.debug(f"Should handle '{user_input}': {result}")
        return result

    def extract_command_info(self, user_input: str) -> tuple:
        """Extrae la información del comando."""
        logger.debug(f"Extrayendo comando de: {user_input}")
        if self.should_handle_command(user_input):
            return 'VOLUME', None
        return None, None

    def _adjust_volume(self, direction: str = None, **kwargs) -> Tuple[str, bool]:
        """Ajusta el volumen del sistema."""
        try:
            logger.debug(f"Ajustando volumen: direction={direction}")
            if direction == 'up':
                subprocess.run(['amixer', 'set', 'Master', '10%+'])
                return "Volumen aumentado", True
            elif direction == 'down':
                subprocess.run(['amixer', 'set', 'Master', '10%-'])
                return "Volumen disminuido", True
            return "Dirección no especificada", False
        except Exception as e:
            logger.error(f"Error ajustando volumen: {e}")
            return str(e), False

    def _play_media(self, platform: str = None, query: str = None, **kwargs) -> Tuple[str, bool]:
        try:
            if platform == 'spotify':
                if query:
                    subprocess.run(['spotify', '--uri', f'spotify:search:{query}'])
                else:
                    subprocess.run(['spotify'])
                return "Reproduciendo en Spotify", True
            elif platform == 'youtube':
                if query:
                    url = f"https://www.youtube.com/results?search_query={query}"
                else:
                    url = "https://www.youtube.com"
                webbrowser.open(url)
                return "Abriendo YouTube", True
            return "Plataforma no especificada", False
        except Exception as e:
            logger.error(f"Error reproduciendo media: {e}")
            return str(e), False

    def _pause_media(self, **kwargs) -> Tuple[str, bool]:
        try:
            # Enviar señal de pausa a través de dbus
            subprocess.run(['playerctl', 'pause'])
            return "Reproducción pausada", True
        except Exception as e:
            logger.error(f"Error pausando reproducción: {e}")
            return str(e), False

    def _next_track(self, **kwargs) -> Tuple[str, bool]:
        try:
            subprocess.run(['playerctl', 'next'])
            return "Siguiente pista", True
        except Exception as e:
            logger.error(f"Error cambiando pista: {e}")
            return str(e), False

    def _previous_track(self, **kwargs) -> Tuple[str, bool]:
        try:
            subprocess.run(['playerctl', 'previous'])
            return "Pista anterior", True
        except Exception as e:
            logger.error(f"Error regresando pista: {e}")
            return str(e), False

    def format_command_response(self, command: str, additional_info: str = "") -> str:
        formatted = f"{self.command_prefix}_{command}"
        logger.debug(f"Formato de respuesta: {formatted}")
        return formatted

    def execute_command(self, command: str, **kwargs) -> Tuple[str, bool]:
        """Sobrescribir método de BaseCommander para debugging."""
        logger.debug(f"Ejecutando comando: {command} con kwargs: {kwargs}")
        if command not in self.commands:
            logger.error(f"Comando {command} no encontrado en {self.commands.keys()}")
            return f"Comando {command} no encontrado", False
            
        handler = self.commands[command]['handler']
        return handler(**kwargs)
