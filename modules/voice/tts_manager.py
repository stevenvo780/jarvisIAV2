import os
import tempfile
import pygame
from gtts import gTTS
import logging
from typing import Optional

class TTSManager:
    def __init__(self):
        self.is_speaking = False
        self.language = 'es'
        self.temp_dir = tempfile.gettempdir()
        self.temp_file = os.path.join(self.temp_dir, 'jarvis_speech.mp3')
        
        # Inicializar pygame mixer
        try:
            pygame.mixer.init()
            logging.info("Pygame mixer inicializado correctamente")
        except Exception as e:
            logging.error(f"Error inicializando pygame mixer: {e}")

    def speak(self, text: str) -> bool:
        if self.is_speaking:
            return False
            
        try:
            self.is_speaking = True
            
            # Crear archivo de audio temporal
            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(self.temp_file)
            
            # Reproducir audio
            pygame.mixer.music.load(self.temp_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Limpiar archivo temporal
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
                
            self.is_speaking = False
            return True
            
        except Exception as e:
            logging.error(f"Error en TTS: {e}")
            self.is_speaking = False
            return False

    def configure(self, language: Optional[str] = None) -> None:
        if language:
            self.language = language

    def __del__(self):
        try:
            pygame.mixer.quit()
        except:
            pass
