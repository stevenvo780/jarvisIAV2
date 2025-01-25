import speech_recognition as sr
import logging
import warnings
import os
from typing import Optional
from utils.audio_manager import AudioManager
from utils.error_handler import AudioError

class VoiceTrigger:
    def __init__(self, terminal, wake_word: str = "Hey Jarvis", language: str = "es-ES"):
        self.terminal = terminal
        self.wake_word = wake_word.lower()
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self._initialize_microphone()

    def _initialize_microphone(self) -> None:
        """Inicializa el micrófono con manejo de errores"""
        try:
            with AudioManager.suppress_output():  # Suprimir stderr durante la inicialización
                self.microphone = sr.Microphone()  # Usa micrófono predeterminado
                with self.microphone as source:
                    self.terminal.print_status("Calibrando micrófono...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    self.recognizer.energy_threshold = 4000
            self.terminal.print_success("Micrófono configurado correctamente")
        except Exception as e:
            self.terminal.print_error(f"Error con micrófono predeterminado: {e}")
            self._try_manual_selection()

    def _try_manual_selection(self) -> None:
        """Permite selección manual del micrófono si falla el predeterminado"""
        try:
            devices = sr.Microphone.list_microphone_names()
            self.terminal.print_status("\nMicrófonos disponibles:")
            for idx, name in enumerate(devices):
                print(f"[{idx}] {name}")
            
            idx = int(input("\nSeleccione número de micrófono: "))
            self.microphone = sr.Microphone(device_index=idx)
            with AudioManager.suppress_output(), self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
        except Exception as e:
            raise AudioError(f"No se pudo inicializar ningún micrófono: {e}")

    def listen_for_activation(self) -> bool:
        """Escucha la palabra de activación"""
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
            logging.error(f"Error en detección: {e}")
            return False

    def capture_query(self) -> str:
        """Captura una consulta de voz"""
        if not self.microphone:
            return ""
            
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                return self.recognizer.recognize_google(audio, language=self.language).strip()
        except Exception as e:
            logging.error(f"Error capturando audio: {e}")
            return ""

    def cleanup(self):
        """Limpia recursos"""
        if self.microphone:
            self.microphone.__exit__(None, None, None)