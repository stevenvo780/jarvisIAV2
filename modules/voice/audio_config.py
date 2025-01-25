import os
import json
import logging
import subprocess
from dataclasses import dataclass, asdict
import time
from typing import Optional, Dict, Any, Tuple
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
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.expanduser('~/.jarvis/audio_config.json')
        self._setup_alsa_config()
        self._configure_audio_system()
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

    def _setup_alsa_config(self) -> None:
        """Configura ALSA para minimizar mensajes de error"""
        asound_conf = os.path.expanduser('~/.asoundrc')
        if not os.path.exists(asound_conf):
            config = """
pcm.!default {
    type pulse
    fallback "sysdefault"
    hint {
        show on
        description "Default ALSA Output (currently PulseAudio Sound Server)"
    }
}
ctl.!default {
    type pulse
    fallback "sysdefault"
}
"""
            try:
                with open(asound_conf, 'w') as f:
                    f.write(config)
            except Exception as e:
                logging.warning(f"No se pudo crear configuración ALSA: {e}")

    def _configure_audio_system(self) -> None:
        """Configura el sistema de audio y verifica permisos"""
        try:
            # Configurar ambiente
            self._configure_environment()
            
            # Verificar permisos
            if not self._check_audio_permissions():
                if not self._request_audio_permissions():
                    logging.warning("Continuando sin permisos de audio completos")
            
            # Verificar PulseAudio
            if os.system('pulseaudio --check') != 0:
                # Intentar iniciar PulseAudio si no está corriendo
                os.system('pulseaudio --start')
                time.sleep(1)
                
        except Exception as e:
            raise AudioError(f"Error configurando audio: {str(e)}")

    def _configure_environment(self) -> None:
        """Configura variables de entorno para el audio"""
        os.environ.update({
            'PULSE_LATENCY_MSEC': '30',
            'PULSE_TIMEOUT': '5000',
            'SDL_AUDIODRIVER': 'pulseaudio',
            'ALSA_CARD': 'PCH'  # Usar la tarjeta de sonido principal
        })

    def _check_audio_permissions(self) -> bool:
        """Verifica permisos de audio"""
        try:
            # Verificar permisos directos
            has_direct_access = os.access('/dev/snd', os.R_OK | os.W_OK)
            
            # Verificar grupo de audio
            groups = subprocess.getoutput('groups').split()
            in_audio_group = 'audio' in groups
            
            # Verificar PulseAudio
            pulse_ok = os.path.exists(os.path.expanduser('~/.config/pulse'))
            
            if not (has_direct_access and in_audio_group and pulse_ok):
                logging.warning("Faltan permisos de audio o configuración")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error verificando permisos: {e}")
            return False

    def _request_audio_permissions(self) -> bool:
        """Solicita permisos de audio necesarios"""
        try:
            user = os.getenv("USER")
            
            # Primero verificar si ya tenemos permisos
            if os.access('/dev/snd', os.R_OK | os.W_OK):
                return True
                
            # Intentar con pkexec primero
            if os.system('which pkexec >/dev/null 2>&1') == 0:
                cmd = f'pkexec usermod -a -G audio,pulse-access {user}'
            else:
                cmd = f'sudo usermod -a -G audio,pulse-access {user}'
            
            if os.system(cmd) != 0:
                logging.error("No se pudieron obtener permisos de audio")
                return False
                
            # Recargar grupos sin necesidad de reiniciar
            os.system(f'newgrp audio && newgrp pulse-access')
            
            return self._check_audio_permissions()
            
        except Exception as e:
            logging.error(f"Error solicitando permisos: {e}")
            return False

    def test_audio_system(self) -> Tuple[bool, str]:
        """Prueba exhaustiva del sistema de audio"""
        try:
            # 1. Verificar permisos
            if not self._check_audio_permissions():
                return False, "Permisos de audio insuficientes"

            # 2. Verificar PulseAudio
            if os.system('pulseaudio --check') != 0:
                return False, "PulseAudio no está ejecutándose"

            # 3. Verificar tarjetas de sonido
            alsa_output = subprocess.getoutput('aplay -l')
            if "no soundcards found" in alsa_output.lower():
                return False, "No se detectaron tarjetas de sonido"

            # 4. Verificar configuración
            if not os.path.exists(os.path.expanduser('~/.asoundrc')):
                self._setup_alsa_config()

            return True, "Sistema de audio OK"
            
        except Exception as e:
            return False, f"Error en sistema de audio: {str(e)}"

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
