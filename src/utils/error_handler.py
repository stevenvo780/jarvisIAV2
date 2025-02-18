import logging
import os
from typing import Any, Type, Callable
from functools import wraps
from logging.handlers import RotatingFileHandler

class JarvisError(Exception):
    pass

class AudioError(JarvisError):
    pass

class AudioDeviceError(AudioError):
    pass

class AudioServiceError(AudioError):
    pass

class AudioConfigError(AudioError):
    pass

class PortAudioError(AudioError):
    pass

class ModelError(JarvisError):
    pass

class ConfigError(JarvisError):
    pass

def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "jarvis.log")
    backup_file = os.path.join(log_dir, "jarvis.log.backup")
    
    handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=5_242_880,  # 5MB
        backupCount=1,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    
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