# audio_handler.py
import collections
import queue
import sounddevice as sd
import numpy as np
import threading
import logging
import time
from contextlib import contextmanager
import webrtcvad
from .audio_config import AudioConfig
from .audio_utils import AudioError, retry_audio

class AudioEngine:
    def __init__(self, timeout=5, device_index=None):
        self.config = AudioConfig()
        self.device_index = device_index
        self.running = True
        self.audio_queue = queue.Queue()
        self.vad = webrtcvad.Vad(3)
        self.ring_buffer = collections.deque(maxlen=10)
        self.timeout = timeout
        self._init_audio_system()

    @contextmanager
    def _audio_context(self):
        start_time = time.time()
        try:
            if hasattr(sd, '_lib'):
                try:
                    sd._lib.Pa_Terminate()
                except:
                    pass
            while time.time() - start_time < self.timeout:
                try:
                    if not hasattr(sd, '_initialized') or not sd._initialized:
                        sd._initialize()
                    break
                except Exception as e:
                    if time.time() - start_time >= self.timeout:
                        raise AudioError(str(e))
                    time.sleep(0.1)
            yield
        except Exception as e:
            raise AudioError(str(e))
        finally:
            if hasattr(sd, '_lib'):
                try:
                    sd._lib.Pa_Terminate()
                except:
                    pass

    @retry_audio(max_attempts=2)
    def _init_audio_system(self):
        try:
            with self._audio_context():
                self._check_audio_permissions()
                self.devices = self._find_best_devices()
                self._setup_streams()
        except Exception as e:
            logging.error(f"Audio init error: {e}")
            raise AudioError(str(e), recoverable=False)

    def _check_audio_permissions(self):
        try:
            s = sd.InputStream(channels=1, samplerate=16000, blocksize=1024)
            s.start()
            s.stop()
            s.close()
        except Exception as e:
            raise AudioError(str(e))

    def _find_best_devices(self):
        devices = sd.query_devices()
        if self.device_index is not None:
            return {'input': devices[self.device_index], 'output': sd.query_devices(None, 'output')}
        valid_inputs = [d for d in devices if d['max_input_channels'] > 0 and d['default_samplerate'] in [16000, 44100, 48000]]
        valid_outputs = [d for d in devices if d['max_output_channels'] > 0]
        if not valid_inputs or not valid_outputs:
            raise AudioError("No compatible devices")
        return {'input': valid_inputs[0], 'output': valid_outputs[0]}

    def _setup_streams(self):
        profile = self.config.get_current_profile()
        self.stream_config = {
            'samplerate': profile.sample_rate,
            'channels': profile.channels,
            'dtype': np.float32,
            'blocksize': profile.chunk_size,
            'device': (self.devices['input']['index'], self.devices['output']['index'])
        }

    def start_listening(self, wake_word_callback, command_callback):
        self.listener_thread = threading.Thread(
            target=self._audio_listener_loop,
            args=(wake_word_callback, command_callback),
            daemon=True
        )
        self.listener_thread.start()

    def _audio_listener_loop(self, wake_word_callback, command_callback):
        try:
            with sd.Stream(**self.stream_config) as stream:
                while self.running:
                    data, _ = stream.read(self.stream_config['blocksize'])
                    self.ring_buffer.append(data)
                    if self._detect_voice_activity(data):
                        if wake_word_callback(self._get_buffer_audio()):
                            audio = self._record_command()
                            if audio is not None:
                                command_callback(audio)
        except Exception as e:
            logging.error(f"Audio listener error: {e}")
            self.running = False

    def _detect_voice_activity(self, data):
        profile = self.config.get_current_profile()
        audio_segment = (data * 32768).astype(np.int16)
        mean_amp = np.abs(data).mean()
        if mean_amp > profile.vad_threshold:
            return self.vad.is_speech(audio_segment.tobytes(), self.stream_config['samplerate'])
        return False

    def _get_buffer_audio(self):
        return np.concatenate(self.ring_buffer)

    def _record_command(self):
        profile = self.config.get_current_profile()
        silence_counter = 0
        audio_buffer = []
        try:
            with sd.InputStream(**self.stream_config) as stream:
                while silence_counter < (profile.silence_duration * self.stream_config['samplerate'] / self.stream_config['blocksize']):
                    data, _ = stream.read(self.stream_config['blocksize'])
                    audio_buffer.append(data)
                    if np.abs(data).mean() < profile.silence_threshold:
                        silence_counter += 1
                    else:
                        silence_counter = 0
            return np.concatenate(audio_buffer)
        except Exception as e:
            logging.error(f"Error recording command: {e}")
            return None

    def cleanup(self):
        self.running = False
        try:
            if hasattr(sd, '_lib'):
                sd._lib.Pa_Terminate()
        except Exception as e:
            logging.error(f"Cleanup error: {e}")

    @classmethod
    def initialize_audio_system(cls, interactive=True):
        """Inicializa todo el sistema de audio y retorna una instancia configurada."""
        config = AudioConfig()
        ok, msg = config.test_audio_system()
        if not ok:
            raise AudioError(msg)
        
        device_index = config.select_input_device(interactive)
        instance = cls(device_index=device_index)
        return instance
