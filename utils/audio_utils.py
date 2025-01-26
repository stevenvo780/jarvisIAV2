import sys
import numpy as np
import sounddevice as sd

def beep(freq=1000, duration=0.3, sr=44100):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = 0.1 * np.sin(2 * np.pi * freq * t)
    sd.play(wave.astype(np.float32), sr)
    sd.wait()