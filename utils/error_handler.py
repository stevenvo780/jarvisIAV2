import logging
import os
from typing import Any, Type, Callable
from functools import wraps

class JarvisError(Exception):
    """Clase base para errores personalizados de Jarvis"""
    pass

class AudioError(JarvisError):
    """Errores relacionados con el sistema de audio"""
    pass

class AudioDeviceError(AudioError):
    """Error específico para problemas con dispositivos de audio"""
    pass

class AudioServiceError(AudioError):
    """Error específico para problemas con servicios de audio"""
    pass

class AudioConfigError(AudioError):
    """Error específico para problemas de configuración de audio"""
    pass

class ModelError(JarvisError):
    """Errores relacionados con los modelos de IA"""
    pass

class ConfigError(JarvisError):
    """Errores relacionados con la configuración"""
    pass

def setup_logging(log_dir: str = "logs") -> None:
    """Configura el sistema de logging"""
    os.makedirs(log_dir, exist_ok=True)
    
    # Configuración básica
    logging.basicConfig(
        filename=os.path.join(log_dir, "jarvis.log"),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Silenciar loggers ruidosos
    noisy_loggers = [
        'alsa', 'ALSA', 'jack', 'JACK', 'pulse', 'pygame',
        'portaudio', 'comtypes', 'speechrecognition'
    ]
    
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL + 1)
        logger.disabled = True
        logger.propagate = False

def handle_errors(error_type: Type[Exception] = Exception,
                 default_value: Any = None,
                 log_message: str = "Error en la operación",
                 terminal: bool = False) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_type as e:
                msg = f"{log_message}: {str(e)}"
                logging.error(msg)
                if terminal and hasattr(args[0], 'terminal'):
                    args[0].terminal.print_error(msg)
                return default_value
        return wrapper
    return decorator