"""
API HTTP con healthcheck endpoint para monitoreo de JarvisIA V2.

Quick Win 6: Healthcheck Endpoint para observabilidad proactiva.
"""
import os
import logging
import psutil
import torch
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Modelo de respuesta del healthcheck."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    uptime_seconds: float
    checks: Dict[str, Any]
    version: str = "2.0"


class HealthcheckAPI:
    """
    API HTTP con endpoint /health para monitoreo proactivo.
    
    Verifica:
    - GPU availability y VRAM disponible
    - Modelos cargados (orchestrator)
    - Sistema de embeddings/RAG operacional
    - Espacio en disco suficiente (>10%)
    - Uso de memoria RAM (<90%)
    """
    
    def __init__(self, jarvis_instance: Optional[Any] = None, port: int = 8080):
        """
        Args:
            jarvis_instance: Instancia de Jarvis para verificar estado
            port: Puerto HTTP para el servidor (default: 8080)
        """
        self.jarvis = jarvis_instance
        self.port = port
        self.start_time = datetime.now()
        
        # FastAPI app
        self.app = FastAPI(
            title="JarvisIA V2 Health API",
            description="Healthcheck endpoint for proactive monitoring",
            version="2.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Register routes
        self._register_routes()
        
        logger.info(f"HealthcheckAPI initialized on port {port}")
    
    def _register_routes(self):
        """Registrar endpoints de la API."""
        
        @self.app.get("/health", response_model=HealthStatus, status_code=200)
        async def health_check():
            """
            Endpoint de healthcheck completo.
            
            Returns:
                HealthStatus con estado general y checks individuales
            
            Status codes:
                - 200: Healthy (todos los checks pasan)
                - 503: Degraded/Unhealthy (algún check crítico falla)
            """
            checks = {
                "gpu": self._check_gpu(),
                "models": self._check_models(),
                "rag": self._check_rag(),
                "disk": self._check_disk(),
                "memory": self._check_memory(),
                "jarvis": self._check_jarvis_state()
            }
            
            # Determinar estado general
            critical_failures = [
                not checks["gpu"]["available"],
                not checks["models"]["loaded"],
                checks["disk"]["usage_percent"] > 90,
                checks["memory"]["usage_percent"] > 95
            ]
            
            if any(critical_failures):
                overall_status = "unhealthy"
                response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            elif any([
                checks["gpu"]["vram_usage_percent"] > 90,
                checks["memory"]["usage_percent"] > 90,
                not checks["rag"]["operational"]
            ]):
                overall_status = "degraded"
                response_status = status.HTTP_200_OK  # Degraded but operational
            else:
                overall_status = "healthy"
                response_status = status.HTTP_200_OK
            
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            response = HealthStatus(
                status=overall_status,
                timestamp=datetime.now().isoformat(),
                uptime_seconds=uptime,
                checks=checks
            )
            
            return JSONResponse(
                content=response.dict(),
                status_code=response_status
            )
        
        @self.app.get("/health/live", status_code=200)
        async def liveness_probe():
            """
            Liveness probe (Kubernetes-style).
            
            Retorna 200 si el servicio está activo (process running).
            No verifica disponibilidad de recursos.
            """
            return {"status": "alive", "timestamp": datetime.now().isoformat()}
        
        @self.app.get("/health/ready", status_code=200)
        async def readiness_probe():
            """
            Readiness probe (Kubernetes-style).
            
            Retorna 200 si el servicio está listo para recibir tráfico.
            Verifica recursos críticos (GPU, modelos).
            """
            gpu_ok = self._check_gpu()["available"]
            models_ok = self._check_models()["loaded"]
            
            if gpu_ok and models_ok:
                return {
                    "status": "ready",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return JSONResponse(
                    content={
                        "status": "not_ready",
                        "timestamp": datetime.now().isoformat(),
                        "reason": "GPU or models not available"
                    },
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        
        @self.app.get("/", status_code=200)
        async def root():
            """Root endpoint con información básica."""
            return {
                "service": "JarvisIA V2 Health API",
                "version": "2.0",
                "endpoints": {
                    "health": "/health",
                    "liveness": "/health/live",
                    "readiness": "/health/ready",
                    "docs": "/docs"
                }
            }
    
    def _check_gpu(self) -> Dict[str, Any]:
        """Verificar disponibilidad de GPUs y VRAM."""
        try:
            if not torch.cuda.is_available():
                return {
                    "available": False,
                    "count": 0,
                    "reason": "CUDA not available"
                }
            
            gpu_count = torch.cuda.device_count()
            gpus = []
            
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                memory_allocated = torch.cuda.memory_allocated(i) / (1024**3)  # GB
                memory_reserved = torch.cuda.memory_reserved(i) / (1024**3)  # GB
                memory_total = props.total_memory / (1024**3)  # GB
                memory_free = memory_total - memory_reserved
                memory_usage_percent = (memory_reserved / memory_total) * 100
                
                gpus.append({
                    "id": i,
                    "name": props.name,
                    "memory_total_gb": round(memory_total, 2),
                    "memory_used_gb": round(memory_reserved, 2),
                    "memory_free_gb": round(memory_free, 2),
                    "memory_usage_percent": round(memory_usage_percent, 2),
                    "allocated_gb": round(memory_allocated, 2)
                })
            
            # VRAM usage promedio
            avg_vram_usage = sum(g["memory_usage_percent"] for g in gpus) / len(gpus)
            
            return {
                "available": True,
                "count": gpu_count,
                "gpus": gpus,
                "vram_usage_percent": round(avg_vram_usage, 2)
            }
        
        except Exception as e:
            logger.error(f"GPU check failed: {e}")
            return {
                "available": False,
                "count": 0,
                "error": str(e)
            }
    
    def _check_models(self) -> Dict[str, Any]:
        """Verificar si modelos están cargados en el orchestrator."""
        try:
            if self.jarvis is None:
                return {"loaded": False, "reason": "Jarvis instance not provided"}
            
            if not hasattr(self.jarvis, 'orchestrator'):
                return {"loaded": False, "reason": "Orchestrator not found"}
            
            orchestrator = self.jarvis.orchestrator
            
            # Verificar modelo principal (Qwen)
            primary_loaded = hasattr(orchestrator, 'model') and orchestrator.model is not None
            
            # Verificar si hay modelos en fallback_models
            fallback_count = 0
            if hasattr(orchestrator, 'fallback_models'):
                fallback_count = len([m for m in orchestrator.fallback_models.values() if m is not None])
            
            return {
                "loaded": primary_loaded,
                "primary_model": primary_loaded,
                "fallback_models_count": fallback_count,
                "total_models": 1 + fallback_count if primary_loaded else fallback_count
            }
        
        except Exception as e:
            logger.error(f"Models check failed: {e}")
            return {
                "loaded": False,
                "error": str(e)
            }
    
    def _check_rag(self) -> Dict[str, Any]:
        """Verificar sistema de embeddings/RAG."""
        try:
            if self.jarvis is None:
                return {"operational": False, "reason": "Jarvis instance not provided"}
            
            if not hasattr(self.jarvis, 'embeddings'):
                return {"operational": False, "reason": "Embeddings not found"}
            
            embeddings = self.jarvis.embeddings
            
            if embeddings is None:
                return {"operational": False, "reason": "Embeddings disabled (ENABLE_RAG=false)"}
            
            # Verificar ChromaDB collection
            chroma_ok = hasattr(embeddings, 'collection') and embeddings.collection is not None
            
            # Verificar modelo de embeddings
            model_ok = hasattr(embeddings, 'model') and embeddings.model is not None
            
            # Conteo de documentos en la colección
            doc_count = 0
            if chroma_ok:
                try:
                    doc_count = embeddings.collection.count()
                except:
                    pass
            
            return {
                "operational": chroma_ok and model_ok,
                "chromadb_ok": chroma_ok,
                "model_ok": model_ok,
                "documents_count": doc_count
            }
        
        except Exception as e:
            logger.error(f"RAG check failed: {e}")
            return {
                "operational": False,
                "error": str(e)
            }
    
    def _check_disk(self) -> Dict[str, Any]:
        """Verificar espacio en disco."""
        try:
            disk = psutil.disk_usage('/')
            
            return {
                "available": True,
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "usage_percent": disk.percent
            }
        
        except Exception as e:
            logger.error(f"Disk check failed: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_memory(self) -> Dict[str, Any]:
        """Verificar uso de memoria RAM."""
        try:
            memory = psutil.virtual_memory()
            
            return {
                "available": True,
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.available / (1024**3), 2),
                "usage_percent": memory.percent
            }
        
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_jarvis_state(self) -> Dict[str, Any]:
        """Verificar estado interno de Jarvis."""
        try:
            if self.jarvis is None:
                return {"running": False, "reason": "Jarvis instance not provided"}
            
            if not hasattr(self.jarvis, 'state'):
                return {"running": False, "reason": "State not found"}
            
            state = self.jarvis.state
            
            return {
                "running": state.running,
                "voice_active": state.voice_active,
                "listening_active": state.listening_active,
                "error_count": state.error_count,
                "max_errors": state.max_errors
            }
        
        except Exception as e:
            logger.error(f"Jarvis state check failed: {e}")
            return {
                "running": False,
                "error": str(e)
            }
    
    def run(self, host: str = "0.0.0.0"):
        """
        Iniciar servidor HTTP (bloqueante).
        
        Args:
            host: Host a escuchar (default: 0.0.0.0 para aceptar conexiones externas)
        """
        import uvicorn
        
        logger.info(f"Starting Health API on {host}:{self.port}")
        uvicorn.run(self.app, host=host, port=self.port, log_level="info")
    
    def run_in_background(self, host: str = "0.0.0.0"):
        """
        Iniciar servidor HTTP en thread separado (no bloqueante).
        
        Args:
            host: Host a escuchar
        
        Returns:
            threading.Thread con el servidor ejecutándose
        """
        import threading
        
        def run_server():
            import uvicorn
            uvicorn.run(self.app, host=host, port=self.port, log_level="warning")
        
        thread = threading.Thread(target=run_server, daemon=True, name="HealthAPI")
        thread.start()
        
        logger.info(f"Health API running in background on {host}:{self.port}")
        return thread


# Función de utilidad para integrar en main.py
def start_healthcheck_api(jarvis_instance, port: int = 8080, background: bool = True):
    """
    Helper para iniciar el Health API desde main.py.
    
    Args:
        jarvis_instance: Instancia de Jarvis
        port: Puerto HTTP
        background: Si True, ejecuta en thread (no bloqueante)
    
    Returns:
        HealthcheckAPI instance
    """
    api = HealthcheckAPI(jarvis_instance=jarvis_instance, port=port)
    
    if background:
        api.run_in_background()
    else:
        api.run()  # Bloqueante
    
    return api
