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
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, Future

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

from src.utils.error_handler import setup_logging
from src.utils.audio_utils import AudioEffects
from src.modules.terminal_manager import TerminalManager
from src.modules.llm.model_manager import ModelManager
from src.modules.system_monitor import SystemMonitor
from src.modules.text.text_handler import TextHandler
from src.modules.voice.audio_handler import AudioHandler
from src.modules.voice.tts_manager import TTSManager
from src.modules.storage_manager import StorageManager
from src.modules.command_manager import CommandManager

setup_logging()

class Jarvis:
    def __init__(self):
        self.terminal = TerminalManager()
        self.input_queue = Queue()
        self.state = {
            'running': True,
            'voice_active': True,
            'audio_initialized': False,
            'error_count': 0,
            'max_errors': 5
        }
        self.system_monitor = SystemMonitor()
        self.text_handler = None
        self.audio_effects = AudioEffects()
        self.command_handler = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        try:
            self._setup_signal_handlers()
            self._initialize_system()
            self._initialize_command_handler()
            self._start_audio_initialization()
            self._initialize_text_mode()
            self.terminal.print_status("System ready")
            self.audio_effects.play('startup')
            
            self.monitor_thread = threading.Thread(target=self._system_monitor, daemon=True)
            self.processor_thread = threading.Thread(target=self._process_inputs_loop, daemon=True)
            self.monitor_thread.start()
            self.processor_thread.start()
        except Exception as e:
            self.audio_effects.play('error')
            self.terminal.print_error(f"Initialization error: {e}")
            sys.exit(1)

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._shutdown_system)
        signal.signal(signal.SIGTERM, self._shutdown_system)

    def _shutdown_system(self, signum=None, frame=None):
        self.terminal.print_status("Shutting down...")
        if not self.state['running']:
            return
        try:
            self.state['running'] = False
            self.terminal.print_warning("Shutdown signal received...")
            
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join(timeout=2)
            if hasattr(self, 'processor_thread'):
                self.processor_thread.join(timeout=2)
            
            if hasattr(self, 'audio'):
                self.audio.cleanup()
            if hasattr(self, 'text_handler'):
                self.text_handler.stop()
            if hasattr(self, 'tts'):
                self.tts.cleanup()
                
            if hasattr(self, 'model'):
                del self.model
                
            self.terminal.print_goodbye()
            
        except Exception as e:
            logging.error(f"Shutdown error: {str(e)}")
        finally:
            os._exit(0)

    def _initialize_system(self):
        self.terminal.print_header("Starting Jarvis System")
        load_dotenv()
        
        self.storage = StorageManager()
        
        self.model = ModelManager(storage_manager=self.storage)
        
        self.tts = TTSManager()
        self.model.set_tts_manager(self.tts)
        self.terminal.print_success("Core system initialized")
        self.command_manager = CommandManager(tts=self.tts, state=self.state)

    def _initialize_command_handler(self):
        """Inicializa el manejador de comandos"""
        from src.modules.command_handler import CommandHandler
        self.command_handler = CommandHandler(self.model)
        self.terminal.print_success("Command handler initialized")

    def _start_audio_initialization(self):
        t = threading.Thread(target=self._async_audio_init, daemon=True)
        t.start()

    def _async_audio_init(self):
        try:
            logging.info("Iniciando inicialización de audio...")
            self.audio = AudioHandler(
                terminal_manager=self.terminal,
                tts=self.tts,
                state=self.state
            )
            
            def audio_processor():
                while self.state['running']:
                    try:
                        if not self.state['audio_initialized']:
                            self.state['audio_initialized'] = True
                            logging.info("Audio inicializado correctamente")
                            
                        triggered, command = self.audio.listen_for_trigger("jarvis")
                        
                        if triggered:
                            self.audio_effects.play('command')
                            
                            if command:
                                self.input_queue.put(('voice', command))
                            else:
                                command_text = self.audio.listen_command()
                                if command_text:
                                    self.input_queue.put(('voice', command_text))
                                    
                    except Exception as e:
                        logging.error(f"Error en procesamiento de audio: {e}")
                        self.audio_effects.play('error')
                        time.sleep(1)
                    time.sleep(0.1)

            # Iniciar el procesador de audio en un thread separado
            self.audio_thread = threading.Thread(target=audio_processor, daemon=True)
            self.audio_thread.start()
            
            self.state['audio_initialized'] = True
            self.state['voice_active'] = True
            self.terminal.print_success("🎤 Voice ready")
            
        except Exception as e:
            self.state['voice_active'] = False
            self.state['audio_initialized'] = False
            self.audio_effects.play('error')
            self.terminal.print_warning(f"⌨️ Text mode only: {e}")
            logging.error(f"Audio init error: {e}")

    def _initialize_text_mode(self):
        if not self.text_handler:
            self.text_handler = TextHandler(
                terminal_manager=self.terminal,
                input_queue=self.input_queue,
                state=self.state,
                tts=self.tts
            )
            self.terminal.print_success("Text mode ready")

    def _handle_critical_error(self, message):
        logging.critical(message)
        self.terminal.print_error(message)
        self.audio_effects.play('error')
        self.state['error_count'] += 1
        if self.state['error_count'] >= self.state['max_errors']:
            self.terminal.print_error("Max error limit reached")
            self._shutdown_system()

    def _system_monitor(self):
        while self.state['running']:
            try:
                status = self.system_monitor.check_system_health()
                if all(status.values()):
                    self.state['error_count'] = 0
                else:
                    self.state['error_count'] += 1
                    f = [k.replace('_ok','') for k,v in status.items() if not v]
                    logging.warning(f"Compromised: {f}")
                    time.sleep(5)
            except Exception as e:
                logging.error(f"Monitor error: {str(e)}")
                if self.state['error_count'] >= self.state['max_errors']:
                    sys.exit(1)
            time.sleep(1)

    def _process_inputs(self):
        try:
            t, content = self.input_queue.get_nowait()
            
            if content.strip():
                if hasattr(self, 'tts'):
                    self.tts.stop_speaking()
                
                handled = self.command_manager.handle_command(content)
                if handled:
                    return False, ""
                
                self.terminal.print_thinking()
                
                model_future = self.executor.submit(
                    self.model.get_response, content
                )
                
                if self.command_handler:
                    response, response_type = self.command_handler.process_input(content)
                    if response_type in ["command", "error"]:
                        if not model_future.done():
                            model_future.cancel()
                        self.terminal.print_response(response, "system" if response_type == "command" else "error")
                        self.input_queue.task_done()
                        return
                
                try:
                    response, model_name = model_future.result(timeout=60)
                    self.terminal.print_response(response, model_name)
                    if (t == 'voice' or self.state['voice_active']) and hasattr(self, 'tts'):
                        self.tts.speak(response)
                except concurrent.futures.TimeoutError:
                    self.terminal.print_error("Timeout esperando respuesta del modelo")
                except Exception as e:
                    self.terminal.print_error(f"Error del modelo: {e}")
            
            self.input_queue.task_done()
            
        except Empty:
            pass
        except Exception as e:
            self._handle_critical_error(f"Error processing input: {str(e)}")

    def run(self):
        m = threading.Thread(target=self._system_monitor, daemon=True)
        m.start()
        p = threading.Thread(target=self._process_inputs_loop, daemon=True)
        p.start()
        
        self.terminal.print_header("Operating System")
        self.terminal.print_status("Jarvis Text Interface - Escribe 'help' para ver los comandos")
        
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
    except Exception as e:
        jarvis._shutdown_system()
        logging.error(f"Fatal error: {e}")
