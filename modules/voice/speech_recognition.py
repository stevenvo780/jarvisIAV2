import speech_recognition as sr
import logging
import time
import warnings
import pyaudio
import os

class VoiceTrigger:
    def __init__(self, wake_word="Hey Jarvis", language="es-ES",
                 energy_threshold=4000, dynamic_energy=True,
                 pause_threshold=0.8, device_index=None):
        # Silenciar warnings de ALSA y JACK
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        warnings.filterwarnings("ignore", category=UserWarning)
        logging.getLogger('alsa').setLevel(logging.ERROR)
        logging.getLogger('jack').setLevel(logging.ERROR)
        logging.getLogger('speechrecognition').setLevel(logging.ERROR)
        
        self.wake_word = wake_word.lower()
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        try:
            # Inicializar micrófono
            print(f"Intentando inicializar micrófono con índice: {device_index}")
            self.microphone = sr.Microphone(device_index=device_index)
            
            # Configurar el reconocedor con manejo de errores más robusto
            retries = 3
            for attempt in range(retries):
                try:
                    with self.microphone as source:
                        print("Calibrando micrófono... Por favor, guarda silencio.")
                        self.recognizer.adjust_for_ambient_noise(source, duration=1)
                        self.recognizer.energy_threshold = energy_threshold
                        self.recognizer.dynamic_energy_threshold = dynamic_energy
                        self.recognizer.pause_threshold = pause_threshold
                        print("¡Calibración completada!")
                        break
                except Exception as e:
                    if attempt == retries - 1:
                        raise
                    print(f"Reintento {attempt + 1} de calibración...")
                    time.sleep(1)
            
            self.continuous_mode = False
            logging.info(f"Micrófono inicializado correctamente (índice: {device_index})")
            
        except Exception as e:
            logging.error(f"Error al inicializar micrófono: {str(e)}")
            raise  # Re-lanzar la excepción para que main() pueda manejarla

    def toggle_continuous_mode(self):
        self.continuous_mode = not self.continuous_mode
        return self.continuous_mode

    def listen_for_activation(self):
        if self.continuous_mode:
            return True
            
        if not self.microphone:
            return False
            
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                text = self.recognizer.recognize_google(audio, language=self.language)
                return self.wake_word.lower() in text.lower()
        except sr.WaitTimeoutError:
            return False
        except sr.UnknownValueError:
            return False
        except Exception as e:
            logging.error(f"Error en detección de wake word: {str(e)}")
            return False

    def capture_query(self):
        if not self.microphone:
            return ""
        try:
            print("Escuchando tu consulta...")  # Eliminamos uso de "\r" y borrado
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio, language=self.language)
                return text.strip()
        except Exception as e:
            logging.error(f"Error en captura de consulta: {str(e)}")
            return ""

    def configure(self, energy_threshold=None, dynamic_energy=None,
                 pause_threshold=None):
        if energy_threshold:
            self.recognizer.energy_threshold = energy_threshold
        if dynamic_energy is not None:
            self.recognizer.dynamic_energy_threshold = dynamic_energy
        if pause_threshold:
            self.recognizer.pause_threshold = pause_threshold