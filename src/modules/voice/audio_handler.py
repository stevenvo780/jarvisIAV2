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
        
        self.max_retries = self.config['triggers']['max_retries']
        self.retry_delay = self.config['triggers']['retry_delay']
        self.last_trigger_time = 0
        self.min_trigger_interval = self.config['triggers']['min_interval']
        logging.info("Audio Handler initialized")
        self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')

    def _setup_recognizer(self) -> sr.Recognizer:
        r = sr.Recognizer()
        r.energy_threshold = self.config['audio']['energy_threshold']
        r.dynamic_energy_threshold = self.config['audio']['dynamic_energy']
        r.pause_threshold = self.config['audio']['pause_threshold']
        r.phrase_threshold = self.config['audio']['phrase_threshold']
        r.non_speaking_duration = self.config['audio']['non_speaking_duration']
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

    def listen_audio_once(self, timeout=5, phrase_timeout=3) -> str:
        self.terminal.update_prompt_state('LISTENING', '👂 Listening...')
        
        try:
            mic = self._get_mic_instance()
            with mic as source:
                self.mic_state['is_active'] = True
                
                audio_data = self.recognizer.listen(
                    source, 
                    timeout=None
                )
                
                self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                
                text = self._transcribe_audio(audio_data)
                if text:
                    self.terminal.print_voice_detected(text)
                    return text.lower()
                return ""

        except Exception as e:
            logging.error(f"Error in listen_audio_once: {e}")
            return ""
        finally:
            self.mic_state['is_active'] = False
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')

    def listen_for_trigger(self, trigger_word="jarvis") -> Tuple[bool, str]:
        if time.time() - self.last_trigger_time < self.min_trigger_interval:
            return False, ""
            
        try:
            mic = self._get_mic_instance()
            with mic as source:
                self.recognizer.energy_threshold = self.config['speech_modes']['short_phrase']['energy_threshold']
                audio_data = self.recognizer.listen(
                    source, 
                    timeout=self.config['speech_modes']['short_phrase']['timeout'],
                    phrase_time_limit=self.config['speech_modes']['short_phrase']['phrase_timeout']
                )
                
                text = self._transcribe_audio(audio_data)
                
                if trigger_word.lower() in text.lower():
                    self.last_trigger_time = time.time()
                    remaining_text = text.lower().replace(trigger_word.lower(), '').strip()
                    
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
            self.terminal.update_prompt_state('LISTENING', '👂 Waiting for command...')
            self.audio_effects.play('listening')
            
            mic = self._get_mic_instance()
            with mic as source:
                self.recognizer.energy_threshold = self.config['speech_modes']['long_phrase']['energy_threshold']
                self.recognizer.pause_threshold = self.config['speech_modes']['adaptive']['silence_threshold']
                
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                audio_data = self.recognizer.listen(
                    source,
                    timeout=None,
                    phrase_time_limit=self.config['speech_modes']['long_phrase']['phrase_timeout']
                )
                
                self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                
                text = self._transcribe_audio(audio_data)
                if text:
                    self.terminal.print_voice_detected(text)
                    return text
                    
        except Exception as e:
            logging.error(f"Error in listen_command: {e}")
        finally:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')
        return ""
