import sys
import os
import logging
from typing import Optional, List, Tuple

class TerminalManager:
    def __init__(self):
        self._setup_colors()
        self._setup_states()
        self.setup_logging()

    def _setup_colors(self):
        """Configura los códigos de color ANSI"""
        self.COLORS = {
            'GREEN': '\033[92m',
            'RED': '\033[91m',
            'BLUE': '\033[94m',
            'CYAN': '\033[96m',
            'YELLOW': '\033[93m',
            'RESET': '\033[0m',
            'BOLD': '\033[1m'
        }

    def _setup_states(self):
        """Configura los estados visuales del sistema"""
        self.STATES = {
            'LISTENING': f"{self.COLORS['GREEN']}🟢{self.COLORS['RESET']}",
            'IDLE': f"{self.COLORS['RED']}🔴{self.COLORS['RESET']}",
            'THINKING': f"{self.COLORS['BLUE']}💭{self.COLORS['RESET']}"
        }

    def setup_logging(self):
        """Configura el sistema de logging silenciando logs innecesarios"""
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            filename="logs/jarvis.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )
        
        # Silenciar logs específicos de sistemas de audio
        for lib in ['alsa', 'jack', 'pulse', 'libav']:
            logging.getLogger(lib).setLevel(logging.CRITICAL)
            logging.getLogger(lib).propagate = False

    def list_audio_devices(self) -> List[Tuple[int, dict]]:
        """Lista dispositivos de audio con manejo de errores silencioso"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            
            for i in range(p.get_device_count()):
                with self._suppress_output():
                    device_info = p.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        devices.append((i, device_info))
            
            p.terminate()
            return devices
            
        except Exception as e:
            logging.error(f"Error listando dispositivos: {e}")
            return []

    def select_audio_device(self) -> Optional[int]:
        """Interfaz de selección de dispositivo de audio"""
        devices = self.list_audio_devices()
        
        if not devices:
            self.print_error("No se encontraron dispositivos de entrada.")
            return None
            
        self._print_devices(devices)
        
        while True:
            try:
                device_index = input(f"\n{self.STATES['IDLE']} Selecciona dispositivo (Enter para predeterminado): ").strip()
                if not device_index:
                    return None
                
                return self._validate_device_index(int(device_index), devices)
                
            except ValueError:
                self.print_error("Ingrese un número válido.")

    def _print_devices(self, devices: List[Tuple[int, dict]]):
        """Muestra los dispositivos disponibles con formato"""
        print("\nDispositivos de entrada disponibles:")
        for idx, dev in devices:
            print(f"[{idx}] {dev['name']}")
            print(f"    Canales: {dev['maxInputChannels']}")
            print(f"    Tasa de muestreo: {int(dev['defaultSampleRate'])}Hz")

    def _validate_device_index(self, index: int, devices: List[Tuple[int, dict]]) -> int:
        """Valida el índice del dispositivo seleccionado"""
        if any(d[0] == index for d in devices):
            return index
        self.print_error("Índice inválido.")
        raise ValueError

    class _suppress_output:
        """Context manager para suprimir salida temporalmente"""
        def __enter__(self):
            self._original_stderr = os.dup(2)
            self._devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(self._devnull, 2)
        
        def __exit__(self, *args):
            os.dup2(self._original_stderr, 2)
            os.close(self._devnull)

    # Métodos de visualización mejorados
    def print_error(self, message: str):
        """Muestra mensajes de error formateados"""
        sys.stdout.write(f"\r{self.COLORS['RED']}✖{self.COLORS['RESET']} {message}\n")

    def print_success(self, message: str):
        """Muestra mensajes de éxito formateados"""
        sys.stdout.write(f"\r{self.COLORS['GREEN']}✓{self.COLORS['RESET']} {message}\n")

    def print_jarvis_response(self, message: str):
        """Formatea respuestas del asistente"""
        sys.stdout.write(f"\r{self.COLORS['CYAN']}🤖 Jarvis:{self.COLORS['RESET']} {message}\n")

    def print_thinking(self):
        """Muestra indicador de procesamiento"""
        sys.stdout.write(f"\r{self.STATES['THINKING']} Procesando...")
        sys.stdout.flush()

    def print_listening(self):
        """Muestra indicador de escucha activa"""
        sys.stdout.write(f"\r{self.STATES['LISTENING']} Escuchando...")
        sys.stdout.flush()

    def clear_display(self):
        """Limpia la línea actual de la terminal"""
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()

    def print_welcome(self):
        """Muestra mensaje de bienvenida"""
        self.clear_display()
        print(f"{self.COLORS['CYAN']}{'='*50}")
        print("   🎙️  Jarvis - Asistente de Voz Inteligente  ")
        print(f"{'='*50}{self.COLORS['RESET']}")
        print("Comandos disponibles:")
        print("- 'config mic': Configurar dispositivo de entrada")
        print("- 'voz on/off': Activar/desactivar reconocimiento por voz")
        print(f"- {self.COLORS['YELLOW']}Ctrl+C para salir{self.COLORS['RESET']}\n")

    def print_goodbye(self):
        """Muestra mensaje de despedida"""
        self.clear_display()
        print(f"\n{self.COLORS['CYAN']}🛑 Sistema finalizado.{self.COLORS['RESET']}")

    def print_header(self, message: str):
        """Encabezado para mensajes importantes."""
        sys.stdout.write(f"\n{self.COLORS['BLUE']}=== {message} ==={self.COLORS['RESET']}\n")

    def print_status(self, message: str):
        """Mensaje de estado."""
        sys.stdout.write(f"{self.COLORS['YELLOW']}[STATUS]{self.COLORS['RESET']} {message}\n")

    def print_warning(self, message: str):
        """Muestra mensajes de advertencia formateados"""
        sys.stdout.write(f"\r{self.COLORS['YELLOW']}⚠{self.COLORS['RESET']} {message}\n")

    def get_prompt(self, prompt: str = "User: "):
        """Obtiene entrada del usuario."""
        return input(prompt)

    def print_response(self, message: str):
        """Muestra respuestas generales del sistema de manera formateada"""
        self.clear_display()
        lines = message.split('\n')
        for line in lines:
            sys.stdout.write(f"\r{self.COLORS['CYAN']}│{self.COLORS['RESET']} {line}\n")
        sys.stdout.flush()