"""
Metrics Tracker - Performance monitoring for Jarvis IA V2
Tracks latency, VRAM usage, costs, and model performance
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import time

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False


@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query: str
    model_used: str
    difficulty: int
    latency: float  # seconds
    tokens_generated: int
    vram_used: Dict[int, int]  # {gpu_id: mb}
    cost: float  # USD
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'query': self.query[:100],  # Truncate for privacy
            'model': self.model_used,
            'difficulty': self.difficulty,
            'latency': round(self.latency, 3),
            'tokens': self.tokens_generated,
            'vram': self.vram_used,
            'cost': round(self.cost, 6),
            'timestamp': self.timestamp,
            'success': self.success,
            'error': self.error
        }


class MetricsTracker:
    """
    Performance metrics tracker for Jarvis
    
    Features:
    - Query latency tracking
    - VRAM usage monitoring
    - API cost tracking
    - Model usage statistics
    - Session summaries
    - JSONL logging
    """
    
    def __init__(
        self,
        log_path: str = "logs/metrics.jsonl",
        enable_gpu_monitoring: bool = True
    ):
        self.logger = logging.getLogger("MetricsTracker")
        self.log_path = log_path
        self.enable_gpu_monitoring = enable_gpu_monitoring
        self.session_metrics: List[QueryMetrics] = []
        
        # Initialize GPU monitoring
        self.gpu_count = 0
        if enable_gpu_monitoring and PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_count = pynvml.nvmlDeviceGetCount()
                self.logger.info(f"✅ GPU monitoring enabled ({self.gpu_count} GPUs)")
            except Exception as e:
                self.logger.warning(f"GPU monitoring failed: {e}")
                self.enable_gpu_monitoring = False
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        self.logger.info("✅ MetricsTracker initialized")
    
    def _get_gpu_memory(self) -> Dict[int, int]:
        """Get current VRAM usage for all GPUs"""
        if not self.enable_gpu_monitoring or not PYNVML_AVAILABLE:
            return {}
        
        vram = {}
        try:
            for i in range(self.gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                vram[i] = info.used // 1024**2  # Convert to MB
        except Exception as e:
            self.logger.warning(f"Failed to get GPU memory: {e}")
        
        return vram
    
    def track_query(
        self,
        query: str,
        model: str,
        difficulty: int,
        latency: float,
        tokens: int = 0,
        cost: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Track a query execution
        
        Args:
            query: User query text
            model: Model name used
            difficulty: Estimated difficulty (1-100)
            latency: Execution time in seconds
            tokens: Tokens generated
            cost: API cost in USD
            success: Whether query succeeded
            error: Error message if failed
        """
        # Capture VRAM
        vram = self._get_gpu_memory()
        
        # Create metrics object
        metrics = QueryMetrics(
            query=query,
            model_used=model,
            difficulty=difficulty,
            latency=latency,
            tokens_generated=tokens,
            vram_used=vram,
            cost=cost,
            success=success,
            error=error
        )
        
        # Add to session
        self.session_metrics.append(metrics)
        
        # Log to file
        self._log_metric(metrics)
        
        # Log summary
        status = "✅" if success else "❌"
        self.logger.info(
            f"{status} Query tracked: model={model}, latency={latency:.2f}s, "
            f"cost=${cost:.4f}"
        )
    
    def _log_metric(self, metric: QueryMetrics):
        """Write metric to JSONL file"""
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metric.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to log metric: {e}")
    
    def get_session_stats(self) -> Dict:
        """Get statistics for current session"""
        if not self.session_metrics:
            return {
                'total_queries': 0,
                'success_rate': 0.0,
                'avg_latency': 0.0,
                'total_tokens': 0,
                'total_cost': 0.0,
                'model_usage': {}
            }
        
        total_queries = len(self.session_metrics)
        successful = sum(1 for m in self.session_metrics if m.success)
        total_latency = sum(m.latency for m in self.session_metrics)
        total_tokens = sum(m.tokens_generated for m in self.session_metrics)
        total_cost = sum(m.cost for m in self.session_metrics)
        
        # Model usage breakdown
        model_usage = {}
        for m in self.session_metrics:
            model = m.model_used
            if model not in model_usage:
                model_usage[model] = {
                    'count': 0,
                    'total_latency': 0.0,
                    'total_cost': 0.0,
                    'failures': 0
                }
            
            model_usage[model]['count'] += 1
            model_usage[model]['total_latency'] += m.latency
            model_usage[model]['total_cost'] += m.cost
            if not m.success:
                model_usage[model]['failures'] += 1
        
        # Calculate averages for each model
        for model, stats in model_usage.items():
            stats['avg_latency'] = round(stats['total_latency'] / stats['count'], 3)
            stats['avg_cost'] = round(stats['total_cost'] / stats['count'], 6)
        
        return {
            'total_queries': total_queries,
            'successful_queries': successful,
            'failed_queries': total_queries - successful,
            'success_rate': round(successful / total_queries * 100, 1),
            'avg_latency': round(total_latency / total_queries, 3),
            'total_tokens': total_tokens,
            'total_cost': round(total_cost, 4),
            'model_usage': model_usage
        }
    
    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_session_stats()
        
        print("\n" + "="*60)
        print("📊 JARVIS SESSION STATISTICS")
        print("="*60)
        
        if stats['total_queries'] == 0:
            print("No queries tracked yet.")
            print("="*60 + "\n")
            return
        
        print(f"Total Queries: {stats['total_queries']}")
        print(f"Success Rate: {stats['success_rate']}% "
              f"({stats['successful_queries']}/{stats['total_queries']})")
        print(f"Avg Latency: {stats['avg_latency']}s")
        print(f"Total Tokens: {stats['total_tokens']}")
        print(f"Total Cost: ${stats['total_cost']}")
        
        print("\n" + "-"*60)
        print("Model Usage:")
        print("-"*60)
        
        for model, model_stats in stats['model_usage'].items():
            print(f"\n{model}:")
            print(f"  Queries: {model_stats['count']}")
            print(f"  Avg Latency: {model_stats['avg_latency']}s")
            print(f"  Avg Cost: ${model_stats['avg_cost']}")
            if model_stats['failures'] > 0:
                print(f"  ⚠️  Failures: {model_stats['failures']}")
        
        print("\n" + "="*60 + "\n")
    
    def get_cost_breakdown(self) -> Dict:
        """Get detailed cost breakdown"""
        breakdown = {
            'total_cost': 0.0,
            'by_model': {},
            'by_date': {}
        }
        
        for metric in self.session_metrics:
            # Total
            breakdown['total_cost'] += metric.cost
            
            # By model
            model = metric.model_used
            if model not in breakdown['by_model']:
                breakdown['by_model'][model] = 0.0
            breakdown['by_model'][model] += metric.cost
            
            # By date
            date = metric.timestamp[:10]  # YYYY-MM-DD
            if date not in breakdown['by_date']:
                breakdown['by_date'][date] = 0.0
            breakdown['by_date'][date] += metric.cost
        
        return breakdown
    
    def reset_session(self):
        """Reset session metrics"""
        self.session_metrics = []
        self.logger.info("Session metrics reset")
    
    def __del__(self):
        """Cleanup"""
        if self.enable_gpu_monitoring and PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except:
                pass


# Context manager for automatic timing
class QueryTimer:
    """Context manager for automatic query timing"""
    
    def __init__(
        self,
        tracker: MetricsTracker,
        query: str,
        model: str,
        difficulty: int,
        cost: float = 0.0
    ):
        self.tracker = tracker
        self.query = query
        self.model = model
        self.difficulty = difficulty
        self.cost = cost
        self.start_time = None
        self.success = True
        self.error = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        
        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)
        
        self.tracker.track_query(
            query=self.query,
            model=self.model,
            difficulty=self.difficulty,
            latency=latency,
            cost=self.cost,
            success=self.success,
            error=self.error
        )
        
        # ✅ Save last response time for Learning Manager
        self.tracker.last_response_time = latency
        
        # Don't suppress exceptions
        return False
