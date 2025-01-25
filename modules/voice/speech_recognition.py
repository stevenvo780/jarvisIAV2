import speech_recognition as sr
import whisper
import numpy as np
import torch
import logging
from typing import Optional, Tuple
from utils.error_handler import AudioError

class SpeechRecognition:
    def __init__(self, terminal, language: str = "es", device: str = "cpu"):
        self.terminal = terminal
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.model = self._load_whisper_model(device)
        self._initialize_microphone()

    def _load_whisper_model(self, device: str) -> whisper.Whisper:
        """Carga el modelo de Whisper"""
        try:
            self.terminal.print_status("Cargando modelo de reconocimiento...")
            model = whisper.load_model("base")
            model.to(device)
            self.terminal.print_success("Modelo de reconocimiento cargado")
            return model
        except Exception as e:
            raise AudioError(f"Error cargando modelo Whisper: {e}")

    def _initialize_microphone(self) -> None:
        """Inicializa el micrófono con manejo de errores"""
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.terminal.print_status("Calibrando micrófono...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            self.terminal.print_success("Micrófono configurado")
        except Exception as e:
            self.terminal.print_error(f"Error con micrófono: {e}")
            self._try_manual_selection()

    def _try_manual_selection(self) -> None:
        """Permite selección manual del micrófono"""
        try:
            devices = sr.Microphone.list_microphone_names()
            self.terminal.print_status("\nMicrófonos disponibles:")
            for idx, name in enumerate(devices):
                print(f"[{idx}] {name}")
            
            idx = int(input("\nSeleccione número de micrófono: "))
            self.microphone = sr.Microphone(device_index=idx)
            
        except Exception as e:
            raise AudioError(f"No se pudo inicializar micrófono: {e}")

    def listen_and_recognize(self, timeout: int = 5) -> Optional[str]:
        """Escucha y reconoce voz usando Whisper"""
        if not self.microphone:
            return None
            
        try:
            with self.microphone as source:
                self.terminal.print_status("Escuchando...")
                audio = self.recognizer.listen(source, timeout=timeout)
                self.terminal.print_status("Procesando audio...")
                
                # Convertir audio a formato numpy para Whisper
                audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
                
                # Reconocimiento con Whisper
                result = self.model.transcribe(
                    audio_data, 
                    language=self.language,
                    fp16=torch.cuda.is_available()
                )
                
                text = result["text"].strip()
                if text:
                    self.terminal.print_success(f"Reconocido: {text}")
                    return text
                    
        except Exception as e:
            logging.error(f"Error en reconocimiento: {e}")
            return None

    def cleanup(self):
        """Limpia recursos"""
        if self.microphone:
            self.microphone.__exit__(None, None, None)
        if hasattr(self, 'model'):
            del self.model
        torch.cuda.empty_cache()