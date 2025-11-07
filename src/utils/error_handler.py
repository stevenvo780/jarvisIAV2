import logging
import os
import traceback
from typing import Any, Type, Callable, Optional
from functools import wraps
from logging.handlers import RotatingFileHandler
from datetime import datetime

class JarvisError(Exception):
    """Base exception for all Jarvis errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class AudioError(JarvisError):
    """Base class for audio-related errors"""
    pass

class AudioDeviceError(AudioError):
    """Raised when audio device is not available or fails"""
    pass

class AudioServiceError(AudioError):
    """Raised when audio service initialization fails"""
    pass

class AudioConfigError(AudioError):
    """Raised when audio configuration is invalid"""
    pass

class PortAudioError(AudioError):
    """Raised when PortAudio has issues"""
    pass

class ModelError(JarvisError):
    """Base class for model-related errors"""
    pass

class ModelLoadError(ModelError):
    """Raised when model fails to load"""
    pass

class ModelInferenceError(ModelError):
    """Raised when model inference fails"""
    pass

class ConfigError(JarvisError):
    """Raised when configuration is invalid or missing"""
    pass

class GPUError(JarvisError):
    """Raised when GPU operations fail"""
    pass

class ValidationError(JarvisError):
    """Raised when input validation fails"""
    pass

def setup_logging(
    log_dir: str = "logs", 
    level: int = logging.INFO,
    structured: bool = False
) -> None:
    """
    Configura el sistema de logging para Jarvis con soporte para logging estructurado
    
    Args:
        log_dir: Directorio donde se guardarán los logs
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Si True, usa formato JSON estructurado
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "jarvis.log")
        error_log_file = os.path.join(log_dir, "errors.log")
        
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        if root_logger.handlers:
            root_logger.handlers.clear()
        
        # Handler para archivo principal
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # Handler separado para errores
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato estructurado o tradicional
        if structured:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)
        
        logging.info("Sistema de logging inicializado correctamente")
        
    except Exception as e:
        print(f"Error configurando logging: {e}")
        raise


class StructuredFormatter(logging.Formatter):
    """Formatter para logging estructurado en JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Añadir información de excepción si existe
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Añadir campos extras
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)

def handle_errors(
    error_type: Type[Exception] = Exception,
    default_value: Any = None,
    log_message: str = "Error en la operación",
    terminal: bool = False,
    raise_on_error: bool = False,
    max_retries: int = 0,
    retry_delay: float = 1.0
) -> Callable:
    """
    Decorador mejorado para manejo de errores con reintentos y logging detallado
    
    Args:
        error_type: Tipo de excepción a capturar
        default_value: Valor a retornar en caso de error
        log_message: Mensaje base para logging
        terminal: Si True, muestra error en terminal
        raise_on_error: Si True, re-lanza la excepción después de loggear
        max_retries: Número de reintentos antes de fallar
        retry_delay: Segundos de espera entre reintentos
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except error_type as e:
                    last_exception = e
                    
                    # Logging detallado
                    error_details = {
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "max_retries": max_retries + 1,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                    
                    if isinstance(e, JarvisError):
                        error_details.update(e.to_dict())
                    
                    msg = f"{log_message}: {str(e)}"
                    
                    # Logging con stack trace completo
                    if attempt == max_retries:
                        logging.error(msg, exc_info=True, extra={'extra_fields': error_details})
                    else:
                        logging.warning(f"{msg} - Reintentando ({attempt + 1}/{max_retries})...")
                    
                    # Mostrar en terminal si está configurado
                    if terminal and hasattr(args[0], 'terminal'):
                        args[0].terminal.print_error(msg)
                    
                    # Si no es el último intento, esperar antes de reintentar
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    else:
                        # Último intento fallido
                        if raise_on_error:
                            raise
                        return default_value
            
            return default_value
        return wrapper
    return decorator


def log_exception(logger: logging.Logger, exception: Exception, context: dict = None):
    """
    Función auxiliar para logging detallado de excepciones
    
    Args:
        logger: Logger a usar
        exception: Excepción a loggear
        context: Contexto adicional (dict)
    """
    error_data = {
        "exception_type": type(exception).__name__,
        "message": str(exception),
        "traceback": traceback.format_exc()
    }
    
    if context:
        error_data["context"] = context
    
    if isinstance(exception, JarvisError):
        error_data.update(exception.to_dict())
    
    logger.error(f"Exception occurred: {error_data['exception_type']}", extra={'extra_fields': error_data})