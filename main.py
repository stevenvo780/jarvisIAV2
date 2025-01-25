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
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Jarvis AI Assistant')
    parser.add_argument('--chat', action='store_true', help='Iniciar en modo chat')
    args = parser.parse_args()

    # Cargar variables de entorno
    load_dotenv()
    
    # Configurar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Iniciando Jarvis... Presiona Ctrl+C para salir.")
    logging.info("Jarvis is starting up.")
    
    # 1. Inicializar sistema de audio con más tolerancia a errores
    initialize_audio_system()
    time.sleep(1)  # Dar tiempo a que el sistema de audio se estabilice
    
    # 2. Se intenta inicializar con el micrófono por defecto
    print("\nIntentando inicializar el micrófono por defecto...")
    trigger = None
    default_device_index = None

    try:
        trigger = VoiceTrigger(
            wake_word="Hey Jarvis",
            language="es-ES",
            energy_threshold=4000,
            device_index=default_device_index
        )
        print("Micrófono predeterminado inicializado correctamente.")
    except Exception as ex:
        logging.error(f"Error al inicializar el micrófono predeterminado: {ex}")
        print("No se pudo inicializar el micrófono predeterminado. Se procederá a la selección manual.")
        
        while trigger is None:
            try:
                device_index = select_audio_device()
                print(f"\nIntentando con dispositivo: {device_index if device_index is not None else 'predeterminado'}")
                trigger = VoiceTrigger(
                    wake_word="Hey Jarvis", 
                    language="es-ES", 
                    energy_threshold=4000,
                    device_index=device_index
                )
            except Exception as e:
                print(f"Error al inicializar dispositivo: {e}")
                print("¿Deseas intentar con otro dispositivo? (s/n)")
                if input().lower() != 's':
                    print("Saliendo...")
                    sys.exit(1)

    # Manager y TTS 
    manager = ModelManager(priority=["local", "google", "openai"], timeout_in_seconds=5)
    tts = TTSManager()

    if args.chat:
        print("\nIniciando en modo chat...")
        chat_mode(manager, tts)
        return

    print("\n" + "="*50)
    print("Jarvis está listo!")
    print("Teclea algo o di 'Hey Jarvis' para activarlo.")
    print("Escribe 'config mic' para cambiar micrófono.")
    print("Presiona Ctrl+C para salir")
    print("="*50 + "\n")

    while True:
        try:
            # Mostrar 'Cargando...' en lugar del prompt si está ocupado
            if manager.is_busy():
                print("\rCargando...     ", end="", flush=True)
                time.sleep(0.1)
                continue
            
            # Cuando no está ocupado, se puede leer input normalmente
            user_input = input("🔴 > ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["salir", "exit"]:
                break
            elif user_input.lower() == "config mic":
                new_dev = select_audio_device()
                if new_dev is not None:
                    trigger = VoiceTrigger(
                        wake_word="Hey Jarvis",
                        language="es-ES",
                        energy_threshold=4000,
                        device_index=new_dev
                    )
                    print("Micrófono reconfigurado.")
                continue
            
            # Enviar query al manager, hablar la respuesta
            print(f"Tu: {user_input}")
            response = manager.get_response(user_input)
            print("Jarvis:", response)
            tts.speak(response)
            
            # Verificar activación por voz sólo si no está ocupado
            if trigger and not manager.is_busy():
                if trigger.listen_for_activation():
                    voice_query = trigger.capture_query()
                    if voice_query:
                        print(f"\nTu: {voice_query}")
                        response = manager.get_response(voice_query)
                        print("Jarvis:", response)
                        tts.speak(response)
            
        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error en el bucle principal: {e}")
            time.sleep(0.1)

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error crítico: {e}")
        sys.exit(1)