import re
import time
import speech_recognition as sr
import warnings
import os
import json
import logging
import whisper
import threading
from typing import Tuple, Dict
from src.utils.audio_utils import AudioEffects

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
        self.recognizer = None
        self.mic_state = {
            'is_active': False,
            'consecutive_failures': 0
        }
        self.device_index = None
        self.mic = None
        self._setup_audio_system()
        self.trigger_thread = None

    def _setup_audio_system(self):
        self.device_index = self.config['audio'].get('device_index')
        self.mic = sr.Microphone(device_index=self.device_index)
        self.mic_context = self.mic.__enter__()
        self.recognizer = self._setup_recognizer('base')
        self._adjust_for_noise()
        logging.info("Audio system initialized successfully")

    def _adjust_for_noise(self):
        try:
            self.recognizer.adjust_for_ambient_noise(self.mic_context, duration=0.5)
            time.sleep(0.2)
        except Exception as e:
            logging.error(f"Error adjusting noise: {e}")

    def _setup_recognizer(self, mode='base'):
        self.recognizer = sr.Recognizer()
        config = self.config['audio'] if mode == 'base' else self.config['speech_modes'][mode]
        self.recognizer.energy_threshold = config['energy_threshold']
        self.recognizer.dynamic_energy_threshold = config.get('dynamic_energy', False)
        self.recognizer.pause_threshold = config['pause_threshold']
        self.recognizer.phrase_threshold = config['phrase_threshold']
        self.recognizer.non_speaking_duration = config['non_speaking_duration']
        return self.recognizer

    def cleanup(self):
        if hasattr(self, 'mic_context'):
            self.mic.__exit__(None, None, None)
        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'mic'):
            del self.mic
        if hasattr(self, 'recognizer'):
            del self.recognizer
        self.running = False

    def _transcribe_audio(self, audio_data):
        temp_wav = os.path.join(os.getcwd(), "temp_audio.wav")
        try:
            with open(temp_wav, "wb") as f:
                f.write(audio_data.get_wav_data())
            result = self.model.transcribe(
                temp_wav,
                language="es",
                initial_prompt="Jarvis asistente virtual",
                no_speech_threshold=0.05,
                temperature=0.0,
                best_of=5,
                beam_size=5,
                patience=1,
                fp16=False
            )
            return result["text"].strip().lower()
        except Exception as e:
            logging.error(f"Transcription error: {e}")
            return ""
        finally:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)

    def listen_for_trigger(self, trigger_word="jarvis"):
        try:
            self._setup_recognizer('short_phrase')
            self._adjust_for_noise()
            audio_data = self.recognizer.listen(
                self.mic_context,
                timeout=self.config['speech_modes']['short_phrase']['operation_timeout'],
                phrase_time_limit=3
            )
            text = self._transcribe_audio(audio_data)
            logging.debug(f"Trigger heard: {text}")
            if re.search(rf'\b{re.escape(trigger_word)}\b', text, re.IGNORECASE):
                cleaned_text = re.sub(rf'\b{re.escape(trigger_word)}\b', '', text, flags=re.IGNORECASE).strip()
                return True, cleaned_text if cleaned_text else self.listen_command()
        except Exception as e:
            logging.debug(f"Trigger error: {e}")
            self._adjust_for_noise()
        return False, ""

    def listen_command(self):
        try:
            self._setup_recognizer('command_phrase')
            self._adjust_for_noise()
            self.terminal.update_prompt_state('LISTENING', '👂 Waiting for command...')
            self.audio_effects.play('listening')
            audio_data = self.recognizer.listen(
                self.mic_context,
                timeout=None,
                phrase_time_limit=5
            )
            self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
            text = self._transcribe_audio(audio_data)
            if text and len(text.split()) >= self.config['speech_modes']['adaptive']['min_command_length']:
                self.terminal.print_voice_detected(text)
                return text
        except Exception as e:
            logging.error(f"Command error: {e}")
        finally:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')
        return ""

    def run_trigger_listener(self):
        while self.running:
            triggered, cleaned_text = self.listen_for_trigger()
            if triggered:
                command = cleaned_text if cleaned_text else self.listen_command()

    def start_trigger_listener(self):
        if not self.trigger_thread:
            self.trigger_thread = threading.Thread(target=self.run_trigger_listener, daemon=True)
            self.trigger_thread.start()
