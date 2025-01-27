import os
import tempfile
import pygame
import time
from gtts import gTTS
import logging
import threading
from queue import Queue, Empty
from typing import Optional, List
from contextlib import contextmanager
from utils.error_handler import handle_errors, AudioError
import json

class TTSManager:
    def __init__(self):
        self.is_speaking = False
        self.should_stop = False
        self.language = 'es'
        self.temp_dir = tempfile.gettempdir()
        self.temp_file = os.path.join(self.temp_dir, 'jarvis_speech.mp3')
        self.speech_queue = Queue()
        self.speech_thread = None
        self.running = True
        self.config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.json')
        self.config = self.load_config()
        self._setup_mixer()
        self._start_speech_thread()

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return {"audio": {"tts_enabled": True}}

    def _start_speech_thread(self):
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()

    def _process_speech_queue(self):
        while self.running:
            try:
                if not self.speech_queue.empty():
                    text = self.speech_queue.get()
                    
                    if text == "STOP":
                        self.stop_speaking()
                        continue
                        
                    if self._speak_text(text):
                        self.speech_queue.task_done()
                    else:
                        self.speech_queue.task_done()
                        break
                else:
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"Error en thread de voz: {e}")
                time.sleep(1)

    def stop_speaking(self):
        self.should_stop = True
        
        # Limpiar cola de reproducción
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except Empty:
                break
                
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            
        self.is_speaking = False
        self.should_stop = False

    def _speak_text(self, text: str) -> bool:
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
        if not self._get_config():
            return
            
        if isinstance(text, str) and text.strip():
            chunks = self._split_text(text.strip())
            
            for chunk in chunks:
                if chunk:
                    self.speech_queue.put(chunk)
            
            logging.debug(f"Texto dividido en {len(chunks)} fragmentos")

    def _split_text(self, text: str) -> List[str]:
        split_chars = ['.', '!', '?', ';', ',']
        sentences = []
        current = []
        
        for char in text:
            current.append(char)
            if char in split_chars:
                sentence = ''.join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []
        
        # Añadir el último fragmento si queda texto
        if current:
            sentence = ''.join(current).strip()
            if sentence:
                sentences.append(sentence)
        
        # Dividir fragmentos largos sin puntuación
        max_length = 200
        final_sentences = []
        for sentence in sentences:
            if len(sentence) > max_length:
                parts = [sentence[i:i+max_length] for i in range(0, len(sentence), max_length)]
                final_sentences.extend(parts)
            else:
                final_sentences.append(sentence)
                
        return final_sentences

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
        try:
            yield self.temp_file
        finally:
            if os.path.exists(self.temp_file):
                try:
                    os.remove(self.temp_file)
                except OSError as e:
                    logging.warning(f"Error eliminando archivo temporal: {e}")

    def cleanup(self):
        self.running = False
        self.stop_speaking()
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=2)
        try:
            pygame.mixer.quit()
        except Exception as e:
            logging.error(f"Error en cleanup de pygame: {e}")

    def configure(self, language: Optional[str] = None) -> None:
        if language:
            self.language = language

    def _get_config(self) -> bool:
        return self.config.get('audio', {}).get('tts_enabled', True)

    def __del__(self):
        self.cleanup()