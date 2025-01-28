import logging
import subprocess
import webbrowser
from typing import Dict, Tuple
from .base_commander import BaseCommander

logger = logging.getLogger(__name__)

class MultimediaCommander(BaseCommander):
    def __init__(self):
        self.command_prefix = "MEDIA"
        super().__init__()

    def initialize_commands(self):
        self.commands = {
            'PLAY': {
                'description': 'Reproduce música o video',
                'examples': ['reproducir música en spotify', 'poner video en youtube'],
                'triggers': ['reproducir', 'poner', 'play', 'escuchar', 'ver video'],
                'handler': self._play_media
            },
            'PAUSE': {
                'description': 'Pausa la reproducción actual',
                'examples': ['pausar música', 'detener reproducción'],
                'triggers': ['pausar', 'pausa', 'detener', 'stop'],
                'handler': self._pause_media
            },
            'NEXT': {
                'description': 'Siguiente canción o video',
                'examples': ['siguiente canción', 'pasar canción'],
                'triggers': ['siguiente', 'próxima', 'pasar'],
                'handler': self._next_track
            },
            'PREVIOUS': {
                'description': 'Canción o video anterior',
                'examples': ['canción anterior', 'regresar canción'],
                'triggers': ['anterior', 'regresar', 'previo'],
                'handler': self._previous_track
            },
            'VOLUME': {
                'description': 'Ajusta el volumen',
                'examples': ['subir volumen', 'bajar volumen', 'volumen 50'],
                'triggers': ['volumen', 'subir volumen', 'bajar volumen'],
                'handler': self._adjust_volume
            }
        }

    def get_rules_text(self) -> str:
        return """
        - Para el módulo MEDIA (MultimediaCommander):
          * Reproducir contenido -> MEDIA_PLAY:plataforma:búsqueda
          * Control de reproducción -> MEDIA_COMANDO
          Ejemplos:
          "reproducir música en spotify" -> MEDIA_PLAY:spotify:nombre_canción
          "ver video en youtube" -> MEDIA_PLAY:youtube:nombre_video
          "subir volumen" -> MEDIA_VOLUME:up
          "bajar volumen" -> MEDIA_VOLUME:down
        """

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

    def _adjust_volume(self, direction: str = None, level: int = None, **kwargs) -> Tuple[str, bool]:
        try:
            if direction == 'up':
                subprocess.run(['amixer', 'set', 'Master', '10%+'])
                return "Volumen aumentado", True
            elif direction == 'down':
                subprocess.run(['amixer', 'set', 'Master', '10%-'])
                return "Volumen disminuido", True
            elif level is not None:
                subprocess.run(['amixer', 'set', 'Master', f'{level}%'])
                return f"Volumen ajustado a {level}%", True
            return "Dirección no especificada", False
        except Exception as e:
            logger.error(f"Error ajustando volumen: {e}")
            return str(e), False

    def process_command_parameters(self, command: str, user_input: str, additional_info: str) -> dict:
        params = {}
        if command == 'PLAY' and additional_info:
            platform, *query_parts = additional_info.split(':')
            params['platform'] = platform.lower()
            params['query'] = ':'.join(query_parts) if query_parts else None
        elif command == 'VOLUME':
            if 'subir' in user_input.lower():
                params['direction'] = 'up'
            elif 'bajar' in user_input.lower():
                params['direction'] = 'down'
            else:
                # Intentar extraer nivel numérico
                import re
                if match := re.search(r'(\d+)', user_input):
                    params['level'] = int(match.group(1))
        return params

    def should_handle_command(self, user_input: str) -> bool:
        media_keywords = ['reproducir', 'pausar', 'siguiente', 'anterior', 'volumen', 
                         'spotify', 'youtube', 'música', 'video']
        return any(keyword in user_input.lower() for keyword in media_keywords)

    def extract_command_info(self, user_input: str) -> tuple:
        lower_input = user_input.lower()
        
        # Detectar plataforma y búsqueda para PLAY
        if any(word in lower_input for word in ['reproducir', 'poner', 'escuchar']):
            platform = 'spotify' if 'spotify' in lower_input else 'youtube'
            # Extraer texto de búsqueda después de "en spotify/youtube"
            import re
            if match := re.search(rf'(?:en {platform})\s+(.+)', lower_input):
                query = match.group(1)
                return 'PLAY', f"{platform}:{query}"
            return 'PLAY', platform

        # Mapeo directo para otros comandos
        command_mapping = {
            'pausar': 'PAUSE',
            'siguiente': 'NEXT',
            'anterior': 'PREVIOUS',
            'volumen': 'VOLUME'
        }
        
        for key, cmd in command_mapping.items():
            if key in lower_input:
                return cmd, None
        
        return None, None

    def format_command_response(self, command: str, additional_info: str = "") -> str:
        if command == 'PLAY' and additional_info:
            return f"{self.command_prefix}_{command}:{additional_info}"
        return f"{self.command_prefix}_{command}"
