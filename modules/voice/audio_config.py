# audio_config.py
import os
import json
import logging
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Tuple
import sounddevice as sd
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from .audio_utils import AudioError

@dataclass
class AudioProfile:
    name: str
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    vad_threshold: float = 0.01
    silence_threshold: float = 0.1
    silence_duration: float = 0.5
    energy_threshold: int = 4000
    dynamic_energy: bool = True

class AudioConfig:
    def __init__(self, config_path: Optional[str] = None, timeout=5):
        self.config_path = config_path or os.path.expanduser('~/.jarvis/audio_config.json')
        self._setup_alsa_config()
        self._configure_audio_system()
        self.current_profile = 'default'
        self.profiles = {
            'default': AudioProfile(name='default'),
            'high_quality': AudioProfile(name='high_quality', sample_rate=44100, chunk_size=2048),
            'noisy': AudioProfile(name='noisy', vad_threshold=0.02, energy_threshold=5000)
        }
        self._load_config()
        self.timeout = timeout
        self._setup_timeouts()

    def _setup_alsa_config(self):
        asound_conf = os.path.expanduser('~/.asoundrc')
        if not os.path.exists(asound_conf):
            config = '''
pcm.!default {
    type pulse
    fallback "sysdefault"
    hint {
        show on
        description "Default ALSA Output (PulseAudio)"
    }
}
ctl.!default {
    type pulse
    fallback "sysdefault"
}
            '''
            try:
                with open(asound_conf, 'w') as f:
                    f.write(config)
            except Exception as e:
                logging.warning(f"Couldn't create ALSA config: {e}")

    def _configure_audio_system(self):
        try:
            self._configure_environment()
            if not self._check_audio_permissions():
                if not self._request_audio_permissions():
                    logging.warning("Continuing without full audio permissions")
            if os.system('pulseaudio --check') != 0:
                os.system('pulseaudio --start')
                time.sleep(1)
        except Exception as e:
            raise AudioError(str(e))

    def _configure_environment(self):
        os.environ.update({
            'PULSE_LATENCY_MSEC': '30',
            'PULSE_TIMEOUT': '5000',
            'SDL_AUDIODRIVER': 'pulseaudio',
            'ALSA_CARD': 'PCH'
        })

    def _check_audio_permissions(self):
        try:
            has_direct_access = os.access('/dev/snd', os.R_OK | os.W_OK)
            groups = subprocess.getoutput('groups').split()
            in_audio_group = 'audio' in groups
            pulse_ok = os.path.exists(os.path.expanduser('~/.config/pulse'))
            if not (has_direct_access and in_audio_group and pulse_ok):
                logging.warning("Missing audio permissions or config")
                return False
            return True
        except Exception as e:
            logging.error(f"Error checking audio permissions: {e}")
            return False

    def _request_audio_permissions(self):
        try:
            user = os.getenv("USER")
            if os.access('/dev/snd', os.R_OK | os.W_OK):
                return True
            if os.system('which pkexec >/dev/null 2>&1') == 0:
                cmd = f'pkexec usermod -a -G audio,pulse-access {user}'
            else:
                cmd = f'sudo usermod -a -G audio,pulse-access {user}'
            if os.system(cmd) != 0:
                logging.error("Could not obtain audio permissions")
                return False
            os.system('newgrp audio && newgrp pulse-access')
            return self._check_audio_permissions()
        except Exception as e:
            logging.error(f"Error requesting permissions: {e}")
            return False

    def _setup_timeouts(self):
        os.environ.update({
            'PULSE_TIMEOUT': str(self.timeout * 1000),
            'SDL_AUDIO_ALLOW_REOPEN': '0',
            'AUDIODEV': 'null' if not self._check_audio_permissions() else ''
        })

    def test_audio_system(self) -> Tuple[bool, str]:
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future_devices = executor.submit(self._check_devices)
                devices_ok, msg_devices = future_devices.result(timeout=self.timeout)
                if not devices_ok:
                    return False, msg_devices
                future_pulseaudio = executor.submit(self._check_pulseaudio)
                pulse_ok, msg_pulse = future_pulseaudio.result(timeout=2)
                if not pulse_ok:
                    return False, msg_pulse
            return True, "Audio system OK"
        except TimeoutError:
            return False, "Timeout checking audio system"
        except Exception as e:
            return False, str(e)

    def _check_devices(self):
        try:
            devices = sd.query_devices()
            if not any(d['max_input_channels'] > 0 for d in devices):
                return False, "No input devices found"
            return True, "Audio devices OK"
        except Exception as e:
            return False, str(e)

    def _check_pulseaudio(self):
        try:
            result = subprocess.run(['pulseaudio', '--check'], capture_output=True, timeout=1)
            if result.returncode != 0:
                return False, "Audio service not available"
            return True, "PulseAudio OK"
        except subprocess.TimeoutExpired:
            return False, "Timeout checking PulseAudio"
        except Exception as e:
            return False, str(e)

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for name, profile_data in data.get('profiles', {}).items():
                        self.profiles[name] = AudioProfile(name=name, **profile_data)
                    self.current_profile = data.get('current_profile', 'default')
        except Exception as e:
            logging.error(f"Error loading audio config: {e}")

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump({
                    'current_profile': self.current_profile,
                    'profiles': {name: asdict(profile) for name, profile in self.profiles.items()}
                }, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving audio config: {e}")

    def get_current_profile(self):
        return self.profiles[self.current_profile]

    def set_profile(self, name):
        if name in self.profiles:
            self.current_profile = name
            self.save_config()
            return True
        return False

    def list_input_devices(self):
        """Lista todos los dispositivos de entrada disponibles."""
        devices = sd.query_devices()
        result = []
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                result.append({
                    'index': i,
                    'name': dev['name'],
                    'samplerate': dev['default_samplerate']
                })
        return result

    def select_input_device(self, interactive=True):
        """Permite seleccionar un dispositivo de entrada."""
        devices = self.list_input_devices()
        if not devices:
            raise AudioError("No se encontraron dispositivos de entrada")
        
        if not interactive:
            return devices[0]['index']

        for i, dev in enumerate(devices):
            print(f"[{i}] {dev['name']} (index={dev['index']}, samplerate={dev['samplerate']})")
        
        try:
            choice = input("Seleccione dispositivo de entrada por número: ")
            choice = int(choice)
            if 0 <= choice < len(devices):
                return devices[choice]['index']
            raise ValueError()
        except ValueError:
            raise AudioError("Selección inválida")
