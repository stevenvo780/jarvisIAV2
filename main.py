import sys
import logging
import time
import warnings
import os
from dotenv import load_dotenv
from modules.speech_recognition import VoiceTrigger
from modules.model_manager import ModelManager

def check_audio_setup():
    try:
        # Silenciar warnings de ALSA
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        warnings.filterwarnings("ignore", category=UserWarning)
        logging.getLogger('alsa').setLevel(logging.ERROR)
        
        import pyaudio
        p = pyaudio.PyAudio()
        
        # Buscar específicamente el micrófono USB
        usb_mic = None
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if "USB" in device_info['name']:
                usb_mic = device_info
                print("\nMicrófono USB encontrado:")
                print(f"[{i}] {device_info['name']}")
                print(f"    Canales: {device_info['maxInputChannels']}")
                print(f"    Tasa de muestreo: {int(device_info['defaultSampleRate'])}Hz")
                break
        
        p.terminate()
        
        if not usb_mic:
            print("\nError: No se encontró el micrófono USB.")
            return False
            
        print("\nSistema de audio inicializado correctamente.")
        return True
        
    except Exception as e:
        logging.error(f"Error al inicializar audio: {str(e)}")
        print("\nError: Problemas con el sistema de audio.")
        print("Posibles soluciones:")
        print("1. Instalar dependencias: sudo apt-get install python3-pyaudio")
        print("2. Instalar ALSA: sudo apt-get install libasound2-dev")
        print("3. Verificar permisos de audio: sudo usermod -a -G audio $USER")
        print("4. Reiniciar el servidor de audio: pulseaudio -k && pulseaudio --start")
        return False

def main():
    # Cargar variables de entorno
    load_dotenv()
    
    print("Iniciando Jarvis... Presiona Ctrl+C para salir.")
    logging.info("Jarvis is starting up.")

    if not check_audio_setup():
        sys.exit(1)

    trigger = VoiceTrigger(wake_word="Hey Jarvis", language="es-ES")
    manager = ModelManager(priority=["local", "google", "openai"], timeout_in_seconds=5)

    try:
        while True:
            time.sleep(0.1)  # Evitar saturación de CPU
            
            if trigger.listen_for_activation():
                print("¡Activado! ¿En qué puedo ayudarte?")
                user_query = trigger.capture_query()
                
                if not user_query:
                    print("No pude entender tu consulta. ¿Podrías repetirla?")
                    continue
                    
                if user_query.lower() in ["salir", "adiós", "terminar"]:
                    print("¡Hasta luego!")
                    break
                    
                response = manager.get_response(user_query)
                print("Jarvis:", response)
                
    except KeyboardInterrupt:
        print("\n¡Hasta luego!")
        sys.exit(0)

if __name__ == "__main__":
    main()