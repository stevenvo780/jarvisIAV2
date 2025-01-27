import re
import speech_recognition as sr
import warnings
import os
import json
import logging
import time
import whisper
from typing import Tuple, Dict
from src.modules.command_manager import CommandManager
from src.utils.audio_utils import AudioEffects
from src.utils.error_handler import AudioError

warnings.filterwarnings("ignore")

class AudioHandler:
    def __init__(self, terminal_manager, tts, state):
        config_path = os.path.join('src', 'config', 'audio_config.json')
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.terminal = terminal_manager
        self.audio_effects = AudioEffects()
        self.running = True
        self.command_manager = CommandManager(tts=tts, state=state)
        self.model = whisper.load_model("base")
        self.recognizer = self._setup_recognizer()
        self.mic = self._setup_microphone()
        self.mic_state = self._initialize_mic_state()
        self.speech_config = {
            'short_phrase': {
                'timeout': 5,
                'phrase_timeout': 3,
                'energy_threshold': 4000
            },
            'long_phrase': {
                'timeout': 10,
                'phrase_timeout': 15,
                'energy_threshold': 3500
            },
            'adaptive': {
                'base_timeout': 5,
                'max_timeout': 15,
                'timeout_increment': 0.5,
                'energy_adjustment': 100
            }
        }
        self.max_retries = 3
        self.retry_delay = 1.0
        self.last_trigger_time = 0
        self.min_trigger_interval = 0.5  # Reducido a 0.5s ya que Whisper es más preciso
        logging.info("Audio Handler initialized")
        if self.terminal:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')

    def _setup_recognizer(self) -> sr.Recognizer:
        r = sr.Recognizer()
        r.energy_threshold = 1000  # Umbral bajo, solo para detectar voz vs silencio
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8
        return r

    def _setup_microphone(self) -> sr.Microphone:
        device_index = self.config['audio'].get('device_index')
        return sr.Microphone(device_index=device_index)

    def _get_mic_instance(self) -> sr.Microphone:
        """Crear una nueva instancia de micrófono para cada operación"""
        return sr.Microphone(device_index=self.config['audio'].get('device_index'))

    def _initialize_mic_state(self) -> Dict:
        return {
            'is_active': False,
            'last_successful': 0,
            'consecutive_failures': 0,
            'waiting_for_command': False,
            'speech_duration': 0,
            'last_energy_level': 0
        }

    def _adjust_thresholds(self, d: float) -> None:
        if d > 5:
            self.recognizer.pause_threshold = min(1.5, 0.8 + (d * 0.05))
            self.recognizer.phrase_threshold = min(0.8, 0.3 + (d * 0.03))
            self.recognizer.non_speaking_duration = min(1.2, 0.5 + (d * 0.04))

    def _reset_mic(self) -> bool:
        try:
            if self.mic_state['consecutive_failures'] > 3:
                logging.info("Resetting microphone due to consecutive failures")
                self.mic = sr.Microphone(device_index=self.config['audio']['device_index'])
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.mic_state['consecutive_failures'] = 0
                return True
            return False
        except Exception as e:
            logging.error(f"Error resetting microphone: {e}")
            return False

    def _combine_audio_data(self, audio1, audio2):
        return audio1

    def _transcribe_audio(self, audio_data) -> str:
        try:
            temp_wav = "temp_audio.wav"
            with open(temp_wav, "wb") as f:
                f.write(audio_data.get_wav_data())
            
            result = self.model.transcribe(
                temp_wav, 
                language="es",
                initial_prompt="Jarvis asistente virtual",
                fp16=False
            )
            
            os.remove(temp_wav)
            return result["text"].strip().lower()
        except Exception as e:
            logging.error(f"Error en transcripción: {e}")
            return ""

    def cleanup(self):
        self.running = False
        self.mic_state['is_active'] = False
        if self.terminal:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Off')

    def listen_audio_once(self, timeout=5, phrase_timeout=3) -> str:
        if self.terminal:
            self.terminal.update_prompt_state('LISTENING', '👂 Listening...')
        
        try:
            mic = self._get_mic_instance()
            with mic as source:
                self.mic_state['is_active'] = True
                
                audio_data = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=phrase_timeout
                )
                
                if self.terminal:
                    self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                
                text = self._transcribe_audio(audio_data)
                if text:
                    if self.terminal:
                        self.terminal.print_voice_detected(text)
                    return text.lower()
                return ""

        except Exception as e:
            logging.error(f"Error in listen_audio_once: {e}")
            return ""
        finally:
            self.mic_state['is_active'] = False
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')

    def listen_for_trigger(self, trigger_word="jarvis") -> Tuple[bool, str]:
        if time.time() - self.last_trigger_time < self.min_trigger_interval:
            return False, ""
            
        try:
            mic = self._get_mic_instance()
            with mic as source:
                audio_data = self.recognizer.listen(
                    source, 
                    timeout=3,
                    phrase_time_limit=3
                )
                
                text = self._transcribe_audio(audio_data)
                
                if trigger_word.lower() in text.lower():
                    self.last_trigger_time = time.time()
                    remaining_text = text.lower().replace(trigger_word.lower(), '').strip()
                    
                    if self.terminal:
                        self.terminal.update_prompt_state('TRIGGERED', '🎯 Trigger detected')
                    
                    if remaining_text:
                        return True, remaining_text
                    
                    return True, self.listen_audio_once()
                
                return False, ""
                
        except Exception as e:
            logging.debug(f"Error in listen_for_trigger: {e}")
            return False, ""

    def listen_command(self) -> str:
        try:
            if self.terminal:
                self.terminal.update_prompt_state('LISTENING', '👂 Waiting for command...')
            self.audio_effects.play('listening')
            
            # Usar nueva instancia de micrófono
            mic = self._get_mic_instance()
            with mic as source:
                self.recognizer.energy_threshold = 4000
                audio_data = self.recognizer.listen(source, timeout=5, phrase_time_limit=7)
                
                if self.terminal:
                    self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                
                text = self._transcribe_audio(audio_data)
                if text:
                    if self.terminal:
                        self.terminal.print_voice_detected(text)
                    return text
                    
        except Exception as e:
            logging.error(f"Error in listen_command: {e}")
        finally:
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')
        return ""
