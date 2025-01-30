import time
import speech_recognition as sr
import warnings
import os
import json
import logging
import whisper
import threading
from typing import Tuple
from src.utils.audio_utils import AudioEffects

warnings.filterwarnings("ignore")

class AudioHandler:
    def __init__(self, terminal_manager, tts, state, input_queue):
        self.terminal = terminal_manager
        self.tts = tts
        self.state = state
        self.input_queue = input_queue
        self.audio_effects = AudioEffects()
        self.trigger_word = "Jarvis"
        self.running = True
        self.model = whisper.load_model("small")
        self.recognizer = sr.Recognizer()
        self.mic_lock = threading.Lock()
        config_path = os.path.join('src', 'config', 'audio_config.json')
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.device_index = self.config['audio']['device_index']
        self.mic = sr.Microphone(device_index=self.device_index)
        with self.mic_lock:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_thread.start()

    def _audio_loop(self):
        while self.running:
            text = self._listen_short()
            if not text:
                continue
            is_valid, command = self._validate_trigger(text, self.trigger_word)
            if is_valid:
                if command:
                    self.input_queue.put(('voice', command))
                else:
                    long_text = self._listen_long()
                    if long_text:
                        self.input_queue.put(('voice', long_text))

    def _listen_short(self):
        c = self.config['speech_modes']['short_phrase']
        self._set_recognizer_config(c)
        with self.mic_lock:
            with sr.Microphone(device_index=self.device_index) as source:
                try:
                    audio_data = self.recognizer.listen(
                        source,
                        timeout=c.get('operation_timeout', 3),
                        phrase_time_limit=c.get('phrase_time_limit', 3)
                    )
                except sr.WaitTimeoutError:
                    return ""
        return self._transcribe_audio(audio_data)

    def _listen_long(self):
        c = self.config['speech_modes']['long_phrase']
        self.audio_effects.play('listening')
        self.terminal.update_prompt_state('LISTENING', '👂 Modo escucha extendida...')
        self._set_recognizer_config(c)
        with self.mic_lock:
            with sr.Microphone(device_index=self.device_index) as source:
                try:
                    audio_data = self.recognizer.listen(
                        source,
                        timeout=c.get('operation_timeout'),
                        phrase_time_limit=c.get('phrase_time_limit', 20)
                    )
                except sr.WaitTimeoutError:
                    return ""
        text = self._transcribe_audio(audio_data)
        self.terminal.update_prompt_state('PROCESSING', '⚡ Procesando...')
        return text

    def _set_recognizer_config(self, cfg):
        self.recognizer.energy_threshold = cfg['energy_threshold']
        self.recognizer.dynamic_energy_threshold = cfg.get('dynamic_energy', False)
        self.recognizer.pause_threshold = cfg['pause_threshold']
        self.recognizer.phrase_threshold = cfg['phrase_threshold']
        self.recognizer.non_speaking_duration = cfg['non_speaking_duration']

    def _transcribe_audio(self, audio_data):
        temp_wav = os.path.join(os.getcwd(), "temp_audio.wav")
        try:
            with open(temp_wav, "wb") as f:
                f.write(audio_data.get_wav_data())
            result = self.model.transcribe(
                temp_wav,
                language="es",
                initial_prompt="Jarvis asistente virtual",
                no_speech_threshold=self.config['speech_modes']['adaptive'].get('silence_threshold', 1.5),
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

    def _validate_trigger(self, text: str, trigger_word: str) -> Tuple[bool, str]:
        processed = ' '.join(text.lower().split())
        tw = trigger_word.lower()
        if tw not in processed and trigger_word.capitalize() not in processed:
            return False, ""
        cmd = processed
        for variant in [tw, trigger_word.capitalize()]:
            cmd = cmd.replace(variant, '').strip()
        return True, ' '.join(cmd.split())

    def cleanup(self):
        self.running = False
        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'mic'):
            del self.mic
        if hasattr(self, 'recognizer'):
            del self.recognizer
