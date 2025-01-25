import signal
from contextlib import contextmanager
import time

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError(f"Timeout después de {seconds} segundos")

    # Configurar manejador de señal
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restaurar manejador por defecto
        signal.alarm(0)
