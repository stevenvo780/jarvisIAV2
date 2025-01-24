import sys
import logging
from dotenv import load_dotenv
from modules.speech_recognition import VoiceTrigger
from modules.model_manager import ModelManager

def check_audio_setup():
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        p.terminate()
        return True
    except Exception as e:
        logging.error(f"Error al inicializar audio: {str(e)}")
        print("Error: No se pudo inicializar el sistema de audio.")
        print("Por favor, revise INSTALL.md para instrucciones de instalación.")
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

    while True:
        if trigger.listen_for_activation():
            user_query = trigger.capture_query()
            response = manager.get_response(user_query)
            print("Jarvis:", response)

if __name__ == "__main__":
    main()