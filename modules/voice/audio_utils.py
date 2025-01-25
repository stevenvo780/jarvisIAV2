import time
import logging
from functools import wraps
from typing import Optional, Callable, Any

class AudioError(Exception):
    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)

def retry_audio(max_attempts: int = 3, 
                delay: float = 1.0, 
                fallback: Optional[Callable] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
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
                    logging.warning(
                        f"Reintentando {func.__name__} ({attempt + 1}/{max_attempts})"
                    )
            
            if fallback:
                return fallback()
            raise last_exception
                
        return wrapper
    return decorator
