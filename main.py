import sys
import logging
import time
import warnings
import os
import select
import subprocess
import signal
import argparse
from dotenv import load_dotenv
from modules.speech_recognition import VoiceTrigger
from modules.model_manager import ModelManager
from modules.tts_manager import TTSManager
from modules.terminal_manager import TerminalManager

# Configuración más agresiva para suprimir mensajes
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
warnings.filterwarnings("ignore")
logging.getLogger("alsa").setLevel(logging.ERROR)
logging.getLogger("jack").setLevel(logging.ERROR)
logging.getLogger("pulse").setLevel(logging.ERROR)

# Redirigir stderr a /dev/null para mensajes que no se pueden capturar
if not sys.platform.startswith('win'):
    import ctypes
    libc = ctypes.CDLL(None)
    c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')
    libc.fflush(c_stderr)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)

def initialize_audio_system():
    """Inicializa y configura el sistema de audio"""
    try:
        # Intentar reiniciar pulseaudio solo si está instalado
        if os.system('which pulseaudio > /dev/null') == 0:
            subprocess.run(['pulseaudio', '-k'], stderr=subprocess.DEVNULL, check=False)
            time.sleep(1)
            subprocess.run(['pulseaudio', '--start'], stderr=subprocess.DEVNULL, check=False)
            time.sleep(1)
        
        # Intentar restaurar ALSA solo si está instalado
        if os.path.exists('/usr/sbin/alsactl'):
            subprocess.run(['alsactl', 'restore'], stderr=subprocess.DEVNULL, check=False)
        
        return True
    except Exception as e:
        logging.error(f"Error inicializando sistema de audio: {e}")
        return False

def check_audio_setup():
    """Verifica la disponibilidad de micrófonos"""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        
        # Buscar cualquier micrófono disponible
        available_mics = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                available_mics.append((i, device_info))
                print(f"\nMicrófono encontrado:")
                print(f"[{i}] {device_info['name']}")
                print(f"    Canales: {device_info['maxInputChannels']}")
                print(f"    Tasa de muestreo: {int(device_info['defaultSampleRate'])}Hz")
        
        p.terminate()
        
        if not available_mics:
            print("\nError: No se encontró ningún micrófono.")
            return False
            
        print(f"\nSe encontraron {len(available_mics)} dispositivos de entrada.")
        return True
        
    except Exception as e:
        logging.error(f"Error al inicializar audio: {str(e)}")
        print("\nError: Problemas con el sistema de audio.")
        print("Posibles soluciones:")
        print("1. Instalar dependencias: sudo apt-get install python3-pip python3-pyaudio")
        print("2. Instalar ALSA: sudo apt-get install libasound2-dev portaudio19-dev")
        print("3. Verificar permisos de audio: sudo usermod -a -G audio $USER")
        print("4. Reiniciar el servidor de audio: pulseaudio -k && pulseaudio --start")
        return False

def list_audio_devices():
    """Lista todos los dispositivos de audio disponibles"""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        
        print("\nDispositivos de audio disponibles:")
        devices = []
        
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # Solo dispositivos de entrada
                devices.append((i, device_info))
                print(f"[{i}] {device_info['name']}")
                print(f"    Canales: {device_info['maxInputChannels']}")
                print(f"    Tasa de muestreo: {int(device_info['defaultSampleRate'])}Hz")
        
        p.terminate()
        return devices
        
    except Exception as e:
        logging.error(f"Error al listar dispositivos: {str(e)}")
        return []

def select_audio_device():
    """Permite al usuario seleccionar un dispositivo de audio"""
    devices = list_audio_devices()
    
    if not devices:
        print("\nError: No se encontraron dispositivos de audio.")
        return None
        
    while True:
        try:
            device_index = input("\nSelecciona el número del dispositivo a usar (Enter para el predeterminado): ").strip()
            
            if not device_index:  # Usar dispositivo predeterminado
                return None
                
            device_index = int(device_index)
            if any(d[0] == device_index for d in devices):
                return device_index
            else:
                print("Índice de dispositivo inválido. Intenta de nuevo.")
        except ValueError:
            print("Por favor ingresa un número válido.")

