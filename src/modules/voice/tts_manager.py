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
        self.audio_buffer = Queue(maxsize=3)  
        self.current_audio = None
        self.preload_thread = None
        self.temp_files = {}  
        self._setup_mixer()
        self._start_speech_thread()
        self._start_preload_thread()

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

    def _start_preload_thread(self):
        self.preload_thread = threading.Thread(target=self._preload_audio, daemon=True)
        self.preload_thread.start()

    def _preload_audio(self):
        while self.running:
            try:
                if not self.speech_queue.empty() and self.audio_buffer.qsize() < 3:
                    text = self.speech_queue.get()
                    if text == "STOP":
                        self.stop_speaking()
                        continue
                    
                    temp_file = os.path.join(self.temp_dir, f'jarvis_speech_{time.time()}.mp3')
                    tts = gTTS(text=text, lang=self.language, slow=False)
                    tts.save(temp_file)
                    self.temp_files[text] = temp_file
                    self.audio_buffer.put(text)
                    self.speech_queue.task_done()
                else:
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"Error en preload de audio: {e}")
                time.sleep(1)

    @handle_errors(error_type=AudioError, log_message="Error inicializando mixer")
    def _setup_mixer(self) -> None:
        try:
            pygame.mixer.pre_init(44100, -16, 2, 1024)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            
            if not pygame.mixer.get_init():
                raise AudioError("Mixer no inicializado correctamente")
            
            self.current_channel = 0
            logging.info("Pygame mixer inicializado correctamente")
        except Exception as e:
            raise AudioError(f"Error inicializando pygame mixer: {e}")

    def _get_next_channel(self):
        if not hasattr(self, 'current_channel'):
            self.current_channel = 0
        self.current_channel = (self.current_channel + 1) % pygame.mixer.get_num_channels()
        return pygame.mixer.Channel(self.current_channel)

    def _process_speech_queue(self):
        while self.running:
            try:
                if not self.audio_buffer.empty() and not self.should_stop:
                    text = self.audio_buffer.get()
                    temp_file = self.temp_files.get(text)
                    
                    if temp_file and os.path.exists(temp_file):
                        self.is_speaking = True
                        sound = pygame.mixer.Sound(temp_file)
                        channel = self._get_next_channel()
                        channel.play(sound)
                        
                        # Esperar a que termine el audio actual
                        while channel.get_busy() and not self.should_stop:
                            time.sleep(0.1)
                            
                        os.remove(temp_file)
                        del self.temp_files[text]
                        self.audio_buffer.task_done()
                        self.is_speaking = False
                else:
                    time.sleep(0.05)
            except Exception as e:
                logging.error(f"Error en reproducción de audio: {e}")
                time.sleep(0.1)
                self.is_speaking = False

    def stop_speaking(self):
        self.should_stop = True
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except Empty:
                break
        
        pygame.mixer.stop()
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
            chunks = self._split_text(text.strip(), max_length=100)
            
            for chunk in chunks:
                if chunk:
                    self.speech_queue.put(chunk)

    def _split_text(self, text: str, max_length: int = 80) -> List[str]:
        sentences = []
        current = []
        
        for word in text.split():
            current.append(word)
            current_text = ' '.join(current)
            
            if len(current_text) > max_length:
                if current:
                    sentences.append(' '.join(current[:-1]))
                    current = [word]
            elif '.' in word or ',' in word or '?' in word or '!' in word:
                sentences.append(current_text)
                current = []
                
        if current:
            sentences.append(' '.join(current))
            
        return sentences

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
        for temp_file in self.temp_files.values():
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=2)
        if self.preload_thread and self.preload_thread.is_alive():
            self.preload_thread.join(timeout=2)
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