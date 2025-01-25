# audio_utils.py
import time
import logging
from functools import wraps

class AudioError(Exception):
    def __init__(self, message, recoverable=True):
        self.recoverable = recoverable
        super().__init__(message)

def retry_audio(max_attempts=3, delay=1.0, fallback=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except AudioError as e:
                    if not e.recoverable:
                        if fallback:
                            return fallback()
                        raise
                    last_exception = e
                except Exception as e:
                    last_exception = AudioError(str(e))
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    logging.warning(f"Retrying {func.__name__} ({attempt+1}/{max_attempts})")
            if fallback:
                return fallback()
            raise last_exception
        return wrapper
    return decorator

def beep(freq=1000, duration=0.3, sr=44100):
    """Reproduce un beep de la frecuencia y duración especificada."""
    import numpy as np
    import sounddevice as sd
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = 0.1 * np.sin(2 * np.pi * freq * t)
    sd.play(wave.astype(np.float32), sr)
    sd.wait()