def chat_mode(manager, tts):
    print("\nModo de chat activado. Comandos disponibles:")
    print("- 'salir': Salir del chat")
    print("- 'voz on/off': Activar/desactivar respuestas por voz")
    print("- 'limpiar': Limpiar historial de conversación")
    print("- 'historial': Mostrar historial de conversación")
    print("- 'exportar': Exportar historial a archivo\n")
    
    use_voice = False
    
    while True:
        try:
            user_input = input("Tu: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["salir", "adiós", "terminar", "exit"]:
                break
            elif user_input.lower() == "voz on":
                use_voice = True
                print("Respuestas por voz activadas")
                continue
            elif user_input.lower() == "voz off":
                use_voice = False
                print("Respuestas por voz desactivadas")
                continue
            elif user_input.lower() == "limpiar":
                manager.clear_context()
                print("Historial de conversación limpiado")
                continue
            elif user_input.lower() == "historial":
                for entry in manager.get_conversation_history():
                    role = "Tu:" if entry["role"] == "user" else "Jarvis:"
                    print(f"{role} {entry['content']}")
                continue
            elif user_input.lower() == "exportar":
                history = manager.get_conversation_history()
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                export_file = f"chat_history_{timestamp}.txt"
                
                with open(export_file, 'w', encoding='utf-8') as f:
                    for entry in history:
                        f.write(f"Tu: {entry['query']}\n")
                        f.write(f"Jarvis: {entry['response']}\n\n")
                print(f"Historial exportado a {export_file}")
                continue
                
            response = manager.get_response(user_input)
            print("Jarvis:", response)
            
            if use_voice:
                tts.speak(response)
                
        except Exception as e:
            logging.error(f"Error en modo chat: {e}")
            print("Ocurrió un error. Intenta de nuevo.")

def signal_handler(signum, frame):
    print("\n¡Hasta luego!")
    sys.exit(0)

def process_keyboard_input(current_input: str, cursor_pos: int, manager: ModelManager) -> tuple:
    """Procesa la entrada de teclado y retorna el input actualizado y posición del cursor"""
    if manager.is_busy():  # Si está procesando, ignorar entrada
        return current_input, cursor_pos, False
        
    char = sys.stdin.read(1)
    
    if char == '\n':
        return current_input, cursor_pos, True
    elif char == '\x7f':  # Backspace
        if cursor_pos > 0:
            current_input = current_input[:-1]
            cursor_pos -= 1
    else:  # Caracteres normales
        current_input += char
        cursor_pos += 1
    
    return current_input, cursor_pos, False

def handle_voice_activation(trigger, manager, tts, current_input: str) -> str:
    """Maneja la activación por voz y retorna el input actual"""
    print("\rEscuchando comando...", end="", flush=True)
    user_query = trigger.capture_query()
    
    if user_query:
        print(f"\nTu: {user_query}")
        response = manager.get_response(user_query)
        print("Jarvis:", response)
        tts.speak(response)
    
    return current_input

def main():
    # Inicializar componentes
    terminal = TerminalManager()
    terminal.setup_logging()
    
    # Cargar configuración y variables de entorno
    load_dotenv()
    
    # Inicializar micrófono
    trigger = None
    while trigger is None:
        try:
            trigger = VoiceTrigger(
                wake_word="Hey Jarvis",
                language="es-ES",
                energy_threshold=4000
            )
            terminal.print_success("Micrófono inicializado correctamente.")
        except Exception as e:
            terminal.print_error(f"Error al inicializar micrófono: {e}")
            if input("¿Intentar con otro dispositivo? (s/n): ").lower() != 's':
                return 1

    # Inicializar componentes principales
    try:
        manager = ModelManager("config/models.json", timeout_in_seconds=5)
    except Exception as e:
        terminal.print_error(f"Error al inicializar el gestor de modelos: {e}")
        return 1

    try:
        tts = TTSManager()
    except Exception as e:
        terminal.print_error(f"Error al inicializar el sistema de voz: {e}")
        return 1
    
    # Mostrar bienvenida
    terminal.print_welcome()

    # Bucle principal
    while True:
        try:
            if manager.is_busy():
                terminal.print_thinking()
                time.sleep(0.1)
                continue
            
            user_input = terminal.get_input('IDLE')
            if not user_input:
                continue
                
            if not terminal.handle_command(user_input, manager, tts, trigger):
                break
            
            terminal.print_thinking()
            response = manager.get_response(user_input)
            terminal.print_jarvis_response(response)
            tts.speak(response)
            
            if trigger and not manager.is_busy():
                if trigger.listen_for_activation():
                    terminal.print_listening()
                    voice_query = trigger.capture_query()
                    if voice_query:
                        response = manager.get_response(voice_query)
                        terminal.print_jarvis_response(response)
                        tts.speak(response)
            
        except KeyboardInterrupt:
            terminal.print_goodbye()
            return 0
        except Exception as e:
            terminal.print_error(f"Error: {e}")
            time.sleep(0.1)

    return 0

if __name__ == "__main__":
    sys.exit(main())