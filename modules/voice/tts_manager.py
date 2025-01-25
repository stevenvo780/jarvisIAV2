import os
import tempfile
import pygame
from gtts import gTTS
import logging
from typing import Optional
from contextlib import contextmanager
from utils.error_handler import handle_errors, AudioError
from utils.audio_manager import AudioManager  # Asegurar que AudioManager está importado

class TTSManager:
    def __init__(self):
        self.is_speaking = False
        self.language = 'es'
        self.temp_dir = tempfile.gettempdir()
        self.temp_file = os.path.join(self.temp_dir, 'jarvis_speech.mp3')
        
        self._setup_mixer()
    
    @handle_errors(error_type=AudioError, log_message="Error inicializando mixer")
    def _setup_mixer(self) -> None:
        try:
            with AudioManager.suppress_output():
                pygame.mixer.pre_init(44100, -16, 2, 2048)
                pygame.mixer.init()
                pygame.mixer.set_num_channels(16)
            
            if not pygame.mixer.get_init():
                raise AudioError("Mixer no inicializado correctamente")
                
            logging.info("Pygame mixer inicializado correctamente")
        except Exception as e:
            raise AudioError(f"Error inicializando pygame mixer: {e}")

    @contextmanager
    def _temp_audio_file(self):
        """Gestiona el ciclo de vida del archivo temporal de audio"""
        try:
            yield self.temp_file
        finally:
            if os.path.exists(self.temp_file):
                try:
                    os.remove(self.temp_file)
                except OSError as e:
                    logging.warning(f"Error eliminando archivo temporal: {e}")

    def cleanup(self):
        """Limpia recursos explícitamente"""
        try:
            pygame.mixer.quit()
        except Exception as e:
            logging.error(f"Error en cleanup de pygame: {e}")

    def speak(self, text: str) -> bool:
        if not isinstance(text, str) or not text.strip():
            return False

        if self.is_speaking:
            return False

        try:
            self.is_speaking = True
            with AudioManager.suppress_output(), self._temp_audio_file():
                # Verificar estado del audio
                if not pygame.mixer.get_init():
                    self._setup_mixer()

                tts = gTTS(text=text, lang=self.language, slow=False)
                tts.save(self.temp_file)
                
                # Reintentar reproducción si falla
                retries = 3
                while retries > 0:
                    try:
                        pygame.mixer.music.load(self.temp_file)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        break
                    except Exception as e:
                        retries -= 1
                        if retries == 0:
                            raise e
                        pygame.mixer.quit()
                        self._setup_mixer()
                        time.sleep(1)
            
            return True
        except Exception as e:
            logging.error(f"Error en TTS: {e}")
            return False
        finally:
            self.is_speaking = False

    def configure(self, language: Optional[str] = None) -> None:
        if language:
            self.language = language

    def __del__(self):
        self.cleanup()
