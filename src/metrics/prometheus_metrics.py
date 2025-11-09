"""
Prometheus metrics integration for JarvisIA V2.

Quick Win 7: Métricas cuantificadas para observabilidad profunda.

Expone métricas en formato Prometheus vía endpoint /metrics:
- Queries per second (throughput)
- Latency percentiles (P50, P95, P99)
- Cache hit rate (embeddings, RAG)
- GPU utilization y VRAM usage
- Error rates por tipo
- Model usage distribution
"""
import os
import logging
import time
import torch
from typing import Optional, Any, Dict
from functools import wraps
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    generate_latest,
    REGISTRY,
    CollectorRegistry
)
from prometheus_client.exposition import choose_encoder
import psutil

logger = logging.getLogger(__name__)


# ============================================================================
# COUNTERS - Valores crecientes (requests, errors, etc.)
# ============================================================================

# Queries totales
queries_total = Counter(
    'jarvis_queries_total',
    'Total number of queries processed',
    ['model', 'status']  # labels: model_id, status (success/error)
)

# Errores por tipo
errors_total = Counter(
    'jarvis_errors_total',
    'Total number of errors',
    ['error_type', 'component']  # labels: OOM/Timeout/ValueError, component
)

# Cache hits/misses
cache_operations = Counter(
    'jarvis_cache_operations_total',
    'Cache operations (hits and misses)',
    ['cache_type', 'operation']  # labels: embeddings/rag, hit/miss
)

# RAG retrievals
rag_retrievals = Counter(
    'jarvis_rag_retrievals_total',
    'Total RAG document retrievals',
    ['search_type']  # labels: dense/sparse/hybrid
)


# ============================================================================
# GAUGES - Valores que suben/bajan (utilización, contadores actuales)
# ============================================================================

# Queries activas
active_queries = Gauge(
    'jarvis_active_queries',
    'Number of queries currently being processed'
)

# GPU utilization
gpu_utilization = Gauge(
    'jarvis_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id', 'gpu_name']
)

# GPU VRAM usage
gpu_vram_used = Gauge(
    'jarvis_gpu_vram_used_bytes',
    'GPU VRAM used in bytes',
    ['gpu_id', 'gpu_name']
)

gpu_vram_total = Gauge(
    'jarvis_gpu_vram_total_bytes',
    'GPU VRAM total in bytes',
    ['gpu_id', 'gpu_name']
)

# CPU usage
cpu_usage_percent = Gauge(
    'jarvis_cpu_usage_percent',
    'CPU usage percentage'
)

# Memory usage
memory_usage_bytes = Gauge(
    'jarvis_memory_usage_bytes',
    'Memory usage in bytes'
)

memory_total_bytes = Gauge(
    'jarvis_memory_total_bytes',
    'Total memory in bytes'
)

# Cache hit rate
cache_hit_rate = Gauge(
    'jarvis_cache_hit_rate',
    'Cache hit rate (0-1)',
    ['cache_type']
)

# Health status
health_status = Gauge(
    'jarvis_health_status',
    'Health status (0=unhealthy, 1=degraded, 2=healthy)'
)

# Model status
model_loaded = Gauge(
    'jarvis_model_loaded',
    'Model loaded status (0=not loaded, 1=loaded)',
    ['model_id']
)

# RAG documents count
rag_documents_count = Gauge(
    'jarvis_rag_documents_count',
    'Number of documents in RAG vectorstore'
)


# ============================================================================
# HISTOGRAMS - Distribuciones (latencias, sizes)
# ============================================================================

