import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

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
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.expanduser('~/.jarvis/audio_config.json')
        self.current_profile = 'default'
        self.profiles: Dict[str, AudioProfile] = {
            'default': AudioProfile(
                name='default',
                sample_rate=16000,
                chunk_size=1024
            ),
            'high_quality': AudioProfile(
                name='high_quality',
                sample_rate=44100,
                chunk_size=2048
            ),
            'noisy': AudioProfile(
                name='noisy',
                vad_threshold=0.02,
                energy_threshold=5000
            )
        }
        self._load_config()

    def _load_config(self) -> None:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for name, profile_data in data.get('profiles', {}).items():
                        self.profiles[name] = AudioProfile(name=name, **profile_data)
                    self.current_profile = data.get('current_profile', 'default')
        except Exception as e:
            logging.error(f"Error loading audio config: {e}")

    def save_config(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump({
                    'current_profile': self.current_profile,
                    'profiles': {name: asdict(profile) 
                               for name, profile in self.profiles.items()}
                }, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving audio config: {e}")

    def get_current_profile(self) -> AudioProfile:
        return self.profiles[self.current_profile]

    def set_profile(self, name: str) -> bool:
        if name in self.profiles:
            self.current_profile = name
            self.save_config()
            return True
        return False
