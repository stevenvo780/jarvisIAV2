import speech_recognition as sr
import warnings
import ctypes
import os
import sys
import json
from contextlib import contextmanager

class SimplifiedAudioHandler:
    def __init__(self, config_path="config/audio_config.json", terminal_manager=None):
        self.terminal = terminal_manager
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
                # Añadir beep antes de escuchar
                if hasattr(self.terminal, 'beep'):
                    self.terminal.beep()
                if self.terminal:
                    self.terminal.update_prompt_state('LISTENING', '👂')
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
                    
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=5)
                    
                    if self.terminal:
                        self.terminal.update_prompt_state('PROCESSING', '⚡')
                        self.terminal.print_thinking()
                    
                    try:
                        text = self.recognizer.recognize_google(audio, language=self.config['audio']['language'])
                        if self.terminal:
                            self.terminal.print_voice_detected(text)
                        return text.lower()
                    except sr.UnknownValueError:
                        if self.terminal:
                            self.terminal.update_prompt_state('ERROR', "❌ No se entendió el audio")
                    except sr.RequestError as e:
                        if self.terminal:
                            self.terminal.update_prompt_state('ERROR', f"❌ Error en Speech Recognition: {e}")
            except Exception as e:
                if self.terminal:
                    self.terminal.update_prompt_state('ERROR', str(e))
            finally:
                # Añadir beep al terminar
                if hasattr(self.terminal, 'beep'):
                    self.terminal.beep()
                if self.terminal:
                    self.terminal.update_prompt_state('IDLE', '')
        return None

    def listen_for_trigger(self, trigger_word="jarvis"):
        with self.suppress_stderr():
            try:
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=2)
                text = self.recognizer.recognize_google(audio, language=self.config['audio']['language'])
                if trigger_word.lower() in text.lower():
                    # Simplificar actualización de estado
                    if self.terminal:
                        self.terminal.update_prompt_state('LISTENING')
                    return True
                return False
            except:
                return False

    def listen_command(self):
        import time
        time.sleep(0.5)
        with self.suppress_stderr():
            try:
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio, language=self.config['audio']['language'])
                if text and self.terminal:
                    self.terminal.print_voice_detected(text)
                return text.lower()
            except:
                if self.terminal:
                    self.terminal.update_prompt_state('ERROR')
                return None

    def cleanup(self):
        self.running = False
