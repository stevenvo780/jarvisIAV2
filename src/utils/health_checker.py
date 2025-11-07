"""
Health Check System - Monitor component health and system status
"""

import logging
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'component': self.component,
            'status': self.status.value,
            'message': self.message,
            'latency_ms': round(self.latency_ms, 2),
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


class HealthChecker:
    """
    Centralized health check system
    
    Features:
    - Component registration
    - Periodic health checks
    - Status aggregation
    - Detailed reporting
    
    Usage:
        checker = HealthChecker()
        
        # Register components
        checker.register("gpu", check_gpu_health)
        checker.register("models", check_models_health)
        
        # Get overall status
        status = checker.check_all()
        print(f"System: {status['overall_status']}")
    """
    
    def __init__(self):
        """Initialize health checker"""
        self.logger = logging.getLogger("HealthChecker")
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self._lock = Lock()
    
    def register(self, component: str, check_func: Callable[[], HealthCheckResult]):
        """
        Register a health check
        
        Args:
            component: Component name
            check_func: Function that returns HealthCheckResult
        """
        with self._lock:
            self.checks[component] = check_func
            self.logger.info(f"Registered health check: {component}")
    
    def unregister(self, component: str):
        """Unregister a health check"""
        with self._lock:
            if component in self.checks:
                del self.checks[component]
                self.logger.info(f"Unregistered health check: {component}")
    
    def check_component(self, component: str) -> Optional[HealthCheckResult]:
        """
        Check single component health
        
        Args:
            component: Component name
        
        Returns:
            HealthCheckResult or None if not registered
        """
        check_func = self.checks.get(component)
        if not check_func:
            self.logger.warning(f"Component not registered: {component}")
            return None
        
        start = time.time()
        try:
            result = check_func()
            result.latency_ms = (time.time() - start) * 1000
            
            with self._lock:
                self.last_results[component] = result
            
            return result
        
        except Exception as e:
            self.logger.error(f"Health check failed for {component}: {e}")
            
            result = HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                latency_ms=(time.time() - start) * 1000,
                metadata={'error': str(e)}
            )
            
            with self._lock:
                self.last_results[component] = result
            
            return result
    
    def check_all(self) -> Dict:
        """
        Check all registered components
        
        Returns:
            Dictionary with overall status and component details
        """
        results = {}
        
        for component in list(self.checks.keys()):
            result = self.check_component(component)
            if result:
                results[component] = result.to_dict()
        
        # Determine overall status
        overall = self._calculate_overall_status(results)
        
        return {
            'overall_status': overall.value,
            'components': results,
            'timestamp': time.time(),
            'healthy_count': sum(1 for r in results.values() if r['status'] == 'healthy'),
            'total_count': len(results)
        }
    
    def _calculate_overall_status(self, results: Dict) -> HealthStatus:
        """Calculate overall system status from component results"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [HealthStatus(r['status']) for r in results.values()]
        
        # If any unhealthy, system is unhealthy
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        
        # If any degraded, system is degraded
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        
        # All healthy
        return HealthStatus.HEALTHY
    
    def is_healthy(self) -> bool:
        """
        Quick health check
        
        Returns:
            True if all components healthy, False otherwise
        """
        status = self.check_all()
        return status['overall_status'] == HealthStatus.HEALTHY.value
    
    def get_summary(self) -> str:
        """
        Get human-readable health summary
        
        Returns:
            Summary string
        """
        status = self.check_all()
        
        lines = [
            f"System Health: {status['overall_status'].upper()}",
            f"Components: {status['healthy_count']}/{status['total_count']} healthy",
            ""
        ]
        
        for component, result in status['components'].items():
            emoji = "✅" if result['status'] == 'healthy' else "⚠️" if result['status'] == 'degraded' else "❌"
            lines.append(f"{emoji} {component}: {result['message']}")
        
        return "\n".join(lines)


# Pre-built health checks

def check_gpu_health() -> HealthCheckResult:
    """Check GPU health"""
    try:
        import torch
        
        if not torch.cuda.is_available():
            return HealthCheckResult(
                component="gpu",
                status=HealthStatus.UNHEALTHY,
                message="CUDA not available"
            )
        
        gpu_count = torch.cuda.device_count()
        
        # Check GPU temperature if possible
        try:
            import pynvml
            pynvml.nvmlInit()
            
            max_temp = 0
            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
                max_temp = max(max_temp, temp)
            
            if max_temp > 85:
                return HealthCheckResult(
                    component="gpu",
                    status=HealthStatus.DEGRADED,
                    message=f"GPU temperature high: {max_temp}°C",
                    metadata={'temperature': max_temp, 'gpu_count': gpu_count}
                )
        except:
            pass
        
        return HealthCheckResult(
            component="gpu",
            status=HealthStatus.HEALTHY,
            message=f"{gpu_count} GPU(s) available",
            metadata={'gpu_count': gpu_count}
        )
    
    except Exception as e:
        return HealthCheckResult(
            component="gpu",
            status=HealthStatus.UNHEALTHY,
            message=f"GPU check failed: {str(e)}"
        )


def check_disk_health(threshold_percent: int = 90) -> HealthCheckResult:
    """Check disk space health"""
    try:
        import shutil
        
        total, used, free = shutil.disk_usage("/")
        percent_used = (used / total) * 100
        
        if percent_used >= threshold_percent:
            return HealthCheckResult(
                component="disk",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk {percent_used:.1f}% full",
                metadata={'percent_used': percent_used, 'free_gb': free // (2**30)}
            )
        elif percent_used >= threshold_percent * 0.8:
            return HealthCheckResult(
                component="disk",
                status=HealthStatus.DEGRADED,
                message=f"Disk {percent_used:.1f}% full",
                metadata={'percent_used': percent_used, 'free_gb': free // (2**30)}
            )
        else:
            return HealthCheckResult(
                component="disk",
                status=HealthStatus.HEALTHY,
                message=f"Disk {percent_used:.1f}% used",
                metadata={'percent_used': percent_used, 'free_gb': free // (2**30)}
            )
    
    except Exception as e:
        return HealthCheckResult(
            component="disk",
            status=HealthStatus.UNKNOWN,
            message=f"Disk check failed: {str(e)}"
        )


def check_memory_health(threshold_percent: int = 90) -> HealthCheckResult:
    """Check system memory health"""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        percent_used = memory.percent
        
        if percent_used >= threshold_percent:
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory {percent_used:.1f}% used",
                metadata={'percent_used': percent_used, 'available_gb': memory.available // (2**30)}
            )
        elif percent_used >= threshold_percent * 0.8:
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.DEGRADED,
                message=f"Memory {percent_used:.1f}% used",
                metadata={'percent_used': percent_used, 'available_gb': memory.available // (2**30)}
            )
        else:
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.HEALTHY,
                message=f"Memory {percent_used:.1f}% used",
                metadata={'percent_used': percent_used, 'available_gb': memory.available // (2**30)}
            )
    
    except Exception as e:
        return HealthCheckResult(
            component="memory",
            status=HealthStatus.UNKNOWN,
            message=f"Memory check failed: {str(e)}"
        )


def create_model_health_check(backend) -> Callable[[], HealthCheckResult]:
    """Create health check for model backend"""
    def check():
        try:
            if hasattr(backend, 'is_healthy') and callable(backend.is_healthy):
                is_healthy = backend.is_healthy()
                
                stats = backend.get_stats() if hasattr(backend, 'get_stats') else {}
                
                if is_healthy:
                    return HealthCheckResult(
                        component="models",
                        status=HealthStatus.HEALTHY,
                        message=f"Backend operational",
                        metadata=stats
                    )
                else:
                    return HealthCheckResult(
                        component="models",
                        status=HealthStatus.UNHEALTHY,
                        message="Backend not healthy",
                        metadata=stats
                    )
            else:
                return HealthCheckResult(
                    component="models",
                    status=HealthStatus.UNKNOWN,
                    message="Health check not supported"
                )
        
        except Exception as e:
            return HealthCheckResult(
                component="models",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}"
            )
    
    return check
