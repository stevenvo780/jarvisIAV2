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
from modules.actions import Actions
from modules.system.command_manager import CommandManager

setup_logging()

class Jarvis:
    def __init__(self):
        self.state = {
            'running': True,
            'voice_active': False,
            'listening_active': False,
            'error_count': 0,
            'max_errors': 5
        }
        self.input_queue = Queue()
        self.executor = ThreadPoolExecutor(max_workers=2)
        load_dotenv()
        try:
            self.terminal = TerminalManager()
            self.terminal.print_header("Starting Jarvis System")
            self.system_monitor = SystemMonitor()
            self.terminal.print_success("System monitor initialized")
            self._initialize_tts()
            self.terminal.print_success("TTS initialized")
            self.storage = StorageManager()
            self.terminal.print_success("Storage initialized")
            self.audio_effects = AudioEffects()
            self.terminal.print_success("Audio effects initialized")
            
            self.text_handler = None
            self.command_manager = None
            self.model_manager = None
            self.actions = None
            self._initialize_llm()
            self.terminal.print_success("System initialized")
            self._async_audio_init()
            self.terminal.print_success("Voice system initialized")
            self._initialize_actions()
            self.terminal.print_success("Actions initialized")
            self.text_handler = TextHandler(
                terminal_manager=self.terminal,
                input_queue=self.input_queue,
                actions=self.actions
            )
            self.terminal.print_success("Text handler initialized")
            
            self.terminal.print_header("Initializing Jarvis")
            self.audio_effects.play('startup')
        except Exception as e:
            self.audio_effects.play('error')
            self.terminal.print_error(f"Initialization error: {e}")
            sys.exit(1)


    def _initialize_actions(self):
        try:
            self.actions = Actions(
                tts=self.tts,
                state=self.state,
                audio_effects=self.audio_effects
            )
        except Exception as e:
            raise e

    def _initialize_tts(self):
        try:
            self.tts = TTSManager()
            self.state['voice_active'] = True
        except Exception as e:
            self.terminal.print_warning(f"TTS initialization error: {e}")
            self.state['voice_active'] = False
            raise e

    def _initialize_llm(self):
        try:
            self.model_manager = ModelManager(storage_manager=self.storage, tts=self.tts)
            self.terminal.print_success("Core system initialized")
            self.command_manager = CommandManager(
                model_manager=self.model_manager,
            )
        except Exception as e:
            raise e

    def _async_audio_init(self):
        try:
            logging.info("Iniciando inicialización de audio...")
            self.audio = AudioHandler(
                terminal_manager=self.terminal,
                tts=self.tts,
                state=self.state,
                input_queue=self.input_queue
            )
            self.state['listening_active'] = True
            pass
        except Exception as e:
            self.terminal.print_warning(f"⌨️ Text mode only: {e}")
            self.state['listening_active'] = False
            self.terminal.print_error(f"Error inicializando audio: {e}")
            self.audio_effects.play('error')
            logging.error(f"Audio init error: {e}")

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

                if self.actions:
                    message, is_command = self.actions.handle_command(content)
                    if is_command == True:
                        if message:
                            self.terminal.print_response(message, "system")
                        self.terminal.update_prompt_state('NEUTRAL')
                        self.input_queue.task_done()
                        return
                
                self.terminal.update_prompt_state('PROCESSING')
                if self.command_manager:
                    response, response_type = self.command_manager.process_input(content)
                    if response and response_type in ["command", "error"]:
                        self.terminal.print_response(response, "system" if response_type == "command" else "error")
                        self.input_queue.task_done()
                        
                        self.terminal.update_prompt_state('SPEAKING')
                        self.tts.speak(response)
                        self.terminal.update_prompt_state('NEUTRAL')
                        return
                
                self.terminal.update_prompt_state('THINKING')
                try:
                    response, model_name = self.model_manager.get_response(content)
                    self.terminal.print_response(response, model_name)
                    if (t == 'voice' or self.state['voice_active']) and hasattr(self, 'tts'):
                        self.tts.speak(response)
                except Exception as e:
                    self.terminal.print_error(f"Error del modelo: {e}")
                self.terminal.update_prompt_state('NEUTRAL')
            
            self.input_queue.task_done()
            
        except Empty:
            pass
        except Exception as e:
            self._handle_critical_error(f"Error processing input: {str(e)}")

    def _process_inputs_loop(self):
        while self.state['running']:
            self._process_inputs()
            time.sleep(0.1)
        self._shutdown_system()

    def _shutdown_system(self, signum=None, frame=None):
        self.terminal.print_status("Shutting down...")
        try:
            self.state['running'] = False
            self.terminal.print_warning("Shutdown signal received...")
            
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join(timeout=2)
            if hasattr(self, 'processor_thread'):
                self.processor_thread.join(timeout=2)
            if hasattr(self, 'text_handler'):
                self.text_handler.stop()
            if hasattr(self, 'tts'):
                self.tts.cleanup()
            if hasattr(self, 'model_manager'):
                del self.model_manager
            if hasattr(self, 'audio'):
                self.audio.cleanup()
            self.terminal.print_goodbye()
            
        except Exception as e:
            logging.error(f"Shutdown error: {str(e)}")
        finally:
            os._exit(0)

    def run(self):
        self.monitor_thread = threading.Thread(target=self._system_monitor, daemon=True)
        self.processor_thread = threading.Thread(target=self._process_inputs_loop, daemon=True)
        self.monitor_thread.start()
        self.processor_thread.start()
        
        self.terminal.print_header("Operating System")
        self.terminal.print_status("Jarvis Text Interface - Escribe 'help' para ver los comandos")
        
        self.text_handler.run_interactive()

if __name__ == "__main__":
    jarvis = Jarvis()
    try:
        jarvis.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        jarvis._shutdown_system()
        logging.error(f"Fatal error: {e}")
