# speech_recognition.py
import os
import logging
import numpy as np
import torch
from .audio_utils import AudioError

try:
    os.environ['PYTHONPATH'] = ''
    import whisper
except ImportError as e:
    logging.error(f"Whisper import error: {e}")
    raise ImportError("Check whisper installation")

class SpeechRecognition:
    def __init__(self, language="es", device=None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.language = language
        self.device = device
        try:
            self.model = whisper.load_model("base", device=device)
        except Exception as e:
            logging.error(f"Error loading Whisper: {e}")
            raise RuntimeError("Whisper model not loaded")

    def transcribe_audio(self, audio_array):
        try:
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)
            r = self.model.transcribe(audio_array, language=self.language, fp16=torch.cuda.is_available())
            text = r["text"].strip()
            return text if text else None
        except Exception as e:
            logging.error(f"Transcription error: {e}")
            return None

    def cleanup(self):
        if hasattr(self, 'model'):
            del self.model
        torch.cuda.empty_cache()
