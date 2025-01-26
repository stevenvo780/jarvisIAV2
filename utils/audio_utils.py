import os
import logging
import json
from typing import Dict, Optional
import pygame
import warnings
warnings.filterwarnings("ignore")

class AudioEffects:
    def __init__(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        except pygame.error:
            try:
                pygame.mixer.init()
            except pygame.error as e:
                logging.error(f"Could not initialize audio: {e}")
                
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.base_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'sounds')
        self.config_file = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        self._load_sounds()

    def _get_config(self) -> bool:
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('audio', {}).get('sound_effects_enabled', True)
        except Exception as e:
            logging.error(f"Error reading config: {e}")
            return True

    def _load_sounds(self) -> None:
        sound_files = {
            'startup': 'startup.mp3',
            'error': 'error.mp3',
            'notification': 'notification.mp3',
            'listening': 'listening.mp3',
            'thinking': 'thinking.mp3',
            'command': 'command.mp3'
        }

        os.makedirs(self.base_path, exist_ok=True)

        for sound_name, filename in sound_files.items():
            try:
                filepath = os.path.join(self.base_path, filename)
                if os.path.exists(filepath):
                    self.sounds[sound_name] = pygame.mixer.Sound(filepath)
                else:
                    logging.warning(f"Archivo de sonido no encontrado: {filepath}")
                    self.sounds[sound_name] = None
            except Exception as e:
                logging.error(f"Error cargando sonido {sound_name}: {e}")
                self.sounds[sound_name] = None

    def play(self, sound_name: str, volume: float = 0.5) -> None:
        """Reproduce un efecto de sonido por nombre"""
        if not self._get_config():
            return
            
        try:
            sound = self.sounds.get(sound_name)
            if sound:
                sound.set_volume(volume)
                sound.play()
        except Exception as e:
            logging.error(f"Error reproduciendo sonido {sound_name}: {e}")

    def stop_all(self) -> None:
        """Detiene todos los sonidos en reproducción"""
        try:
            pygame.mixer.stop()
        except Exception as e:
            logging.error(f"Error deteniendo sonidos: {e}")

    def __del__(self):
        """Limpieza al destruir la instancia"""
        try:
            pygame.mixer.quit()
        except:
            pass