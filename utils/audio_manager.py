import os
import sys
import logging
import subprocess
import time
from contextlib import contextmanager
from typing import Optional, Dict

class AudioManager:
    @staticmethod
    def configure_environment():
        """Configura las variables de entorno necesarias para el audio"""
        env_vars = {
            'PULSE_LATENCY_MSEC': '30',
            'PULSE_TIMEOUT': '5000',
            'PULSE_RETRY': '5',
            'ALSA_CARD': 'default',
            'AUDIODEV': 'default',
            'SDL_AUDIODRIVER': 'pulseaudio',
            'JACK_NO_START_SERVER': '1'
        }
        os.environ.update(env_vars)
        AudioManager._create_alsa_config()

    @staticmethod
    def _create_alsa_config():
        """Crea configuración ALSA robusta"""
        config = """
pcm.!default {
    type plug
    slave.pcm {
        type pulse
        fallback "sysdefault"
        hint.description "Default Audio Device"
    }
    fallback "sysdefault"
}

ctl.!default {
    type pulse
    fallback "sysdefault"
}

pcm.pulse {
    type pulse
}

ctl.pulse {
    type pulse
}

pcm.dmix {
    type dmix
    ipc_key 1024
    slave {
        pcm "hw:0,0"
        period_time 0
        period_size 1024
        buffer_size 4096
    }
}
"""
        config_path = os.path.expanduser('~/.asoundrc')
        with open(config_path, 'w') as f:
            f.write(config)

    @staticmethod
    def setup_audio_system() -> bool:
        """Configura y valida el sistema de audio"""
        try:
            # Verificar PulseAudio
            if not AudioManager._check_pulseaudio():
                return False

            # Reiniciar servicios de audio
            AudioManager._restart_audio_services()

            # Verificar dispositivos
            if not AudioManager._validate_audio_devices():
                return False

            return True
        except Exception as e:
            logging.error(f"Error en configuración de audio: {e}")
            return False

    @staticmethod
    def _check_pulseaudio() -> bool:
        """Verifica estado de PulseAudio"""
        try:
            result = subprocess.run(
                ['pulseaudio', '--check'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                subprocess.run(['pulseaudio', '--start'])
                time.sleep(2)  # Esperar inicialización
            return True
        except Exception:
            return False

    @staticmethod
    def _restart_audio_services():
        """Reinicia servicios de audio con manejo de errores"""
        commands = [
            ['pulseaudio', '-k'],
            ['pulseaudio', '--start'],
            ['alsactl', 'restore']
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, stderr=subprocess.PIPE, timeout=5)
                time.sleep(1)
            except subprocess.TimeoutExpired:
                logging.warning(f"Timeout ejecutando {cmd}")
            except Exception as e:
                logging.error(f"Error en comando {cmd}: {e}")

    @staticmethod
    def _validate_audio_devices() -> bool:
        """Valida dispositivos de audio disponibles"""
        try:
            result = subprocess.run(
                ['aplay', '-l'],
                capture_output=True,
                text=True
            )
            return 'no soundcards found' not in result.stderr
        except Exception:
            return False

    @staticmethod
    @contextmanager
    def suppress_output():
        """Suprime todas las salidas incluyendo stderr y logs de bajo nivel"""
        with open(os.devnull, 'w') as devnull:
            stderr_fd = sys.stderr.fileno()
            stdout_fd = sys.stdout.fileno()
            
            stderr_copy = os.dup(stderr_fd)
            stdout_copy = os.dup(stdout_fd)
            
            os.dup2(devnull.fileno(), stderr_fd)
            os.dup2(devnull.fileno(), stdout_fd)
            
            try:
                yield
            finally:
                os.dup2(stderr_copy, stderr_fd)
                os.dup2(stdout_copy, stdout_fd)
                os.close(stderr_copy)
                os.close(stdout_copy)

    @staticmethod
    def get_default_device() -> Optional[Dict]:
        """Obtiene información del dispositivo de audio predeterminado"""
        try:
            result = subprocess.run(
                ['pacmd', 'list-sinks'],
                capture_output=True,
                text=True
            )
            if '* index' in result.stdout:
                return {'status': 'ok', 'device': 'default'}
            return None
        except Exception:
            return None
