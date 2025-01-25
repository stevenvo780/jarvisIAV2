import collections
import queue
import sounddevice as sd
import numpy as np
import subprocess
import threading
import logging
import time
from contextlib import contextmanager
from .audio_config import AudioConfig
from .audio_utils import AudioError, retry_audio
from typing import Callable, Optional
import webrtcvad

class AudioEngine:
    def __init__(self, timeout=5):
        self.config = AudioConfig()
        self.running = True
        self.audio_queue = queue.Queue()
        self.vad = webrtcvad.Vad(3)
        self.ring_buffer = collections.deque(maxlen=10)
        self.timeout = timeout
        self._init_audio_system()

    @contextmanager
    def _audio_context(self):
        """Contexto seguro para operaciones de audio con timeout"""
        start_time = time.time()
        try:
            # Forzar cierre de cualquier instancia previa
            if hasattr(sd, '_lib'):
                try:
                    sd._lib.Pa_Terminate()
                except:
                    pass

            # Inicializar con timeout
            while time.time() - start_time < self.timeout:
                try:
                    if not hasattr(sd, '_initialized') or not sd._initialized:
                        sd._initialize()
                    break
                except Exception as e:
                    if time.time() - start_time >= self.timeout:
                        raise AudioError(f"Timeout inicializando audio: {str(e)}")
                    time.sleep(0.1)
            yield
            
        except Exception as e:
            raise AudioError(f"Error de PortAudio: {str(e)}")
        finally:
            if hasattr(sd, '_lib'):
                try:
                    sd._lib.Pa_Terminate()
                except:
                    pass

    @retry_audio(max_attempts=2)
    def _init_audio_system(self) -> None:
        """Inicializa el sistema de audio con timeout"""
        try:
            with self._audio_context():
                # Verificar permisos de audio primero
                self._check_audio_permissions()
                self.devices = self._find_best_devices()
                self._setup_streams()
        except Exception as e:
            logging.error(f"Error inicializando audio: {e}")
            raise AudioError("Fallo en inicialización de audio", recoverable=False)

    def _check_audio_permissions(self):
        """Verifica permisos de audio"""
        try:
            # Intenta abrir brevemente el stream para verificar permisos
            dummy_stream = sd.InputStream(channels=1, samplerate=16000, blocksize=1024)
            dummy_stream.start()
            dummy_stream.stop()
            dummy_stream.close()
        except Exception as e:
            raise AudioError(f"Error de permisos de audio: {str(e)}")

    def _find_best_devices(self) -> dict:
        try:
            devices = sd.query_devices()
            valid_inputs = [d for d in devices 
                          if d['max_input_channels'] > 0 and 
                          d['default_samplerate'] in [16000, 44100, 48000]]
            valid_outputs = [d for d in devices 
                           if d['max_output_channels'] > 0]

            if not valid_inputs or not valid_outputs:
                raise AudioError("No se encontraron dispositivos compatibles")

            return {
                'input': valid_inputs[0],
                'output': valid_outputs[0]
            }
        except Exception as e:
            raise AudioError(f"Error detectando dispositivos: {e}")

    def _setup_streams(self) -> None:
        profile = self.config.get_current_profile()
        self.stream_config = {
            'samplerate': profile.sample_rate,
            'channels': profile.channels,
            'dtype': np.float32,
            'blocksize': profile.chunk_size,
            'device': (self.devices['input']['index'], 
                      self.devices['output']['index'])
        }

    def start_listening(self, wake_word_callback: Callable, 
                       command_callback: Callable) -> None:
        """Inicia escucha en segundo plano"""
        self.listener_thread = threading.Thread(
            target=self._audio_listener_loop,
            args=(wake_word_callback, command_callback),
            daemon=True
        )
        self.listener_thread.start()

    def _audio_listener_loop(self, wake_word_callback: Callable, 
                           command_callback: Callable) -> None:
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
            logging.error(f"Error en audio listener: {e}")
            self.running = False

    def _detect_voice_activity(self, data: np.ndarray) -> bool:
        profile = self.config.get_current_profile()
        audio_segment = (data * 32768).astype(np.int16)
        return (np.abs(data).mean() > profile.vad_threshold and
                self.vad.is_speech(audio_segment.tobytes(), 
                                 self.stream_config['samplerate']))

    def _get_buffer_audio(self) -> np.ndarray:
        return np.concatenate(self.ring_buffer)

    def _record_command(self) -> Optional[np.ndarray]:
        profile = self.config.get_current_profile()
        silence_counter = 0
        audio_buffer = []
        
        try:
            with sd.InputStream(**self.stream_config) as stream:
                while silence_counter < (profile.silence_duration * 
                                       self.stream_config['samplerate'] / 
                                       self.stream_config['blocksize']):
                    data, _ = stream.read(self.stream_config['blocksize'])
                    audio_buffer.append(data)
                    
                    if np.abs(data).mean() < profile.silence_threshold:
                        silence_counter += 1
                    else:
                        silence_counter = 0

            return np.concatenate(audio_buffer)
        except Exception as e:
            logging.error(f"Error grabando comando: {e}")
            return None

    def cleanup(self) -> None:
        """Limpieza explícita de recursos"""
        self.running = False
        try:
            if hasattr(sd, '_lib'):
                sd._lib.Pa_Terminate()
        except Exception as e:
            logging.error(f"Error en cleanup: {e}")
