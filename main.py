#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
import signal
from queue import Queue, Empty
from dotenv import load_dotenv
import torch
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Add the root directory to sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

# Initial environment configuration
os.environ.update({
    'PYTORCH_ENABLE_MPS_FALLBACK': '1',
    'PYTHONWARNINGS': 'ignore'
})

# Custom imports
from utils.error_handler import setup_logging, handle_errors, AudioError, ModelError
from modules.terminal_manager import TerminalManager
from modules.llm.model_manager import ModelManager
from modules.voice import SpeechRecognition, TTSManager
from modules.system_monitor import SystemMonitor
from modules.voice.audio_config import AudioConfig
from modules.text.text_handler import TextHandler

# Logging
setup_logging()

class Jarvis:
    def __init__(self):
        self.terminal = TerminalManager()
        self.input_queue = Queue()
        self.audio_init_queue = Queue()
        
        # States
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
            # Start audio in background
            # self._start_audio_initialization()
            self._initialize_text_mode()
        except Exception as e:
            self.terminal.print_error(f"Initialization error: {e}")
            sys.exit(1)

    def _setup_signal_handlers(self):
        """Sets up OS signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._graceful_shutdown)
        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def _graceful_shutdown(self, signum=None, frame=None):
        """Handles graceful system shutdown."""
        self.state['running'] = False
        self.terminal.print_warning("\nShutdown signal received...")

    def _initialize_system(self):
        """Initializes system components."""
        self.terminal.print_header("Starting Jarvis System")
        load_dotenv()
        self.model = ModelManager()
        self.terminal.print_success("System initialized (voice mode pending)")

    def _start_audio_initialization(self):
        """Launches audio initialization in a background thread."""
        self.audio_init_thread = threading.Thread(
            target=self._async_audio_init,
            daemon=True
        )
        self.audio_init_thread.start()

    def _async_audio_init(self):
        """Asynchronous audio system initialization."""
        try:
            self.audio_config = AudioConfig(timeout=5)
            audio_ok, message = self.audio_config.test_audio_system()
            if not audio_ok:
                raise AudioError(message)
            self.tts = TTSManager()
            self.speech = SpeechRecognition(
                terminal=self.terminal,
                language="es",
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
            
            # Audio init success
            self.state['audio_initialized'] = True
            self.state['voice_active'] = True
            self.terminal.print_success("Voice system initialized successfully")
            return True
            
        except Exception as e:
            self.state['voice_active'] = False
            self.state['audio_initialized'] = False
            self.terminal.print_warning(f"Fallback to text mode: {str(e)}")
            logging.error(f"Audio initialization error: {e}")

    def _initialize_text_mode(self):
        """Initializes text mode handler."""
        if not self.text_handler:
            self.text_handler = TextHandler(
                terminal_manager=self.terminal,
                input_queue=self.input_queue,
                state=self.state
            )
            self.terminal.print_success("Text mode available")

    def _start_service_threads(self):
        """Starts needed background threads (system monitor, voice input if available, text input)."""
        threads = []
        
        # Start system monitor
        t_monitor = threading.Thread(target=self._system_monitor, daemon=True)
        threads.append(t_monitor)
        
        # Start voice input if audio is ok
        if self.state['audio_initialized'] and self.state['voice_active']:
            t_voice = threading.Thread(target=self._voice_input_handler, daemon=True)
            threads.append(t_voice)

        # Start text handler input thread
        if self.text_handler:
            self.text_handler.start()

        for t in threads:
            t.start()
        return threads

    def _voice_input_handler(self):
        """Voice input loop."""
        while self.state['running'] and self.state['voice_active']:
            try:
                text = self.speech.listen_and_recognize()
                if text:
                    self.input_queue.put(('voice', text))
            except Exception as e:
                self._handle_critical_error(f"Voice error: {str(e)}")
                self.state['voice_active'] = False
                break
            time.sleep(0.1)

    def _system_monitor(self):
        """Periodically checks system health."""
        while self.state['running']:
            try:
                health_status = self.system_monitor.check_system_health()
                
                if all(health_status.values()):
                    self.state['error_count'] = 0
                else:
                    self.state['error_count'] += 1
                    failed_systems = [k.replace('_ok', '') 
                                      for k, v in health_status.items() if not v]
                    self.terminal.print_warning(
                        f"Alert: Problematic systems: {', '.join(failed_systems)}"
                    )
                    logging.warning(f"Compromised systems: {failed_systems}")
                
                time.sleep(5)
            except Exception as e:
                logging.error(f"Monitor error: {str(e)}")

    def _handle_critical_error(self, message: str):
        """Handles critical errors and increments error count."""
        logging.critical(message)
        self.terminal.print_error(message)
        self.state['error_count'] += 1
        
        if self.state['error_count'] >= self.state['max_errors']:
            self.terminal.print_error("Max error limit reached")
            self._graceful_shutdown()

    def _process_inputs(self):
        """Continuously processes queued inputs from voice or keyboard."""
        while self.state['running']:
            try:
                input_type, content = self.input_queue.get(timeout=0.5)
                self.terminal.print_thinking()
                
                # Get LLM response
                response = self.model.get_response(content)
                self.terminal.print_response(response)
                
                # If voice is active, TTS
                if input_type == 'voice' or self.state['voice_active']:
                    if hasattr(self, 'tts'):
                        self.tts.speak(response)
                
                self.input_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self._handle_critical_error(f"Error processing input: {str(e)}")

    def run(self):
        """Main execution loop."""
        try:
            # Start service threads
            threads = self._start_service_threads()
            
            # Start a separate thread to consume inputs
            process_thread = threading.Thread(target=self._process_inputs, daemon=True)
            process_thread.start()
            
            self.terminal.print_header("Operating System")
            
            # Keep the main thread alive
            while self.state['running']:
                time.sleep(0.5)
            
            # Join threads
            process_thread.join(timeout=2)
            for t in threads:
                t.join(timeout=2)
                
        finally:
            self._shutdown_system()

    def _shutdown_system(self):
        """Clean shutdown procedure."""
        self.terminal.print_status("\nShutting down system...")
        try:
            if self.text_handler:
                self.text_handler.stop()
            if hasattr(self, 'tts'):
                self.tts.cleanup()
            if hasattr(self, 'speech'):
                self.speech.cleanup()
            self.terminal.print_goodbye()
        except Exception as e:
            logging.error(f"Shutdown error: {str(e)}")
        finally:
            os._exit(0)

if __name__ == "__main__":
    jarvis = Jarvis()
    try:
        jarvis.run()
    except KeyboardInterrupt:
        print("\nShutdown signal received...")
    finally:
        jarvis._shutdown_system()
