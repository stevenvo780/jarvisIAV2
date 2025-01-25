import os
import tempfile
import pygame
import time  # Añadido import time
from gtts import gTTS
import logging
import threading
from queue import Queue
from typing import Optional
from contextlib import contextmanager
from utils.error_handler import handle_errors, AudioError

class TTSManager:
    def __init__(self):
        self.is_speaking = False
        self.should_stop = False
        self.language = 'es'
        self.temp_dir = tempfile.gettempdir()
        self.temp_file = os.path.join(self.temp_dir, 'jarvis_speech.mp3')
        self.speech_queue = Queue()
        self.speech_thread = None
        self.running = True  # Flag para controlar el thread
        self._setup_mixer()
        self._start_speech_thread()
    
    def _start_speech_thread(self):
        """Inicia el hilo de procesamiento de voz"""
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()

    def _process_speech_queue(self):
        """Procesa la cola de mensajes de voz"""
        while self.running:  # Usar flag para control del loop
            try:
                if not self.speech_queue.empty():
                    text = self.speech_queue.get()
                    if text == "STOP":
                        self.stop_speaking()
                        continue
                    self._speak_text(text)
                    self.speech_queue.task_done()
                else:
                    time.sleep(0.1)  # Evitar CPU alto cuando está idle
            except Exception as e:
                logging.error(f"Error en thread de voz: {e}")
                time.sleep(1)  # Esperar si hay error

    def stop_speaking(self):
        """Detiene la reproducción actual"""
        self.should_stop = True
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.is_speaking = False
        self.should_stop = False

    def _speak_text(self, text: str) -> bool:
        """Reproduce el texto internamente"""
        if not text or self.should_stop:
            return False

        try:
            self.is_speaking = True
            with self._temp_audio_file():
                if not pygame.mixer.get_init():
                    self._setup_mixer()

                tts = gTTS(text=text, lang=self.language, slow=False)
                tts.save(self.temp_file)
                
                retries = 3
                while retries > 0 and not self.should_stop:
                    try:
                        pygame.mixer.music.load(self.temp_file)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy() and not self.should_stop:
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

    def speak(self, text: str):
        """Añade texto a la cola de reproducción"""
        if isinstance(text, str) and text.strip():
            if not self.speech_thread or not self.speech_thread.is_alive():
                self._start_speech_thread()  # Reiniciar thread si murió
            self.speech_queue.put(text.strip())
            logging.debug(f"Texto añadido a cola: {text[:50]}...")

    @handle_errors(error_type=AudioError, log_message="Error inicializando mixer")
    def _setup_mixer(self) -> None:
        try:
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
        """Limpia recursos"""
        self.running = False  # Señalizar threads para terminar
        self.stop_speaking()
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=2)  # Esperar thread
        try:
            pygame.mixer.quit()
        except Exception as e:
            logging.error(f"Error en cleanup de pygame: {e}")

    def configure(self, language: Optional[str] = None) -> None:
        if language:
            self.language = language

    def __del__(self):
        self.cleanup()
