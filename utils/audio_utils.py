import os
import logging
from typing import Dict, Optional
import pygame

class AudioEffects:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.base_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'sounds')
        self._load_sounds()

    def _load_sounds(self) -> None:
        """Carga los efectos de sonido desde el directorio de assets"""
        sound_files = {
            'startup': 'startup.wav',
            'shutdown': 'shutdown.wav',
            'processing': 'processing.wav',
            'success': 'success.wav',
            'error': 'error.wav',
            'notification': 'notification.wav',
            'listening': 'listening.wav',
            'command': 'command.wav'
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