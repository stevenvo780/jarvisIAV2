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
        self.base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'sounds'))
        self.config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.json'))
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
            'ready': 'ready.mp3',
            'thinking': 'listening.mp3',
            'command': 'ready.mp3',
            'notification': 'ready.mp3',
            'listening': 'listening.mp3'
        }

        if not os.path.exists(self.base_path):
            logging.error(f"Directory not found: {self.base_path}")
            return

        for sound_name, filename in sound_files.items():
            try:
                filepath = os.path.join(self.base_path, filename)
                if os.path.exists(filepath):
                    self.sounds[sound_name] = pygame.mixer.Sound(filepath)
                else:
                    logging.warning(f"Sound file not found: {filepath}")
                    self.sounds[sound_name] = None
            except Exception as e:
                logging.error(f"Error loading sound {sound_name}: {e}")
                self.sounds[sound_name] = None

    def play(self, sound_name: str, volume: float = 0.5) -> None:
        try:
            sound = self.sounds.get(sound_name)
            if sound:
                sound.set_volume(volume)
                sound.play()
        except Exception as e:
            logging.error(f"Error reproduciendo sonido {sound_name}: {e}")

    def stop_all(self) -> None:
        try:
            pygame.mixer.stop()
        except Exception as e:
            logging.error(f"Error deteniendo sonidos: {e}")

    def __del__(self):
        try:
            pygame.mixer.quit()
        except:
            pass