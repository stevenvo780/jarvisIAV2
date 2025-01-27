import re
import speech_recognition as sr
import warnings
import os
import json
import logging
import time
from typing import Optional, Tuple, Dict
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
        logging.info("Audio Handler initialized")
        if self.terminal:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')

    def _setup_recognizer(self) -> sr.Recognizer:
        r = sr.Recognizer()
        r.energy_threshold = 3500
        r.dynamic_energy_threshold = True
        r.pause_threshold = 1.0
        r.phrase_threshold = 0.5
        r.non_speaking_duration = 0.8
        return r

    def _setup_microphone(self) -> sr.Microphone:
        m = sr.Microphone(device_index=None)
        with m as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        return m

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

    def cleanup(self):
        self.running = False
        self.mic_state['is_active'] = False
        if self.terminal:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Off')

    def listen_audio_once(self, timeout=5, phrase_timeout=3) -> str:
        if self.terminal:
            self.terminal.update_prompt_state('LISTENING', '👂 Listening...')
        c = self.speech_config['adaptive']
        t = c['base_timeout']
        try:
            with self.mic as source:
                if time.time() - self.mic_state['last_successful'] > 20:
                    if self.terminal:
                        self.terminal.update_prompt_state('CALIBRATING', '⚡ Calibrating...')
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.mic_state['is_active'] = True
                d = self.recognizer.listen(source, timeout=t, phrase_time_limit=None)
                while True:
                    try:
                        if self.terminal:
                            self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                        p = self.recognizer.recognize_google(d, language='es-ES')
                        if len(p) > 0:
                            self._adjust_thresholds(len(p) / 20)
                            t = min(c['max_timeout'], t + c['timeout_increment'])
                            try:
                                x = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)
                                d = self._combine_audio_data(d, x)
                            except sr.WaitTimeoutError:
                                break
                    except sr.UnknownValueError:
                        break
                final_text = self.recognizer.recognize_google(d, language='es-ES')
                self.mic_state['last_successful'] = time.time()
                self.mic_state['consecutive_failures'] = 0
                if self.terminal:
                    self.terminal.print_voice_detected(final_text)
                return final_text.lower()
        except Exception as e:
            logging.error(f"Error in listen_audio_once: {e}")
            self.mic_state['consecutive_failures'] += 1
            if self.terminal:
                self.terminal.update_prompt_state('ERROR', '❌ Error')
            return ""
        finally:
            self.mic_state['is_active'] = False
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')

    def listen_for_trigger(self, trigger_word="jarvis") -> Tuple[bool, str]:
        try:
            with self.mic as source:
                self.recognizer.energy_threshold = 3000
                a = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                t = self.recognizer.recognize_google(a, language='es-ES').lower()
                p = re.compile(rf'\b{re.escape(trigger_word.lower())}\b')
                if p.search(t):
                    c = p.sub('', t).strip()
                    c = ' '.join(c.split())
                    if self.terminal:
                        self.terminal.update_prompt_state('TRIGGERED', '🎯 Trigger detected')
                        if c:
                            self.terminal.print_voice_detected(c)
                            return True, c
                        else:
                            extra = self.listen_audio_once()
                            return True, extra
                return False, ""
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return False, ""
        except Exception as e:
            logging.debug(f"Error in listen_for_trigger: {e}")
            return False, ""

    def listen_command(self) -> str:
        try:
            if self.terminal:
                self.terminal.update_prompt_state('LISTENING', '👂 Waiting for command...')
            self.audio_effects.play('listening')
            with self.mic as source:
                self.recognizer.energy_threshold = 4000
                a = self.recognizer.listen(source, timeout=5, phrase_time_limit=7)
                if self.terminal:
                    self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                t = self.recognizer.recognize_google(a, language='es-ES')
                if t:
                    if self.terminal:
                        self.terminal.print_voice_detected(t)
                    return t.lower()
        except Exception as e:
            logging.error(f"Error in listen_command: {e}")
        finally:
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')
        return ""
