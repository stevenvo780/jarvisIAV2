import re
import speech_recognition as sr
import warnings
import os
import json
import logging
import time
import whisper
from typing import Tuple, Dict
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
        
        self.model = whisper.load_model("small")
        self.recognizer = self._setup_recognizer()
        self.mic_state = self._initialize_mic_state()
        self._setup_audio_system()
        
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

    def _setup_audio_system(self):
        self.device_index = self.config['audio'].get('device_index')
        self.mic = sr.Microphone(device_index=self.device_index)
        
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logging.info(f"Micrófono calibrado - Umbral: {self.recognizer.energy_threshold}")

    def _initialize_mic_state(self) -> Dict:
        return {
            'is_active': False,
            'last_successful': 0,
            'consecutive_failures': 0,
            'waiting_for_command': False,
            'speech_duration': 0,
            'last_energy_level': 0
        }

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

    def cleanup(self):
        try:
            if hasattr(self, 'model'):
                del self.model
            if hasattr(self, 'mic'):
                del self.mic
            if hasattr(self, 'recognizer'):
                del self.recognizer
            self.running = False
            logging.info("AudioHandler recursos liberados")
        except Exception as e:
            logging.error(f"Error en cleanup: {e}")

    def _transcribe_audio(self, audio_data) -> str:
        if not self.running:
            return ""
            
        temp_wav = os.path.join(os.getcwd(), "temp_audio.wav")
        try:
            with open(temp_wav, "wb") as f:
                f.write(audio_data.get_wav_data())
            
            result = self.model.transcribe(
                temp_wav, 
                language="es",
                initial_prompt="Jarvis asistente virtual",
                fp16=False,
                temperature=0.3
            )
            
            return result["text"].strip().lower()
        except Exception as e:
            logging.error(f"Error en transcripción: {e}")
            return ""
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except:
                    pass

    def listen_audio_once(self, timeout=5, phrase_timeout=3) -> str:
        self.terminal.update_prompt_state('LISTENING', '👂 Listening...')
        try:
            with self.mic as source:
                self.mic_state['is_active'] = True
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_timeout)
                return self._transcribe_audio(audio)
        except Exception as e:
            logging.error(f"Error en captura de audio: {e}")
            return ""
        finally:
            self.mic_state['is_active'] = False

    def listen_for_trigger(self, trigger_word="jarvis") -> Tuple[bool, str]:
            
        try:
            with self.mic as source:
                self.recognizer.energy_threshold = self.config['speech_modes']['short_phrase']['energy_threshold']
                self.recognizer.pause_threshold = self.config['speech_modes']['short_phrase']['pause_threshold']
                audio_data = self.recognizer.listen(
                    source,
                    timeout=None,
                )
                
                text = self._transcribe_audio(audio_data)
                print(f"Texto reconocido: {text}")
                if trigger_word.lower() in text.lower():
                    remaining_text = text.lower().replace(trigger_word.lower(), '').strip()
                    
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
            
            with self.mic as source:
                self.recognizer.energy_threshold = self.config['speech_modes']['long_phrase']['energy_threshold']
                self.recognizer.pause_threshold = self.config['speech_modes']['adaptive']['silence_threshold']
                
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                audio_data = self.recognizer.listen(
                    source,
                    timeout=None,
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
