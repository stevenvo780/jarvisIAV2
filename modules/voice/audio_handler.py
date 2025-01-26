import speech_recognition as sr
import warnings
import ctypes
import os
import sys
import json
import logging
import time
from typing import Optional, Tuple
from contextlib import contextmanager
from modules.command_manager import CommandManager
from utils.audio_utils import AudioEffects
from utils.error_handler import AudioError
warnings.filterwarnings("ignore")

class AudioHandler:
    def __init__(self, config_path="config/audio_config.json", terminal_manager=None, tts=None, state=None):
        self.terminal = terminal_manager
        self.audio_effects = AudioEffects()
        try:
            self._load_config(config_path)
            ctypes.CDLL('libasound.so').snd_lib_error_set_handler(None)
            
            devices = sr.Microphone.list_microphone_names()
            if not devices:
                raise AudioError("No se encontraron dispositivos de audio")
                
            if self.config['audio']['device_index'] >= len(devices):
                logging.warning(f"Índice de dispositivo inválido {self.config['audio']['device_index']}, usando default")
                self.config['audio']['device_index'] = None
            
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = self.config['audio']['energy_threshold']
            self.recognizer.dynamic_energy_threshold = self.config['audio']['dynamic_energy']
            self.recognizer.pause_threshold = self.config['audio']['pause_threshold']
            
            self.mic = sr.Microphone(device_index=self.config['audio']['device_index'])
            
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
            self.running = True
            self.command_manager = CommandManager(tts=tts, state=state)
            logging.info("Audio inicializado correctamente")
            
        except Exception as e:
            logging.error(f"Error inicializando audio: {e}")
            raise AudioError(f"Error de inicialización: {e}")

        self.max_retries = 3
        self.retry_delay = 1.0
        self.mic_state = {
            'is_active': False,
            'last_successful': 0,
            'consecutive_failures': 0
        }

    def _load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
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
                if self.terminal:
                    self.terminal.update_prompt_state('LISTENING', '👂')
                    self.audio_effects.play('thinking')
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
                    if self.terminal:
                        self.terminal.update_prompt_state('LISTENING')
                    return True
                return False
            except:
                return False

    def cleanup(self):
        self.running = False
        self.mic_state['is_active'] = False

    def _reset_mic(self) -> bool:
        try:
            if self.mic_state['consecutive_failures'] > 3:
                logging.info("Reiniciando micrófono debido a fallos consecutivos")
                self.mic = sr.Microphone(device_index=self.config['audio']['device_index'])
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.mic_state['consecutive_failures'] = 0
                return True
            return False
        except Exception as e:
            logging.error(f"Error reseteando micrófono: {e}")
            return False

    def _dynamic_timeout_adjustment(self) -> Tuple[float, float]:
        base_timeout = 5
        base_phrase_timeout = 3
        
        if self.mic_state['consecutive_failures'] > 0:
            timeout = min(base_timeout + self.mic_state['consecutive_failures'], 10)
            phrase_timeout = min(base_phrase_timeout + (self.mic_state['consecutive_failures'] * 0.5), 7)
        else:
            timeout = base_timeout
            phrase_timeout = base_phrase_timeout
            
        return timeout, phrase_timeout

    def listen_audio_once(self) -> str:
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            try:
                if self._reset_mic():
                    self.audio_effects.play('ready', volume=0.3)
                
                timeout, phrase_timeout = self._dynamic_timeout_adjustment()
                
                with self.mic as source:
                    if time.time() - self.mic_state['last_successful'] > 30:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    try:
                        self.mic_state['is_active'] = True
                        audio = self.recognizer.listen(
                            source,
                            timeout=timeout,
                            phrase_time_limit=phrase_timeout
                        )
                        
                        text = self.recognizer.recognize_google(
                            audio,
                            language=self.config['audio']['language']
                        )
                        
                        # Éxito en el reconocimiento
                        self.mic_state.update({
                            'last_successful': time.time(),
                            'consecutive_failures': 0
                        })
                        return text.lower()
                        
                    except sr.WaitTimeoutError:
                        last_error = "Timeout esperando audio"
                        self.mic_state['consecutive_failures'] += 1
                    except sr.UnknownValueError:
                        last_error = "No se pudo entender el audio"
                        if attempts == self.max_retries - 1:
                            self.audio_effects.play('error', volume=0.3)
                    except sr.RequestError as e:
                        last_error = f"Error en el servicio de reconocimiento: {e}"
                        
            except Exception as e:
                last_error = str(e)
                logging.error(f"Error en listen_audio_once: {e}")
            finally:
                self.mic_state['is_active'] = False
            
            attempts += 1
            if attempts < self.max_retries:
                time.sleep(self.retry_delay)
                
        if last_error:
            logging.warning(f"Audio recognition failed after {attempts} attempts: {last_error}")
        return ""

    def detect_jarvis_command(self, trigger: str) -> str:
        try:
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE')
                
            recognized_text = self.listen_audio_once()
            if not recognized_text:
                return ""

            if trigger.lower() in recognized_text.lower():
                if self.terminal:
                    self.terminal.update_prompt_state('LISTENING')
                    self.audio_effects.play('command', volume=0.4)
                
                parts = recognized_text.lower().split(trigger.lower(), 1)
                if len(parts) > 1 and parts[1].strip():
                    command = parts[1].strip()
                    if self.terminal:
                        self.terminal.print_voice_detected(command)
                        self.terminal.update_prompt_state('VOICE_IDLE')
                    return command
                
                time.sleep(0.5)  # Pequeña pausa antes de escuchar el comando
                self.audio_effects.play('listening', volume=0.3)
                additional_text = self.listen_audio_once()
                
                if additional_text:
                    if self.terminal:
                        self.terminal.print_voice_detected(additional_text)
                        self.terminal.update_prompt_state('VOICE_IDLE')
                    return additional_text.strip()

            return ""
            
        except Exception as e:
            logging.error(f"Error en detect_jarvis_command: {e}")
            return ""
        finally:
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE')
