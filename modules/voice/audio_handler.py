import speech_recognition as sr
import warnings
import ctypes
import os
import sys
import json
from contextlib import contextmanager

class SimplifiedAudioHandler:
    def __init__(self, config_path="config/audio_config.json"):
        self._load_config(config_path)
        ctypes.CDLL('libasound.so').snd_lib_error_set_handler(None)
        warnings.filterwarnings("ignore")
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.config['audio']['energy_threshold']
        self.recognizer.dynamic_energy_threshold = self.config['audio']['dynamic_energy']
        self.recognizer.pause_threshold = self.config['audio']['pause_threshold']
        
        # Usar directamente el device_index de la configuración
        self.mic = sr.Microphone(device_index=self.config['audio']['device_index'])
        self.running = True

    def _load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error cargando configuración de audio: {e}")
            # Configuración por defecto
            self.config = {
                "audio": {
                    "device_index": 6,
                    "device_name": "USB Microphone",
                    "sample_rate": 48000,
                    "language": "es-ES",
                    "energy_threshold": 4000,
                    "dynamic_energy": True,
                    "pause_threshold": 0.5
                }
            }

    @contextmanager
    def suppress_stderr(self):
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(devnull, 2)
        os.close(devnull)
        try:
            yield
        finally:
            os.dup2(old_stderr, 2)
            os.close(old_stderr)

    def list_devices(self):
        with self.suppress_stderr():
            devices = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(devices):
                print(f"[{idx}] {name}")
        return devices

    def listen(self):
        with self.suppress_stderr():
            try:
                with self.mic as source:
                    print('Ajustando al ruido ambiente...')
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
                    print('Escuchando...')
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=5)
                    
                    try:
                        text = self.recognizer.recognize_google(audio, language=self.config['audio']['language'])
                        return text.lower()
                    except sr.UnknownValueError:
                        print("No se pudo entender el audio")
                    except sr.RequestError as e:
                        print(f"Error en Google Speech Recognition: {e}")
            except Exception as e:
                print(f"Error de audio: {e}")
        return None

    def cleanup(self):
        self.running = False
