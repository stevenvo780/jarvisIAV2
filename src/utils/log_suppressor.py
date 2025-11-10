"""
Utilidad para suprimir logs verbosos de librerías externas
mantiene limpia la interfaz de usuario
"""
import os
import sys
import logging
from contextlib import contextmanager
from io import StringIO
from typing import Optional


class SuppressedOutput:
    """Context manager para suprimir stdout/stderr selectivamente"""
    
    def __init__(self, suppress_stdout=True, suppress_stderr=True, redirect_to_log=False):
        self.suppress_stdout = suppress_stdout
        self.suppress_stderr = suppress_stderr
        self.redirect_to_log = redirect_to_log
        self._stdout = None
        self._stderr = None
        self._old_stdout = None
        self._old_stderr = None
        
    def __enter__(self):
        if self.suppress_stdout:
            self._old_stdout = sys.stdout
            self._stdout = StringIO()
            sys.stdout = self._stdout
            
        if self.suppress_stderr:
            self._old_stderr = sys.stderr
            self._stderr = StringIO()
            sys.stderr = self._stderr
            
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Capturar output antes de restaurar
        stdout_content = self._stdout.getvalue() if self._stdout else ""
        stderr_content = self._stderr.getvalue() if self._stderr else ""
        
        # Restaurar originales
        if self._old_stdout:
            sys.stdout = self._old_stdout
        if self._old_stderr:
            sys.stderr = self._old_stderr
        
        # Si hay error, siempre mostrar
        if exc_type is not None:
            if stderr_content:
                print(stderr_content, file=sys.stderr)
            if stdout_content:
                print(stdout_content, file=sys.stdout)
            return False
        
        # Si redirect_to_log, enviar a logger en vez de descartar
        if self.redirect_to_log:
            logger = logging.getLogger('vllm.suppressed')
            if stdout_content:
                logger.debug(f"vLLM stdout: {stdout_content}")
            if stderr_content:
                logger.debug(f"vLLM stderr: {stderr_content}")
        
        return False


def configure_quiet_mode():
    """
    Configura el entorno para suprimir logs verbosos de librerías
    Debe llamarse ANTES de importar vLLM, torch, transformers, etc.
    """
    # Variables de entorno para librerías
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
    os.environ.setdefault('TRANSFORMERS_VERBOSITY', 'error')
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    os.environ.setdefault('VLLM_LOGGING_LEVEL', 'ERROR')
    os.environ.setdefault('VLLM_CONFIGURE_LOGGING', '0')
    os.environ.setdefault('VLLM_LOGGING_CONFIG_PATH', '')
    os.environ.setdefault('TORCH_DISTRIBUTED_DETAIL', 'OFF')
    os.environ.setdefault('NCCL_DEBUG', '')
    os.environ.setdefault('GLOO_LOG_LEVEL', 'ERROR')
    
    # Configurar loggers de librerías verbosas
    verbose_loggers = [
        'vllm',
        'vllm.engine',
        'vllm.worker',
        'vllm.model_executor',
        'torch',
        'torch.distributed',
        'torch.distributed.distributed_c10d',
        'transformers',
        'sentence_transformers',
        'chromadb',
        'httpx',
        'asyncio',
        'tqdm',
        'filelock',
        'huggingface_hub',
    ]
    
    for logger_name in verbose_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)
        logger.propagate = False
        # Remover todos los handlers existentes
        logger.handlers.clear()


def suppress_tqdm():
    """Desactiva barras de progreso de tqdm"""
    try:
        import tqdm as tqdm_module
        
        # Monkey-patch tqdm para que sea silencioso por defecto
        original_tqdm = tqdm_module.tqdm
        
        def silent_tqdm(*args, **kwargs):
            kwargs.setdefault('disable', True)
            return original_tqdm(*args, **kwargs)
        
        tqdm_module.tqdm = silent_tqdm
        tqdm_module.trange = lambda *args, **kwargs: silent_tqdm(range(*args), **kwargs)
        
    except ImportError:
        pass  # tqdm no instalado


def suppress_safetensors_progress():
    """Desactiva mensajes de progreso de safetensors"""
    try:
        import safetensors
        # Intentar deshabilitar verbose mode si existe
        if hasattr(safetensors, 'set_verbose'):
            safetensors.set_verbose(False)
    except (ImportError, AttributeError):
        pass


@contextmanager
def model_loading_context(debug_mode: bool = False):
    """
    Context manager para cargar modelos sin contaminar la terminal
    
    Uso:
        with model_loading_context():
            llm = LLM(model="...")
    """
    if debug_mode:
        # En modo debug, mostrar todo
        yield
        return
    
    # Configurar entorno silencioso
    configure_quiet_mode()
    suppress_tqdm()
    suppress_safetensors_progress()
    
    # Suprimir output
    with SuppressedOutput(
        suppress_stdout=True,
        suppress_stderr=True,
        redirect_to_log=False
    ):
        yield


def setup_clean_terminal():
    """
    Configuración inicial para mantener terminal limpio
    Llamar al inicio de main.py
    """
    debug_mode = os.environ.get('JARVIS_DEBUG') == '1'
    
    if not debug_mode:
        configure_quiet_mode()
        suppress_tqdm()
        suppress_safetensors_progress()
        
        # Suprimir warnings de Python
        import warnings
        warnings.filterwarnings('ignore')
