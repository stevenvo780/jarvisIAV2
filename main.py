#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
import signal
from queue import Queue, Empty
from dotenv import load_dotenv

# Añadir el directorio raíz al path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

# Configuración inicial del entorno
os.environ.update({
    'PYTORCH_ENABLE_MPS_FALLBACK': '1',
    'PYTHONWARNINGS': 'ignore',
    'PULSE_LATENCY_MSEC': '30',
    'PULSE_TIMEOUT': '5000',
    'SDL_AUDIODRIVER': 'pulseaudio'
})

# Importaciones
from utils.error_handler import setup_logging, handle_errors, AudioError, ModelError
from modules.terminal_manager import TerminalManager
from modules.llm.model_manager import ModelManager
from modules.voice import AudioEngine, VoiceTrigger, TTSManager

# Configurar logging
setup_logging()

class Jarvis:
    def __init__(self):
        self.terminal = TerminalManager()
        self.input_queue = Queue()
        self.text_mode = False
        
        self.state = {
            'running': True,
            'voice_active': True,
            'error_count': 0,
            'max_errors': 5
        }

        try:
            self._setup_signal_handlers()
            self._init_audio_subsystem()
            self._initialize_system()
        except AudioError as e:
            self.terminal.print_warning(f"Iniciando en modo texto: {e}")
            self.text_mode = True
            self.state['voice_active'] = False
            self._initialize_system()
        except Exception as e:
            self.terminal.print_error(f"Error en inicialización: {e}")
            sys.exit(1)

    def _init_audio_subsystem(self):
        """Inicializa el subsistema de audio"""
        self._check_audio_permissions()
        self.audio_engine = AudioEngine()
        if self.state['voice_active']:
            self.tts = TTSManager()
            self.voice_trigger = VoiceTrigger(self.terminal)

    def _initialize_system(self):
        """Inicializa componentes del sistema"""
        self.terminal.print_header("Iniciando Sistema Jarvis")
        load_dotenv()
        self.model = ModelManager()
        
        self.terminal.print_success(
            "Sistema iniciado en modo " + 
            ("voz" if self.state['voice_active'] else "texto")
        )

    @handle_errors(error_type=Exception, log_message="Error en inicialización", terminal=True)
    def _initialize_system(self):
        """Inicializa todos los componentes del sistema"""
        self.terminal.print_header("Iniciando Sistema Jarvis")
        
        load_dotenv()
        
        # Inicializar componentes base
        self.model = ModelManager()
        
        # Inicializar audio si está disponible
        if self.state['voice_active'] and self.audio_engine:
            self.tts = TTSManager()
        else:
            self.tts = None
            
        self.terminal.print_success(
            "Sistema iniciado en modo " + 
            ("voz" if self.state['voice_active'] else "texto")
        )

    def _init_audio_subsystem(self):
        """Inicializa el subsistema de audio con validación"""
        try:
            # Verificar permisos y estado del sistema de audio
            self._check_audio_permissions()
            
            # Configurar variables de entorno para audio
            os.environ.update({
                'PULSE_LATENCY_MSEC': '30',
                'PULSE_TIMEOUT': '5000',
                'SDL_AUDIODRIVER': 'pulseaudio'
            })
            
            self.audio_engine = AudioEngine()
            self.terminal.print_success("Sistema de audio iniciado correctamente")
            
        except Exception as e:
            raise AudioError(f"Error en subsistema de audio: {e}")

    def _check_audio_permissions(self):
        """Verifica permisos de audio"""
        if not os.access('/dev/snd', os.R_OK | os.W_OK):
            raise AudioError(
                "Sin permisos de audio. Ejecute: sudo usermod -a -G audio $USER"
            )

    def _setup_signal_handlers(self):
        """Configura manejadores de señales del sistema"""
        signal.signal(signal.SIGINT, self._graceful_shutdown)
        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def _graceful_shutdown(self, signum=None, frame=None):
        """Maneja el apagado ordenado del sistema"""
        self.state['running'] = False
        self.terminal.print_warning("\nRecibida señal de apagado...")

    @handle_errors(error_type=AudioError, log_message="Error en subsistema de audio", terminal=True)
    def _configure_audio_subsystem(self):
        """Configura y verifica el subsistema de audio"""
        self.terminal.print_status("Configurando audio...")
        
        with AudioManager.suppress_output():
            if not AudioManager.setup_audio_system():
                raise AudioError("No se pudo configurar el sistema de audio")
            
            # Esperar a que los servicios de audio estén listos
            time.sleep(2)
        
        self.terminal.print_success("Subsistema de audio configurado")

    @handle_errors(error_type=ModelError, log_message="Error en modelo de lenguaje", terminal=True)
    def _initialize_core_components(self):
        """Inicializa los componentes principales"""
        try:
            self.terminal.print_status("Configurando reconocimiento de voz...")
            device_index = self.terminal.select_audio_device()
            self.voice_trigger = VoiceTrigger(
                terminal=self.terminal,
                wake_word="Hey Jarvis",
                language="es-ES",
                energy_threshold=4000,
                device_index=device_index
            )

            self.terminal.print_status("Cargando modelo de lenguaje...")
            self.model = ModelManager()

            self.terminal.print_status("Inicializando TTS...")
            self.tts = TTSManager()

        except Exception as e:
            self.terminal.print_error(f"Error en inicialización de componentes: {str(e)}")
            raise

    def _check_system_dependencies(self):
        """Verifica dependencias del sistema"""
        self.terminal.print_status("Verificando dependencias...")
        required = ['ffmpeg', 'python3', 'pip3']
        missing = []
        
        for cmd in required:
            if os.system(f'which {cmd} > /dev/null 2>&1') != 0:
                missing.append(cmd)
        
        if missing:
            self.terminal.print_error(f"Dependencias faltantes: {', '.join(missing)}")
            self._show_install_instructions(missing)
            raise RuntimeError("Dependencias faltantes")
            
        self.terminal.print_success("Todas las dependencias están instaladas")

    def _show_install_instructions(self, missing):
        """Muestra instrucciones de instalación para dependencias faltantes"""
        instructions = {
            'ffmpeg': "sudo apt install ffmpeg",
            'python3': "https://www.python.org/downloads/",
            'pip3': "sudo apt install python3-pip"
        }
        
        self.terminal.print_warning("Instrucciones de instalación:")
        for dep in missing:
            if dep in instructions:
                self.terminal.print_info(f"{dep}: {instructions[dep]}")

    def _start_service_threads(self):
        """Inicia los hilos de servicio"""
        threads = [
            threading.Thread(target=self._keyboard_input_handler, daemon=True),
            threading.Thread(target=self._voice_input_handler, daemon=True),
            threading.Thread(target=self._system_monitor, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
            
        return threads

    def _keyboard_input_handler(self):
        """Maneja la entrada por teclado"""
        while self.state['running']:
            try:
                user_input = input(self.terminal.get_prompt()).strip()
                if user_input:
                    self.input_queue.put(('keyboard', user_input))
            except (EOFError, KeyboardInterrupt):
                self.state['running'] = False
            except Exception as e:
                self._handle_critical_error(f"Error en teclado: {str(e)}")

    def _voice_input_handler(self):
        """Maneja la entrada por voz"""
        while self.state['running'] and self.state['voice_active']:
            try:
                self.audio_engine.listen(self._handle_voice_input)
            except Exception as e:
                self._handle_critical_error(f"Error en voz: {str(e)}")
                self.state['voice_active'] = False
                break

    def _handle_voice_input(self, audio_data):
        """Procesa entrada de voz"""
        self.input_queue.put(('voice', audio_data))

    def _system_monitor(self):
        """Monitorea el estado del sistema"""
        while self.state['running']:
            try:
                # Verificar uso de recursos
                if self._check_system_health():
                    self.state['error_count'] = 0
                else:
                    self.state['error_count'] += 1
                    
                # Reiniciar servicios caídos
                self._restart_failed_services()
                
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error en monitor: {str(e)}")

    def _process_inputs(self):
        """Procesa las entradas de la cola"""
        while self.state['running']:
            try:
                input_type, content = self.input_queue.get(timeout=0.5)
                self._handle_input(input_type, content)
                self.input_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self._handle_critical_error(f"Error procesando entrada: {str(e)}")

    def _handle_input(self, input_type: str, content: str):
        """Maneja diferentes tipos de entrada"""
        try:
            # Comandos del sistema
            if content.lower() in ['exit', 'salir', 'quit']:
                self.state['running'] = False
                return
                
            if content.lower() == 'voz off':
                self.state['voice_active'] = False
                self.terminal.print_success("Modo voz desactivado")
                return
                
            if content.lower() == 'voz on':
                self.state['voice_active'] = True
                self.terminal.print_success("Modo voz activado")
                return
                
            # Procesamiento de consultas
            self.terminal.print_thinking()
            response = self.model.get_response(content)
            self.terminal.print_response(response)
            
            if input_type == 'voice' or self.state['voice_active']:
                self.tts.speak(response)
                
        except Exception as e:
            self._handle_critical_error(f"Error procesando {input_type}: {str(e)}")

    def _check_system_health(self) -> bool:
        """Verifica el estado de salud del sistema"""
        # Implementar chequeos reales aquí
        return True

    def _restart_failed_services(self):
        """Reinicia servicios caídos"""
        pass  # Implementar lógica de reinicio

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
            if self.tts:
                self.tts.cleanup()
                
            if self.voice_trigger:
                self.voice_trigger.cleanup()
                
            self.terminal.print_goodbye()
        except Exception as e:
            logging.error(f"Error en apagado: {str(e)}")
        finally:
            os._exit(0)

if __name__ == "__main__":
    jarvis = Jarvis()
    try:
        jarvis.run()  # Cambiado de main_loop() a run()
    except KeyboardInterrupt:
        print("\nRecibida señal de apagado...")
    finally:
        jarvis._shutdown_system()  # Cambiado de cleanup() a _shutdown_system()