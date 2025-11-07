"""
Context Managers para Gestión de Recursos GPU
Asegura cleanup automático y manejo correcto de recursos
"""

import logging
import torch
from contextlib import contextmanager
from typing import Optional, Generator, Any
from dataclasses import dataclass

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class GPUMemorySnapshot:
    """Snapshot de memoria GPU"""
    device_id: int
    allocated_mb: float
    reserved_mb: float
    free_mb: float
    total_mb: float
    utilization: float


class GPUContextManager:
    """
    Context manager para operaciones GPU con cleanup automático
    
    Usage:
        with GPUContextManager(device_id=0) as gpu:
            model = load_model()
            result = model.generate()
        # Automáticamente libera memoria aquí
    """
    
    def __init__(
        self,
        device_id: int = 0,
        reserve_mb: int = 500,
        enable_monitoring: bool = True
    ):
        """
        Inicializar context manager GPU
        
        Args:
            device_id: ID de la GPU a usar
            reserve_mb: Memoria a reservar (MB)
            enable_monitoring: Si debe monitorear uso de memoria
        """
        self.device_id = device_id
        self.reserve_mb = reserve_mb
        self.enable_monitoring = enable_monitoring
        self.initial_snapshot: Optional[GPUMemorySnapshot] = None
        self.final_snapshot: Optional[GPUMemorySnapshot] = None
        
    def __enter__(self):
        """Entrar al contexto"""
        if not torch.cuda.is_available():
            logger.warning("CUDA no disponible, operando en CPU")
            return self
        
        # Tomar snapshot inicial
        if self.enable_monitoring:
            self.initial_snapshot = self._take_snapshot()
            logger.info(f"GPU {self.device_id} - Memoria inicial: "
                       f"{self.initial_snapshot.allocated_mb:.1f}MB allocated, "
                       f"{self.initial_snapshot.free_mb:.1f}MB free")
        
        # Limpiar cache
        torch.cuda.empty_cache()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Salir del contexto con cleanup"""
        if not torch.cuda.is_available():
            return False
        
        try:
            # Limpiar memoria GPU
            torch.cuda.empty_cache()
            torch.cuda.synchronize(self.device_id)
            
            # Tomar snapshot final
            if self.enable_monitoring:
                self.final_snapshot = self._take_snapshot()
                
                # Calcular diferencia de memoria
                delta_mb = (self.final_snapshot.allocated_mb - 
                           self.initial_snapshot.allocated_mb)
                
                if abs(delta_mb) > 100:  # Más de 100MB de diferencia
                    logger.warning(f"GPU {self.device_id} - Posible memory leak: "
                                 f"{delta_mb:+.1f}MB de cambio")
                
                logger.info(f"GPU {self.device_id} - Memoria final: "
                           f"{self.final_snapshot.allocated_mb:.1f}MB allocated, "
                           f"{self.final_snapshot.free_mb:.1f}MB free")
        
        except Exception as e:
            logger.error(f"Error en cleanup GPU: {e}")
        
        # No suprimir excepciones
        return False
    
    def _take_snapshot(self) -> GPUMemorySnapshot:
        """Tomar snapshot de memoria GPU"""
        if PYNVML_AVAILABLE:
            return self._pynvml_snapshot()
        else:
            return self._torch_snapshot()
    
    def _torch_snapshot(self) -> GPUMemorySnapshot:
        """Snapshot usando PyTorch"""
        allocated = torch.cuda.memory_allocated(self.device_id)
        reserved = torch.cuda.memory_reserved(self.device_id)
        
        props = torch.cuda.get_device_properties(self.device_id)
        total = props.total_memory
        free = total - allocated
        
        return GPUMemorySnapshot(
            device_id=self.device_id,
            allocated_mb=allocated / 1024**2,
            reserved_mb=reserved / 1024**2,
            free_mb=free / 1024**2,
            total_mb=total / 1024**2,
            utilization=(allocated / total) * 100 if total > 0 else 0
        )
    
    def _pynvml_snapshot(self) -> GPUMemorySnapshot:
        """Snapshot usando pynvml"""
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_id)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            return GPUMemorySnapshot(
                device_id=self.device_id,
                allocated_mb=info.used / 1024**2,
                reserved_mb=0,  # pynvml no distingue reserved
                free_mb=info.free / 1024**2,
                total_mb=info.total / 1024**2,
                utilization=(info.used / info.total) * 100
            )
        except Exception as e:
            logger.warning(f"Error usando pynvml: {e}, fallback a torch")
            return self._torch_snapshot()
    
    def get_memory_usage(self) -> dict:
        """Obtener uso actual de memoria"""
        if not torch.cuda.is_available():
            return {}
        
        snapshot = self._take_snapshot()
        return {
            'allocated_mb': snapshot.allocated_mb,
            'free_mb': snapshot.free_mb,
            'utilization_pct': snapshot.utilization
        }


@contextmanager
def gpu_memory_guard(
    device_id: int = 0,
    max_allocated_mb: Optional[float] = None,
    raise_on_exceed: bool = False
) -> Generator[None, None, None]:
    """
    Context manager que guarda contra uso excesivo de memoria GPU
    
    Args:
        device_id: ID de GPU
        max_allocated_mb: Máximo de memoria permitida
        raise_on_exceed: Si debe lanzar excepción al exceder límite
    
    Usage:
        with gpu_memory_guard(device_id=0, max_allocated_mb=10000):
            result = heavy_computation()
    """
    if not torch.cuda.is_available():
        yield
        return
    
    initial_allocated = torch.cuda.memory_allocated(device_id) / 1024**2
    
    try:
        yield
    finally:
        final_allocated = torch.cuda.memory_allocated(device_id) / 1024**2
        delta = final_allocated - initial_allocated
        
        if max_allocated_mb and final_allocated > max_allocated_mb:
            msg = (f"GPU {device_id} excedió límite de memoria: "
                  f"{final_allocated:.1f}MB > {max_allocated_mb:.1f}MB")
            
            if raise_on_exceed:
                raise RuntimeError(msg)
            else:
                logger.warning(msg)
        
        if delta > 100:  # Más de 100MB de incremento
            logger.info(f"GPU {device_id} - Memoria incrementada en {delta:+.1f}MB")


@contextmanager
def model_context(
    model: Any,
    device: str = "cuda:0",
    unload_on_exit: bool = True
) -> Generator[Any, None, None]:
    """
    Context manager para modelos con carga/descarga automática
    
    Args:
        model: Modelo a gestionar
        device: Dispositivo target
        unload_on_exit: Si debe descargar modelo al salir
    
    Usage:
        with model_context(my_model, device="cuda:0", unload_on_exit=True) as model:
            output = model.generate(input)
        # Modelo descargado automáticamente
    """
    original_device = None
    
    try:
        # Mover a dispositivo si es necesario
        if hasattr(model, 'to'):
            if hasattr(model, 'device'):
                original_device = str(model.device)
            model = model.to(device)
            logger.info(f"Modelo movido a {device}")
        
        yield model
    
    finally:
        if unload_on_exit:
            try:
                # Mover de vuelta a CPU o dispositivo original
                if hasattr(model, 'to'):
                    target_device = original_device if original_device else 'cpu'
                    model.to(target_device)
                    logger.info(f"Modelo descargado de GPU")
                
                # Limpiar cache
                if 'cuda' in device:
                    torch.cuda.empty_cache()
            
            except Exception as e:
                logger.error(f"Error descargando modelo: {e}")


@contextmanager
def synchronized_gpu(device_id: int = 0) -> Generator[None, None, None]:
    """
    Context manager que asegura sincronización GPU
    
    Usage:
        with synchronized_gpu(device_id=0):
            async_operation()
        # Garantiza que todas las operaciones terminaron
    """
    try:
        yield
    finally:
        if torch.cuda.is_available():
            torch.cuda.synchronize(device_id)


class GPUPool:
    """
    Pool de GPUs para distribución de carga
    
    Usage:
        pool = GPUPool([0, 1])
        
        with pool.acquire() as gpu_id:
            model = load_model(device=f"cuda:{gpu_id}")
            result = model.generate()
    """
    
    def __init__(self, gpu_ids: list[int], reserve_mb: int = 500):
        """
        Inicializar pool de GPUs
        
        Args:
            gpu_ids: Lista de IDs de GPU disponibles
            reserve_mb: Memoria reservada por GPU
        """
        self.gpu_ids = gpu_ids
        self.reserve_mb = reserve_mb
        self.usage_count = {gpu_id: 0 for gpu_id in gpu_ids}
    
    @contextmanager
    def acquire(self, prefer_gpu: Optional[int] = None) -> Generator[int, None, None]:
        """
        Adquirir GPU del pool
        
        Args:
            prefer_gpu: GPU preferida (si está disponible)
        
        Yields:
            ID de GPU asignada
        """
        # Seleccionar GPU menos usada
        if prefer_gpu and prefer_gpu in self.gpu_ids:
            selected_gpu = prefer_gpu
        else:
            selected_gpu = min(self.usage_count, key=self.usage_count.get)
        
        self.usage_count[selected_gpu] += 1
        logger.debug(f"GPU {selected_gpu} adquirida (uso: {self.usage_count[selected_gpu]})")
        
        try:
            yield selected_gpu
        finally:
            self.usage_count[selected_gpu] -= 1
            logger.debug(f"GPU {selected_gpu} liberada (uso: {self.usage_count[selected_gpu]})")
    
    def get_stats(self) -> dict:
        """Obtener estadísticas del pool"""
        return {
            'total_gpus': len(self.gpu_ids),
            'usage': dict(self.usage_count),
            'available': [gpu for gpu, count in self.usage_count.items() if count == 0]
        }


# Funciones helper
def cleanup_gpu(device_id: int = 0):
    """Limpiar memoria GPU manualmente"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize(device_id)
        logger.info(f"GPU {device_id} limpiada")


def get_gpu_info(device_id: int = 0) -> dict:
    """Obtener información de GPU"""
    if not torch.cuda.is_available():
        return {"available": False}
    
    props = torch.cuda.get_device_properties(device_id)
    allocated = torch.cuda.memory_allocated(device_id)
    reserved = torch.cuda.memory_reserved(device_id)
    
    return {
        "available": True,
        "device_id": device_id,
        "name": props.name,
        "total_memory_mb": props.total_memory / 1024**2,
        "allocated_mb": allocated / 1024**2,
        "reserved_mb": reserved / 1024**2,
        "free_mb": (props.total_memory - allocated) / 1024**2,
        "compute_capability": f"{props.major}.{props.minor}"
    }