# Query latency (buckets para percentiles)
query_latency_seconds = Histogram(
    'jarvis_query_latency_seconds',
    'Query processing latency in seconds',
    ['model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)  # hasta 2 minutos
)

# RAG search latency
rag_search_latency_seconds = Histogram(
    'jarvis_rag_search_latency_seconds',
    'RAG search latency in seconds',
    ['search_type'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0)
)

# Token generation throughput (tokens/s)
tokens_per_second = Histogram(
    'jarvis_tokens_per_second',
    'Token generation throughput (tokens/s)',
    ['model'],
    buckets=(10, 25, 50, 100, 200, 500, 1000)
)

# Query size (tokens)
query_size_tokens = Histogram(
    'jarvis_query_size_tokens',
    'Query size in tokens',
    buckets=(10, 50, 100, 250, 500, 1000, 2000, 4000, 8000)
)

# Response size (tokens)
response_size_tokens = Histogram(
    'jarvis_response_size_tokens',
    'Response size in tokens',
    buckets=(10, 50, 100, 250, 500, 1000, 2000, 4000, 8000)
)


# ============================================================================
# SUMMARIES - Estadísticas (alternativa a histograms, más ligero)
# ============================================================================

# Query processing summary
query_processing_time = Summary(
    'jarvis_query_processing_seconds',
    'Query processing time summary',
    ['model']
)


# ============================================================================
# INFO - Metadata estático
# ============================================================================

jarvis_info = Info(
    'jarvis_build_info',
    'JarvisIA build information'
)

# Setear info inicial (una vez)
jarvis_info.info({
    'version': '2.0',
    'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
    'torch_version': torch.__version__,
    'cuda_available': str(torch.cuda.is_available()),
    'cuda_version': torch.version.cuda if torch.cuda.is_available() else 'N/A'
})


# ============================================================================
# DECORATORS - Instrumentación automática
# ============================================================================

def track_query_metrics(model_id: str = "unknown"):
    """
    Decorator para trackear métricas de queries automáticamente.
    
    Usage:
        @track_query_metrics(model_id="qwen-14b")
        def process_query(query: str) -> str:
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            active_queries.inc()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Success
                queries_total.labels(model=model_id, status='success').inc()
                
                # Latency
                latency = time.time() - start_time
                query_latency_seconds.labels(model=model_id).observe(latency)
                query_processing_time.labels(model=model_id).observe(latency)
                
                return result
            
            except Exception as e:
                # Error
                queries_total.labels(model=model_id, status='error').inc()
                errors_total.labels(
                    error_type=type(e).__name__,
                    component='query_processor'
                ).inc()
                raise
            
            finally:
                active_queries.dec()
        
        return wrapper
    return decorator


def track_rag_search(search_type: str = "dense"):
    """
    Decorator para trackear búsquedas RAG.
    
    Usage:
        @track_rag_search(search_type="hybrid")
        def search_documents(query: str) -> List[Document]:
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Success
                rag_retrievals.labels(search_type=search_type).inc()
                
                # Latency
                latency = time.time() - start_time
                rag_search_latency_seconds.labels(search_type=search_type).observe(latency)
                
                return result
            
            except Exception as e:
                errors_total.labels(
                    error_type=type(e).__name__,
                    component='rag_search'
                ).inc()
                raise
        
        return wrapper
    return decorator


# ============================================================================
# COLLECTORS - Funciones para actualizar métricas periódicamente
# ============================================================================

class MetricsCollector:
    """
    Collector para actualizar métricas del sistema periódicamente.
    
    Se ejecuta en background para mantener gauges actualizados.
    """
    
    def __init__(self, jarvis_instance: Optional[Any] = None):
        """
        Args:
            jarvis_instance: Instancia de Jarvis para acceder a estado
        """
        self.jarvis = jarvis_instance
        logger.info("MetricsCollector initialized")
    
    def collect_system_metrics(self):
        """Actualizar métricas del sistema (CPU, RAM)."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_usage_percent.set(cpu_percent)
            
            # Memory
            memory = psutil.virtual_memory()
            memory_usage_bytes.set(memory.used)
            memory_total_bytes.set(memory.total)
        
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def collect_gpu_metrics(self):
        """Actualizar métricas de GPUs."""
        try:
            if not torch.cuda.is_available():
                return
            
            gpu_count = torch.cuda.device_count()
            
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                gpu_name = props.name
                
                # VRAM
                memory_reserved = torch.cuda.memory_reserved(i)
                memory_total = props.total_memory
                
                gpu_vram_used.labels(gpu_id=str(i), gpu_name=gpu_name).set(memory_reserved)
                gpu_vram_total.labels(gpu_id=str(i), gpu_name=gpu_name).set(memory_total)
                
                # Utilization (aproximado: si hay memoria reservada, GPU está en uso)
                # Nota: Para utilization precisa, usar pynvml (nvidia-ml-py)
                utilization = (memory_reserved / memory_total) * 100 if memory_total > 0 else 0
                gpu_utilization.labels(gpu_id=str(i), gpu_name=gpu_name).set(utilization)
        
        except Exception as e:
            logger.error(f"Failed to collect GPU metrics: {e}")
    
    def collect_health_metrics(self):
        """Actualizar métricas de salud."""
        try:
            if self.jarvis is None:
                return
            
            # Health status (derivado de health API si existe)
            if hasattr(self.jarvis, 'health_api') and self.jarvis.health_api:
                # Simular check rápido
                gpu_ok = torch.cuda.is_available()
                models_ok = hasattr(self.jarvis, 'orchestrator') and self.jarvis.orchestrator is not None
                
                if not gpu_ok or not models_ok:
                    status_value = 0  # unhealthy
                else:
                    status_value = 2  # healthy
                
                health_status.set(status_value)
        
        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")
    
    def collect_model_metrics(self):
        """Actualizar métricas de modelos."""
        try:
            if self.jarvis is None or not hasattr(self.jarvis, 'orchestrator'):
                return
            
            orchestrator = self.jarvis.orchestrator
            
            # Primary model
            if hasattr(orchestrator, 'model') and orchestrator.model is not None:
                model_loaded.labels(model_id='primary').set(1)
            else:
                model_loaded.labels(model_id='primary').set(0)
            
            # Fallback models
            if hasattr(orchestrator, 'fallback_models'):
                for model_id, model in orchestrator.fallback_models.items():
                    if model is not None:
                        model_loaded.labels(model_id=model_id).set(1)
                    else:
                        model_loaded.labels(model_id=model_id).set(0)
        
        except Exception as e:
            logger.error(f"Failed to collect model metrics: {e}")
    
    def collect_rag_metrics(self):
        """Actualizar métricas de RAG."""
        try:
            if self.jarvis is None or not hasattr(self.jarvis, 'embeddings'):
                return
            
            embeddings = self.jarvis.embeddings
            
            if embeddings is None:
                return
            
            # Document count
            if hasattr(embeddings, 'collection') and embeddings.collection is not None:
                try:
                    doc_count = embeddings.collection.count()
                    rag_documents_count.set(doc_count)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Failed to collect RAG metrics: {e}")
    
    def collect_all(self):
        """Actualizar todas las métricas."""
        self.collect_system_metrics()
        self.collect_gpu_metrics()
        self.collect_health_metrics()
        self.collect_model_metrics()
        self.collect_rag_metrics()


# ============================================================================
# ENDPOINT /metrics
# ============================================================================

def get_metrics_response() -> bytes:
    """
    Generar respuesta para endpoint /metrics en formato Prometheus.
    
    Returns:
        bytes: Métricas en formato Prometheus exposition
    """
    return generate_latest(REGISTRY)


def add_metrics_endpoint_to_fastapi(app):
    """
    Agregar endpoint /metrics a una app FastAPI existente.
    
    Args:
        app: FastAPI application instance
    """
    from fastapi import Response
    
    @app.get("/metrics", status_code=200)
    async def metrics():
        """
        Endpoint de métricas Prometheus.
        
        Returns formato Prometheus exposition (text/plain).
        """
        metrics_output = get_metrics_response()
        return Response(
            content=metrics_output,
            media_type="text/plain; charset=utf-8"
        )
    
    logger.info("Metrics endpoint /metrics added to FastAPI app")


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def start_metrics_collector_background(jarvis_instance, interval_seconds: int = 15):
    """
    Iniciar MetricsCollector en background thread.
    
    Args:
        jarvis_instance: Instancia de Jarvis
        interval_seconds: Intervalo de actualización (default: 15s)
    
    Returns:
        threading.Thread con el collector ejecutándose
    """
    import threading
    
    collector = MetricsCollector(jarvis_instance=jarvis_instance)
    
    def collect_loop():
        while True:
            try:
                collector.collect_all()
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
            time.sleep(interval_seconds)
    
    thread = threading.Thread(target=collect_loop, daemon=True, name="MetricsCollector")
    thread.start()
    
    logger.info(f"Metrics collector running in background (interval={interval_seconds}s)")
    return thread


# ============================================================================
# CACHE HIT RATE TRACKER
# ============================================================================

class CacheMetrics:
    """
    Helper para trackear cache hit rate.
    
    Usage:
        cache_metrics = CacheMetrics("embeddings")
        
        def get_embedding(text):
            if text in cache:
                cache_metrics.record_hit()
                return cache[text]
            else:
                cache_metrics.record_miss()
                result = compute_embedding(text)
                cache[text] = result
                return result
    """
    
    def __init__(self, cache_type: str):
        """
        Args:
            cache_type: Tipo de cache ("embeddings", "rag", etc.)
        """
        self.cache_type = cache_type
        self.hits = 0
        self.misses = 0
    
    def record_hit(self):
        """Registrar cache hit."""
        self.hits += 1
        cache_operations.labels(cache_type=self.cache_type, operation='hit').inc()
        self._update_hit_rate()
    
    def record_miss(self):
        """Registrar cache miss."""
        self.misses += 1
        cache_operations.labels(cache_type=self.cache_type, operation='miss').inc()
        self._update_hit_rate()
    
    def _update_hit_rate(self):
        """Actualizar gauge de hit rate."""
        total = self.hits + self.misses
        if total > 0:
            hit_rate_value = self.hits / total
            cache_hit_rate.labels(cache_type=self.cache_type).set(hit_rate_value)
    
    def get_hit_rate(self) -> float:
        """
        Obtener hit rate actual.
        
        Returns:
            float: Hit rate (0-1)
        """
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
