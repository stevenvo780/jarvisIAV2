"""
GPU Resource Management
Context managers and utilities for safe GPU resource handling
"""

import logging
import torch
from typing import Optional, List
from contextlib import contextmanager

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False


class GPUResourceManager:
    """
    Manages GPU resources with automatic cleanup
    
    Usage:
        with GPUResourceManager.allocate_gpu(0) as gpu:
            # Use GPU
            model.to(f"cuda:{gpu.device_id}")
        # Automatic cleanup
    """
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize NVML for GPU monitoring"""
        if cls._initialized:
            return
        
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                cls._initialized = True
                logging.info("✅ NVML initialized for GPU monitoring")
            except Exception as e:
                logging.warning(f"Failed to initialize NVML: {e}")
        else:
            logging.warning("pynvml not available, GPU monitoring disabled")
    
    @classmethod
    def shutdown(cls):
        """Shutdown NVML"""
        if cls._initialized and PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
                cls._initialized = False
                logging.info("NVML shutdown")
            except Exception as e:
                logging.error(f"Error shutting down NVML: {e}")
    
    @staticmethod
    @contextmanager
    def allocate_gpu(gpu_id: int):
        """
        Context manager for GPU allocation with safe cleanup
        
        Args:
            gpu_id: GPU device ID
        
        Yields:
            GPUContext object
        """
        gpu_context = GPUContext(gpu_id)
        acquired = False
        
        try:
            gpu_context.acquire()
            acquired = True
            yield gpu_context
        finally:
            if acquired:
                gpu_context.release()
            else:
                # Clean up partial state if acquire failed
                gpu_context.cleanup_partial()
    
    @staticmethod
    def get_gpu_memory(gpu_id: int) -> tuple[int, int]:
        """
        Get GPU memory usage
        
        Args:
            gpu_id: GPU device ID
        
        Returns:
            (used_mb, total_mb)
        """
        if not PYNVML_AVAILABLE:
            return (0, 0)
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used = info.used // (1024 ** 2)
            total = info.total // (1024 ** 2)
            return (used, total)
        except Exception as e:
            logging.error(f"Error getting GPU {gpu_id} memory: {e}")
            return (0, 0)
    
    @staticmethod
    def get_available_gpus() -> List[int]:
        """
        Get list of available GPU IDs
        
        Returns:
            List of GPU device IDs
        """
        if torch.cuda.is_available():
            return list(range(torch.cuda.device_count()))
        return []
    
    @staticmethod
    def clear_cache(gpu_id: Optional[int] = None):
        """
        Clear GPU cache
        
        Args:
            gpu_id: Specific GPU to clear, or None for all
        """
        if torch.cuda.is_available():
            if gpu_id is not None:
                with torch.cuda.device(gpu_id):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                logging.info(f"Cleared cache for GPU {gpu_id}")
            else:
                torch.cuda.empty_cache()
                logging.info("Cleared cache for all GPUs")


class GPUContext:
    """Context for GPU allocation"""
    
    def __init__(self, device_id: int):
        self.device_id = device_id
        self.device_name = f"cuda:{device_id}"
        self.initial_memory = None
        self.logger = logging.getLogger(f"GPU.{device_id}")
    
    def acquire(self):
        """Acquire GPU resources"""
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available")
        
        if self.device_id >= torch.cuda.device_count():
            raise ValueError(f"GPU {self.device_id} not available")
        
        # Record initial memory
        self.initial_memory = GPUResourceManager.get_gpu_memory(self.device_id)
        self.logger.info(
            f"Acquired GPU {self.device_id} "
            f"(Memory: {self.initial_memory[0]}/{self.initial_memory[1]} MB)"
        )
    
    def release(self):
        """Release GPU resources and cleanup"""
        try:
            # Clear cache
            GPUResourceManager.clear_cache(self.device_id)
            
            # Log memory usage
            final_memory = GPUResourceManager.get_gpu_memory(self.device_id)
            memory_diff = final_memory[0] - self.initial_memory[0]
            
            if memory_diff > 0:
                self.logger.warning(
                    f"GPU {self.device_id} memory increased by {memory_diff} MB "
                    "(possible memory leak)"
                )
            
            self.logger.info(f"Released GPU {self.device_id}")
        
        except Exception as e:
            self.logger.error(f"Error releasing GPU {self.device_id}: {e}")
    
    def cleanup_partial(self):
        """Clean up partial state if acquire failed"""
        try:
            # Clear any partially allocated resources
            if torch.cuda.is_available() and self.device_id < torch.cuda.device_count():
                GPUResourceManager.clear_cache(self.device_id)
                self.logger.info(f"Cleaned up partial state for GPU {self.device_id}")
        except Exception as e:
            self.logger.error(f"Error cleaning up partial state: {e}")
    
    def get_memory_info(self) -> dict:
        """Get current memory information"""
        used, total = GPUResourceManager.get_gpu_memory(self.device_id)
        return {
            "device_id": self.device_id,
            "used_mb": used,
            "total_mb": total,
            "free_mb": total - used,
            "utilization_pct": (used / total * 100) if total > 0 else 0
        }


@contextmanager
def cuda_device(device_id: int):
    """
    Simple context manager for CUDA device
    
    Args:
        device_id: GPU device ID
    
    Usage:
        with cuda_device(0):
            # Code runs on GPU 0
            model.forward(x)
    """
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available")
    
    previous_device = torch.cuda.current_device()
    
    try:
        torch.cuda.set_device(device_id)
        yield
    finally:
        torch.cuda.set_device(previous_device)


@contextmanager
def gpu_memory_guard(gpu_id: int, required_mb: int, buffer_mb: int = 500):
    """
    Context manager that ensures sufficient GPU memory
    
    Args:
        gpu_id: GPU device ID
        required_mb: Required memory in MB
        buffer_mb: Additional buffer in MB
    
    Raises:
        RuntimeError: If insufficient memory
    """
    used, total = GPUResourceManager.get_gpu_memory(gpu_id)
    available = total - used
    
    if available < (required_mb + buffer_mb):
        raise RuntimeError(
            f"Insufficient GPU memory on device {gpu_id}: "
            f"need {required_mb + buffer_mb} MB, have {available} MB"
        )
    
    try:
        yield
    finally:
        # Cleanup
        GPUResourceManager.clear_cache(gpu_id)


# Initialize on import
GPUResourceManager.initialize()
