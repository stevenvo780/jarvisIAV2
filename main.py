# main.py
#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
import signal
from queue import Queue, Empty
from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
import torch

from concurrent.futures import ThreadPoolExecutor, TimeoutError

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from utils.error_handler import setup_logging, handle_errors, AudioError, ModelError
from modules.terminal_manager import TerminalManager
from modules.llm.model_manager import ModelManager
from modules.system_monitor import SystemMonitor
from modules.text.text_handler import TextHandler

from modules.voice.audio_config import AudioConfig
from modules.voice.audio_handler import AudioEngine
from modules.voice.speech_recognition import SpeechRecognition
from modules.voice.tts_manager import TTSManager

setup_logging()

def beep(freq=1000, duration=0.3, sr=44100):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = 0.1 * np.sin(2 * np.pi * freq * t)
    sd.play(wave.astype(np.float32), sr)
    sd.wait()

def list_input_devices():
    d = sd.query_devices()
    r = []
    for i, dev in enumerate(d):
        if dev['max_input_channels'] > 0:
            r.append((i, dev['name'], dev['default_samplerate']))
    return r

def select_input_device():
    devs = list_input_devices()
    if not devs:
        print("No input devices found")
        sys.exit(1)
    for i, v in enumerate(devs):
        print(f"[{i}] {v[1]} (index={v[0]}, samplerate={v[2]})")
    c = input("Select input device by number: ")
    try:
        c = int(c)
        return devs[c][0]
    except:
        print("Invalid selection")
        sys.exit(1)

class Jarvis:
    def __init__(self):
        self.terminal = TerminalManager()
        self.input_queue = Queue()
        self.audio_init_queue = Queue()
        self.state = {
            'running': True,
            'voice_active': True,
            'audio_initialized': False,
            'error_count': 0,
            'max_errors': 5
        }
        self.system_monitor = SystemMonitor()
        self.text_handler = None
        try:
            self._setup_signal_handlers()
            self._initialize_system()
            self._start_audio_initialization()
            self._initialize_text_mode()
            self.terminal.print_status("System ready")
        except Exception as e:
            self.terminal.print_error(f"Initialization error: {e}")
            sys.exit(1)

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._graceful_shutdown)
        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def _graceful_shutdown(self, signum=None, frame=None):
        self.state['running'] = False
        self.terminal.print_warning("Shutdown signal received...")

    def _initialize_system(self):
        self.terminal.print_header("Starting Jarvis System")
        load_dotenv()
        self.model = ModelManager()
        self.terminal.print_success("Core system initialized")

    def _start_audio_initialization(self):
        t = threading.Thread(target=self._async_audio_init, daemon=True)
        t.start()

    def _async_audio_init(self):
        try:
            self.audio_engine = AudioEngine.initialize_audio_system()
            self.tts = TTSManager()
            self.speech = SpeechRecognition(language="es")
            
            def wake_word_callback(audio_segment):
                text = self.speech.transcribe_audio(audio_segment)
                if text and "jarvis" in text.lower():
                    from modules.voice.audio_utils import beep
                    beep()
                    return True
                return False
            
            def command_callback(audio_segment):
                text = self.speech.transcribe_audio(audio_segment)
                if text:
                    self.input_queue.put(('voice', text))
                    
            self.audio_engine.start_listening(wake_word_callback, command_callback)
            self.state['audio_initialized'] = True
            self.state['voice_active'] = True
            self.terminal.print_success("Voice system initialized")
        except Exception as e:
            self.state['voice_active'] = False
            self.state['audio_initialized'] = False
            self.terminal.print_warning(f"Fallback to text mode: {e}")
            logging.error(f"Audio init error: {e}")

    def _initialize_text_mode(self):
        if not self.text_handler:
            self.text_handler = TextHandler(
                terminal_manager=self.terminal,
                input_queue=self.input_queue,
                state=self.state
            )
            self.terminal.print_success("Text mode ready")

    def _handle_critical_error(self, message):
        logging.critical(message)
        self.terminal.print_error(message)
        self.state['error_count'] += 1
        if self.state['error_count'] >= self.state['max_errors']:
            self.terminal.print_error("Max error limit reached")
            self._graceful_shutdown()

    def _system_monitor(self):
        while self.state['running']:
            try:
                status = self.system_monitor.check_system_health()
                if all(status.values()):
                    self.state['error_count'] = 0
                else:
                    self.state['error_count'] += 1
                    f = [k.replace('_ok','') for k,v in status.items() if not v]
                    self.terminal.print_warning(f"Alert: {', '.join(f)} failure")
                    logging.warning(f"Compromised: {f}")
                time.sleep(5)
            except Exception as e:
                logging.error(f"Monitor error: {str(e)}")

    def _process_inputs(self):
        try:
            t, content = self.input_queue.get_nowait()
            self.terminal.print_thinking()
            response, model_name = self.model.get_response(content)
            self.terminal.print_response(response, model_name)
            if t == 'voice' or self.state['voice_active']:
                if hasattr(self, 'tts'):
                    self.tts.speak(response)
            self.input_queue.task_done()
        except Empty:
            pass
        except Exception as e:
            self._handle_critical_error(f"Error processing input: {str(e)}")

    def _shutdown_system(self):
        self.terminal.print_status("Shutting down...")
        try:
            if self.text_handler:
                self.text_handler.stop()
            if hasattr(self, 'tts'):
                self.tts.cleanup()
            if hasattr(self, 'speech'):
                self.speech.cleanup()
            if hasattr(self, 'audio_engine'):
                self.audio_engine.cleanup()
            self.terminal.print_goodbye()
        except Exception as e:
            logging.error(f"Shutdown error: {str(e)}")
        finally:
            os._exit(0)

    def run(self):
        m = threading.Thread(target=self._system_monitor, daemon=True)
        m.start()
        p = threading.Thread(target=self._process_inputs_loop, daemon=True)
        p.start()
        self.terminal.print_header("Operating System")
        if self.text_handler:
            self.text_handler.run_interactive()

    def _process_inputs_loop(self):
        while self.state['running']:
            self._process_inputs()
            time.sleep(0.1)
        self._shutdown_system()

if __name__ == "__main__":
    jarvis = Jarvis()
    try:
        jarvis.run()
    except KeyboardInterrupt:
        pass
    finally:
        jarvis._shutdown_system()
