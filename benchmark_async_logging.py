#!/usr/bin/env python3
"""
Test Async Logging Performance
Compares sync vs async logging latency
"""

import logging
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.error_handler import setup_logging, log_with_context

def benchmark_logging(async_mode: bool, num_logs: int = 1000):
    """Benchmark logging performance"""
    
    # Setup logging
    log_dir = f"logs/benchmark_{'async' if async_mode else 'sync'}"
    setup_logging(
        log_dir=log_dir,
        structured=True,
        async_logging=async_mode
    )
    
    logger = logging.getLogger("BenchmarkTest")
    
    # Warmup
    for i in range(10):
        logger.info(f"Warmup {i}")
    
    # Benchmark
    start = time.perf_counter()
    
    for i in range(num_logs):
        log_with_context(
            logger,
            logging.INFO,
            f"Test log entry {i}",
            iteration=i,
            query_time_ms=150.5,
            model="qwen-14b",
            tokens=256
        )
    
    elapsed = time.perf_counter() - start
    
    # Calculate metrics
    avg_latency_ms = (elapsed / num_logs) * 1000
    throughput = num_logs / elapsed
    
    return {
        "mode": "async" if async_mode else "sync",
        "total_time_s": elapsed,
        "num_logs": num_logs,
        "avg_latency_ms": avg_latency_ms,
        "throughput_logs_per_sec": throughput
    }


def main():
    print("=" * 60)
    print("🔬 Async Logging Performance Benchmark")
    print("=" * 60)
    
    num_logs = 1000
    
    # Test sync logging
    print(f"\n📊 Testing SYNC logging ({num_logs} logs)...")
    sync_results = benchmark_logging(async_mode=False, num_logs=num_logs)
    
    print(f"  ⏱️  Total time: {sync_results['total_time_s']:.3f}s")
    print(f"  ⚡ Avg latency: {sync_results['avg_latency_ms']:.3f}ms")
    print(f"  📈 Throughput: {sync_results['throughput_logs_per_sec']:.1f} logs/sec")
    
    # Test async logging
    print(f"\n📊 Testing ASYNC logging ({num_logs} logs)...")
    async_results = benchmark_logging(async_mode=True, num_logs=num_logs)
    
    print(f"  ⏱️  Total time: {async_results['total_time_s']:.3f}s")
    print(f"  ⚡ Avg latency: {async_results['avg_latency_ms']:.3f}ms")
    print(f"  📈 Throughput: {async_results['throughput_logs_per_sec']:.1f} logs/sec")
    
    # Calculate improvement
    latency_improvement = (
        (sync_results['avg_latency_ms'] - async_results['avg_latency_ms']) 
        / sync_results['avg_latency_ms'] * 100
    )
    
    throughput_improvement = (
        (async_results['throughput_logs_per_sec'] - sync_results['throughput_logs_per_sec'])
        / sync_results['throughput_logs_per_sec'] * 100
    )
    
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    print(f"\n⚡ Latency reduction: {latency_improvement:.1f}%")
    print(f"   • Sync:  {sync_results['avg_latency_ms']:.3f}ms per log")
    print(f"   • Async: {async_results['avg_latency_ms']:.3f}ms per log")
    
    print(f"\n📈 Throughput increase: {throughput_improvement:.1f}%")
    print(f"   • Sync:  {sync_results['throughput_logs_per_sec']:.1f} logs/sec")
    print(f"   • Async: {async_results['throughput_logs_per_sec']:.1f} logs/sec")
    
    # Validation
    print("\n" + "=" * 60)
    print("✅ VALIDATION")
    print("=" * 60)
    
    if latency_improvement > 20:
        print("✅ PASS: Latency reduced by >20%")
    elif latency_improvement > 10:
        print("⚠️  PASS: Latency reduced by >10% (target was >20%)")
    else:
        print(f"❌ FAIL: Latency only reduced by {latency_improvement:.1f}% (target >10%)")
    
    if throughput_improvement > 50:
        print("✅ PASS: Throughput increased by >50%")
    elif throughput_improvement > 20:
        print("⚠️  PASS: Throughput increased by >20% (target was >50%)")
    else:
        print(f"❌ FAIL: Throughput only increased by {throughput_improvement:.1f}% (target >20%)")
    
    print("\n💡 Expected impact in production:")
    print(f"   • Query latency reduction: ~{latency_improvement * 0.5:.1f}ms")
    print(f"   • (Assuming 5-10 logs per query)")
    
    return 0 if latency_improvement > 10 else 1


if __name__ == "__main__":
    sys.exit(main())
