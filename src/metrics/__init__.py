"""Metrics module for JarvisIA V2 - Prometheus integration."""
from .prometheus_metrics import (
    # Decorators
    track_query_metrics,
    track_rag_search,
    
    # Collectors
    MetricsCollector,
    CacheMetrics,
    
    # Integration helpers
    add_metrics_endpoint_to_fastapi,
    start_metrics_collector_background,
    get_metrics_response,
    
    # Métricas individuales (para uso directo)
    queries_total,
    errors_total,
    cache_operations,
    rag_retrievals,
    active_queries,
    gpu_utilization,
    gpu_vram_used,
    gpu_vram_total,
    cpu_usage_percent,
    memory_usage_bytes,
    memory_total_bytes,
    cache_hit_rate,
    health_status,
    model_loaded,
    rag_documents_count,
    query_latency_seconds,
    rag_search_latency_seconds,
    tokens_per_second,
    query_size_tokens,
    response_size_tokens,
    query_processing_time,
    jarvis_info
)

__all__ = [
    "track_query_metrics",
    "track_rag_search",
    "MetricsCollector",
    "CacheMetrics",
    "add_metrics_endpoint_to_fastapi",
    "start_metrics_collector_background",
    "get_metrics_response",
    "queries_total",
    "errors_total",
    "cache_operations",
    "rag_retrievals",
    "active_queries",
    "gpu_utilization",
    "gpu_vram_used",
    "gpu_vram_total",
    "cpu_usage_percent",
    "memory_usage_bytes",
    "memory_total_bytes",
    "cache_hit_rate",
    "health_status",
    "model_loaded",
    "rag_documents_count",
    "query_latency_seconds",
    "rag_search_latency_seconds",
    "tokens_per_second",
    "query_size_tokens",
    "response_size_tokens",
    "query_processing_time",
    "jarvis_info"
]
