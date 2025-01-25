import sys
import os
import logging
from typing import Optional, List, Tuple

class TerminalManager:
    def __init__(self):
        self.COLORS = {
            'GREEN': '\033[92m',
            'RED': '\033[91m',
            'BLUE': '\033[94m',
            'CYAN': '\033[96m',
            'YELLOW': '\033[93m',
            'RESET': '\033[0m',
            'BOLD': '\033[1m'
        }

        self.STATES = {
            'LISTENING': f"{self.COLORS['GREEN']}🟢{self.COLORS['RESET']}",
            'IDLE': f"{self.COLORS['RED']}🔴{self.COLORS['RESET']}",
            'THINKING': f"{self.COLORS['BLUE']}💭{self.COLORS['RESET']}"
        }

    def setup_logging(self):
        """Configura el sistema de logging"""
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            filename="logs/jarvis.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )
        
        # Silenciar logs innecesarios
        logging.getLogger("alsa").setLevel(logging.ERROR)
        logging.getLogger("jack").setLevel(logging.ERROR)
        logging.getLogger("pulse").setLevel(logging.ERROR)

    def list_audio_devices(self) -> List[Tuple[int, dict]]:
        """Lista los dispositivos de audio disponibles"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            
            print("\nDispositivos de audio disponibles:")
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    devices.append((i, device_info))
                    print(f"[{i}] {device_info['name']}")
                    print(f"    Canales: {device_info['maxInputChannels']}")
                    print(f"    Tasa de muestreo: {int(device_info['defaultSampleRate'])}Hz")
            
            p.terminate()
            return devices
            
        except Exception as e:
            logging.error(f"Error listando dispositivos: {e}")
            return []

    def select_audio_device(self) -> Optional[int]:
        """Maneja la selección de dispositivo de audio"""
        devices = self.list_audio_devices()
        
        if not devices:
            self.print_error("No se encontraron dispositivos de audio.")
            return None
            
        while True:
            try:
                device_index = input("\nSelecciona el número del dispositivo a usar (Enter para el predeterminado): ").strip()
                
                if not device_index:
                    return None
                    
                device_index = int(device_index)
                if any(d[0] == device_index for d in devices):
                    return device_index
                else:
                    self.print_error("Índice de dispositivo inválido. Intenta de nuevo.")
            except ValueError:
                self.print_error("Por favor ingresa un número válido.")

    def print_error(self, message: str):
        """Imprime mensajes de error con formato"""
        print(f"{self.COLORS['RED']}Error:{self.COLORS['RESET']} {message}")

    def print_success(self, message: str):
        """Imprime mensajes de éxito con formato"""
        print(f"{self.COLORS['GREEN']}✓{self.COLORS['RESET']} {message}")

    def print_audio_help(self):
        """Muestra ayuda para problemas de audio"""
        print("\nPosibles soluciones para problemas de audio:")
        print("1. Instalar dependencias: sudo apt-get install python3-pip python3-pyaudio")
        print("2. Instalar ALSA: sudo apt-get install libasound2-dev portaudio19-dev")
        print("3. Verificar permisos de audio: sudo usermod -a -G audio $USER")
        print("4. Reiniciar el servidor de audio: pulseaudio -k && pulseaudio --start")

    def handle_command(self, command: str, manager, tts, trigger) -> bool:
        """Maneja comandos especiales del sistema"""
        if command.lower() in ["salir", "exit"]:
            return False
        elif command.lower() == "config mic":
            new_dev = self.select_audio_device()
            if new_dev is not None:
                try:
                    trigger.reconfigure(device_index=new_dev)
                    self.print_success("Micrófono reconfigurado.")
                except Exception as e:
                    self.print_error(f"Error reconfigurando micrófono: {e}")
        return True

    def clear_line(self):
        """Limpia la línea actual en la terminal"""
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()

    def show_prompt(self, state: str = 'IDLE'):
        """Muestra el prompt con el estado actual"""
        return f"{self.STATES[state]} > "

    def print_thinking(self):
        """Muestra el estado de procesamiento"""
        self.clear_line()
        sys.stdout.write(f"{self.STATES['THINKING']} Procesando...")
        sys.stdout.flush()
        print()  # Solo un salto de línea

    def print_listening(self):
        """Muestra el estado de escucha"""
        print(f"\n{self.STATES['LISTENING']} Escuchando...")

    def print_jarvis_response(self, message: str):
        """Formatea y muestra la respuesta de Jarvis"""
        print(f"{self.COLORS['CYAN']}Jarvis:{self.COLORS['RESET']} {message}")

    def print_user_message(self, message: str):
        """Formatea y muestra el mensaje del usuario"""
        print(message)

    def print_welcome(self):
        """Muestra el mensaje de bienvenida"""
        print("\n" + "="*50)
        print("Jarvis está listo!")
        print("Teclea algo o di 'Hey Jarvis' para activarlo.")
        print("Escribe 'config mic' para cambiar micrófono.")
        print("Presiona Ctrl+C para salir")
        print("="*50 + "\n")

    def print_goodbye(self):
        """Muestra mensaje de despedida"""
        print(f"\n{self.COLORS['CYAN']}¡Hasta luego!{self.COLORS['RESET']}")

    def get_input(self, state: str = 'IDLE') -> str:
        """Obtiene input del usuario con el prompt apropiado"""
        try:
            user_input = input(f"{self.STATES[state]} > ").strip()
            if user_input:
                # No añadir línea extra después del input
                pass
            return user_input
        except (EOFError, KeyboardInterrupt):
            return ""
