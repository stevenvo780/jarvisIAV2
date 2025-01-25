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

# Añadir el directorio raíz al path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

# Configuración inicial del entorno
os.environ.update({
    'PYTORCH_ENABLE_MPS_FALLBACK': '1',
    'PYTHONWARNINGS': 'ignore'
})

# Importaciones
from utils.error_handler import setup_logging, handle_errors, AudioError, ModelError
from modules.terminal_manager import TerminalManager
from modules.llm.model_manager import ModelManager
from modules.voice import SpeechRecognition, TTSManager
from modules.system_monitor import SystemMonitor
from modules.voice.audio_config import AudioConfig
from modules.text.text_handler import TextHandler

# Configurar logging
setup_logging()

class Jarvis:
    def __init__(self):
        self.terminal = TerminalManager()
        self.input_queue = Queue()
        self.audio_init_queue = Queue()
        self.text_mode = False
        
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
            # Iniciar el audio en segundo plano
            self._start_audio_initialization()
            # Iniciar en modo texto mientras se configura el audio
            self._initialize_text_mode()
        except Exception as e:
            self.terminal.print_error(f"Error en inicialización: {e}")
            sys.exit(1)

    def _start_audio_initialization(self):
        """Inicia la inicialización del audio en segundo plano"""
        self.audio_init_thread = threading.Thread(
            target=self._async_audio_init,
            daemon=True
        )
        self.audio_init_thread.start()

    def _async_audio_init(self):
        """Inicialización asíncrona del sistema de audio"""
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
            
            # Señalizar éxito
            self.state['audio_initialized'] = True
            self.state['voice_active'] = True
            self.terminal.print_success("Sistema de voz iniciado correctamente")
            
        except Exception as e:
            self.state['voice_active'] = False
            self.state['audio_initialized'] = False
            self.terminal.print_warning(f"Fallback a modo texto: {str(e)}")
            logging.error(f"Error inicializando audio: {e}")

    def _initialize_text_mode(self):
        """Inicialización del modo texto"""
        if not self.text_handler:
            self.text_handler = TextHandler(
                terminal_manager=self.terminal,
                input_queue=self.input_queue,
                state=self.state
            )
            self.terminal.print_success("Modo texto disponible")

    def _initialize_system(self):
        """Inicializa componentes del sistema"""
        self.terminal.print_header("Iniciando Sistema Jarvis")
        load_dotenv()
        self.model = ModelManager()
        self.terminal.print_success(
            "Sistema iniciado en modo " + 
            ("voz" if self.state['voice_active'] else "texto")
        )

    def _setup_signal_handlers(self):
        """Configura manejadores de señales del sistema"""
        signal.signal(signal.SIGINT, self._graceful_shutdown)
        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def _graceful_shutdown(self, signum=None, frame=None):
        """Maneja el apagado ordenado del sistema"""
        self.state['running'] = False
        self.terminal.print_warning("\nRecibida señal de apagado...")

    def _voice_input_handler(self):
        """Maneja la entrada por voz"""
        while self.state['running'] and self.state['voice_active']:
            try:
                text = self.speech.listen_and_recognize()
                if text:
                    self.input_queue.put(('voice', text))
            except Exception as e:
                self._handle_critical_error(f"Error en voz: {str(e)}")
                self.state['voice_active'] = False
                break
            time.sleep(0.1)

    def _start_service_threads(self):
        """Inicia los hilos de servicio"""
        threads = [
            threading.Thread(target=self._system_monitor, daemon=True)
        ]
        
        # El hilo de voz solo se inicia si el audio se inicializó correctamente
        if self.state['audio_initialized'] and self.state['voice_active']:
            threads.append(
                threading.Thread(target=self._voice_input_handler, daemon=True)
            )
        
        # Iniciar el manejador de texto
        if self.text_handler:
            self.text_handler.start()
        
        for thread in threads:
            thread.start()
            
        return threads


    def _system_monitor(self):
        """Monitorea el estado del sistema"""
        while self.state['running']:
            try:
                health_status = self.system_monitor.check_system_health()
                
                if all(health_status.values()):
                    self.state['error_count'] = 0
                else:
                    self.state['error_count'] += 1
                    failed_systems = [k.replace('_ok', '') for k, v in health_status.items() if not v]
                    self.terminal.print_warning(
                        f"Alerta: Sistemas con problemas: {', '.join(failed_systems)}"
                    )
                    logging.warning(f"Sistemas comprometidos: {failed_systems}")
                
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error en monitor: {str(e)}")

    def _process_inputs(self):
        """Procesa las entradas de la cola"""
        while self.state['running']:
            try:
                input_type, content = self.input_queue.get(timeout=0.5)
                
                # Procesamiento de consultas
                self.terminal.print_thinking()
                response = self.model.get_response(content)
                self.terminal.print_response(response)
                
                if input_type == 'voice' or self.state['voice_active']:
                    self.tts.speak(response)
                    
                self.input_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self._handle_critical_error(f"Error procesando entrada: {str(e)}")


    def _handle_critical_error(self, message: str):
        """Maneja errores críticos"""
        logging.critical(message)
        self.terminal.print_error(message)
        self.state['error_count'] += 1
        
        if self.state['error_count'] >= self.state['max_errors']:
            self.terminal.print_error("Límite de errores alcanzado")
            self._graceful_shutdown()

    def run(self):
        """Bucle principal de ejecución"""
        try:
            # Iniciar hilos
            threads = self._start_service_threads()
            
            # Bucle principal
            self.terminal.print_header("Sistema Operativo")
            self._process_inputs()
            
            # Esperar finalización
            for thread in threads:
                thread.join(timeout=2)
                
        finally:
            self._shutdown_system()

    def _shutdown_system(self):
        """Procedimiento de apagado ordenado"""
        self.terminal.print_status("\nApagando sistema...")
        
        try:
            if self.text_handler:
                self.text_handler.stop()
            if hasattr(self, 'tts'):
                self.tts.cleanup()
            if hasattr(self, 'speech'):
                self.speech.cleanup()
            self.terminal.print_goodbye()
        except Exception as e:
            logging.error(f"Error en apagado: {str(e)}")
        finally:
            os._exit(0)

if __name__ == "__main__":
    jarvis = Jarvis()
    try:
        jarvis.run()
    except KeyboardInterrupt:
        print("\nRecibida señal de apagado...")
    finally:
        jarvis._shutdown_system()