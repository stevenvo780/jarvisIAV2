import logging
import subprocess
import webbrowser
import time
from typing import Dict, Tuple
from urllib.parse import quote_plus
from .base_commander import BaseCommander

logger = logging.getLogger(__name__)

class MultimediaCommander(BaseCommander):
    def __init__(self, model_manager=None):
        super().__init__()
        self.command_prefix = "MEDIA"
        self.model_manager = model_manager
        self.initialize_commands()

    def initialize_commands(self):
        """Initialize available commands."""
        self.commands = {
            'VOLUME': {
                'description': 'Adjust system volume',
                'examples': ['subir volumen', 'bajar volumen'],
                'triggers': ['volumen', 'subir', 'bajar', 'sube', 'baja'],
                'handler': self._adjust_volume
            },
            'MUSIC': {
                'description': 'Play music or videos',
                'examples': ['reproduce Metallica', 'pon un video de cocina'],
                'triggers': ['reproduce', 'pon', 'play', 'música', 'spotify',
                             'youtube', 'video', 'videos', 'music'],
                'handler': self._play_media
            },
            'PAUSE': {
                'description': 'Pause current playback',
                'examples': ['pausa', 'detener'],
                'triggers': ['pausa', 'pausar', 'detener', 'stop'],
                'handler': self._pause_media
            },
            'RESUME': {
                'description': 'Resume playback',
                'examples': ['reanudar', 'continua', 'resume'],
                'triggers': ['reanudar', 'continua', 'resume', 'seguir'],
                'handler': self._resume_media
            }
        }

    def get_rules_text(self) -> str:
        return """
        - Para el módulo MEDIA (MultimediaCommander):
          * Control de volumen -> MEDIA_VOLUME
          * Reproducir contenido -> MEDIA_PLAY:plataforma:búsqueda
          * Pausar reproducción -> MEDIA_PAUSE
          * Reanudar reproducción -> MEDIA_RESUME
        """

    def should_handle_command(self, user_input: str) -> bool:
        """Check if this commander should handle the command."""
        lower_input = user_input.lower()
        all_triggers = []
        for cmd_info in self.commands.values():
            all_triggers.extend(cmd_info['triggers'])

        result = any(k in lower_input for k in all_triggers)
        logger.debug(f"Should handle '{user_input}': {result}")
        return result

    def extract_command_info(self, user_input: str) -> Tuple[str, str]:
        logger.debug(f"Extracting command info from: {user_input}")
        lower_input = user_input.lower()

        for command_name, command_data in self.commands.items():
            if any(t in lower_input for t in command_data['triggers']):
                # If it's MUSIC, detect platform, then clean query
                if command_name == 'MUSIC':
                    platform = self._detect_platform(lower_input)
                    search_terms = self._clean_search_terms(lower_input)
                    if search_terms:
                        return 'MUSIC', f"{platform}:{search_terms}"
                return command_name, None
        return None, None

    def _detect_platform(self, text: str) -> str:
        text = text.lower()

        if 'spotify' in text:
            return 'spotify'
        if 'youtube' in text:
            return 'youtube'
        if 'video' in text or 'videos' in text:
            return 'youtube'
        if 'music' in text or 'música' in text:
            return 'spotify'

        return 'spotify'

    def _clean_search_terms(self, text: str) -> str:
        text = text.lower()
        keywords_to_remove = [
            'reproduce', 'pon', 'play', 'youtube', 'spotify',
            'música', 'music', 'video', 'videos', 'ponme', 'escuchar', 'ver',
            'un', 'una', 'el', 'la', 'los', 'las', 'de',
            'musica', 'cancion', 'canciones', 'subir', 'bajar', 'volumen',
            'pausar', 'pausa', 'detener', 'resume', 'reanudar', 'continua',
            'seguir', 'stop'
        ]

        tokens = text.split()
        cleaned_tokens = [token for token in tokens if token not in keywords_to_remove]
        cleaned_text = ' '.join(cleaned_tokens).strip()
        return cleaned_text

    def process_command_parameters(self, command: str, user_input: str, additional_info: str) -> dict:
        """Process command parameters and return a dict with relevant info."""
        logger.debug(f"Processing parameters: command={command}, input={user_input}, additional_info={additional_info}")

        if command == 'VOLUME':
            lower_input = user_input.lower()
            if any(w in lower_input for w in ['subir', 'sube', 'más', 'aumenta']):
                return {'direction': 'up'}
            return {'direction': 'down'}

        elif command == 'MUSIC':
            if additional_info:
                parts = additional_info.split(':', 1)
                if len(parts) == 2:
                    platform, query = parts
                else:
                    platform = 'spotify'
                    query = parts[0]
                return {'platform': platform.strip(), 'query': query.strip()}

            detected_platform = self._detect_platform(user_input)
            search_terms = self._clean_search_terms(user_input)
            return {'platform': detected_platform, 'query': search_terms}

        return {}

    def format_command_response(self, command: str, additional_info: str = "") -> str:
        formatted = f"{self.command_prefix}_{command}"
        logger.debug(f"Formatted response: {formatted}")
        return formatted

    def execute_command(self, command: str, **kwargs) -> Tuple[str, bool]:
        logger.debug(f"Executing command: {command} with kwargs: {kwargs}")
        if command not in self.commands:
            logger.error(f"Command {command} not found in {list(self.commands.keys())}")
            return f"Comando {command} no encontrado", False

        handler = self.commands[command]['handler']
        return handler(**kwargs)

    def _adjust_volume(self, direction: str = None, **kwargs) -> Tuple[str, bool]:
        try:
            logger.debug(f"Adjusting volume: direction={direction}")
            if direction == 'up':
                subprocess.run(['amixer', 'set', 'Master', '10%+'])
                return "Volumen aumentado", True
            elif direction == 'down':
                subprocess.run(['amixer', 'set', 'Master', '10%-'])
                return "Volumen disminuido", True
            return "Dirección no especificada", False
        except Exception as e:
            logger.error(f"Error adjusting volume: {e}")
            return str(e), False

    def _play_media(self, platform: str = None, query: str = None, **kwargs) -> Tuple[str, bool]:
        try:
            logger.debug(f"Playing media: platform={platform}, query={query}")
            if not query or not query.strip():
                return "No se especificó qué reproducir", False

            query = query.strip()

            if platform == 'spotify':
                return self._play_spotify(query)
            elif platform == 'youtube':
                return self._play_youtube(query)

            return "Plataforma no especificada", False

        except Exception as e:
            logger.error(f"Error playing media: {e}")
            return str(e), False

    def _play_spotify(self, query: str) -> Tuple[str, bool]:
        try:
            methods = [
                lambda: subprocess.run(['spotify', '--uri', f'spotify:search:{query}'], check=True),
                lambda: subprocess.run(['xdg-open', f'spotify:search:{query}'], check=True),
                lambda: (
                    subprocess.run(['spotify'], check=True),
                    time.sleep(2),
                    subprocess.run(['playerctl', '-p', 'spotify', 'play'], check=True)
                )
            ]
            for method in methods:
                try:
                    method()
                    return f"Reproduciendo '{query}' en Spotify", True
                except Exception as e:
                    logger.debug(f"Spotify method failed: {e}")
                    continue
            return "No se pudo abrir Spotify", False

        except Exception as e:
            logger.error(f"Error with Spotify: {e}")
            return "Error al reproducir en Spotify", False

    def _play_youtube(self, query: str) -> Tuple[str, bool]:
        """Open a YouTube search URL with the given query."""
        search_query = quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={search_query}"
        webbrowser.open(url)
        return f"Buscando '{query}' en YouTube", True

    def _pause_media(self, **kwargs) -> Tuple[str, bool]:
        """Pause current playback."""
        try:
            subprocess.run(['playerctl', 'pause'], check=True)
            return "Reproducción pausada", True
        except Exception as e:
            logger.error(f"Error pausing playback: {e}")
            return str(e), False

    def _resume_media(self, **kwargs) -> Tuple[str, bool]:
        """Resume current playback."""
        try:
            subprocess.run(['playerctl', 'play'], check=True)
            return "Reproducción reanudada", True
        except Exception as e:
            logger.error(f"Error resuming playback: {e}")
            return str(e), False
