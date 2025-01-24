import speech_recognition as sr
import logging
import time
import warnings
import pyaudio
import os

class VoiceTrigger:
    def __init__(self, wake_word="Hey Jarvis", language="es-ES"):
        # Silenciar warnings de ALSA y JACK
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        warnings.filterwarnings("ignore", category=UserWarning)
        logging.getLogger('speechrecognition').setLevel(logging.ERROR)
        
        self.wake_word = wake_word.lower()
        self.language = language
        self.recognizer = sr.Recognizer()
        
        try:
            # Usar específicamente el micrófono USB
            self.microphone = sr.Microphone(device_index=4)  # USB Microphone
            with self.microphone as source:
                print("Calibrando micrófono... (silencio por favor)")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.recognizer.energy_threshold = 4000
                self.recognizer.dynamic_energy_threshold = True
                logging.info("Micrófono USB inicializado correctamente")
                print("¡Listo! Puedes hablar.")
        except Exception as e:
            logging.error(f"Error al inicializar micrófono USB: {str(e)}")
            self.microphone = None

    def listen_for_activation(self):
        if not self.microphone:
            return False
            
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                text = self.recognizer.recognize_google(audio, language=self.language)
                return self.wake_word.lower() in text.lower()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return False
        except Exception as e:
            logging.error(f"Error en detección: {str(e)}")
            return False

    def capture_query(self):
        if not self.microphone:
            return ""
            
        try:
            with self.microphone as source:
                print("Escuchando...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio, language=self.language)
                return text
        except (sr.UnknownValueError, sr.RequestError) as e:
            logging.error(f"Error en captura de consulta: {str(e)}")
            return ""