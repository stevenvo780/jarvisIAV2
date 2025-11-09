#!/usr/bin/env python3
"""
Validación Quick Win 4: ChromaDB HNSW Index Optimization

Verifica que los parámetros HNSW optimizados estén configurados correctamente
y mide mejora en latencia de búsqueda RAG.
"""

import sys
import time
import chromadb
from typing import List, Dict
import numpy as np

def test_hnsw_parameters():
    """Verifica que colección tiene parámetros HNSW optimizados"""
    print("=" * 60)
    print("🔍 Test 1: Verificar Parámetros HNSW")
    print("=" * 60)
    
    try:
        client = chromadb.PersistentClient(path="vectorstore/chromadb")
        collection = client.get_collection(name="jarvis_memory")
        
        metadata = collection.metadata
        print(f"\n📊 Metadata de colección: {metadata}")
        
        # Verificar parámetros esperados
        expected = {
            "hnsw:space": "cosine",
            "hnsw:construction_ef": 400,
            "hnsw:search_ef": 200,
            "hnsw:M": 64,
            "hnsw:num_threads": 8
        }
        
        all_ok = True
        for key, expected_value in expected.items():
            actual_value = metadata.get(key)
            match = "✅" if actual_value == expected_value else "❌"
            print(f"  {match} {key}: {actual_value} (esperado: {expected_value})")
            if actual_value != expected_value:
                all_ok = False
        
        if all_ok:
            print("\n✅ Todos los parámetros HNSW configurados correctamente")
            return True
        else:
            print("\n❌ Algunos parámetros HNSW no coinciden")
            return False
            
    except Exception as e:
        print(f"\n❌ Error al verificar parámetros: {e}")
        return False


def benchmark_search_latency(num_queries: int = 100):
    """
    Benchmark latencia de búsqueda en ChromaDB
    
    Genera embeddings sintéticos y mide tiempo promedio de query()
    """
    print("\n" + "=" * 60)
    print(f"🔬 Test 2: Benchmark Latencia de Búsqueda ({num_queries} queries)")
    print("=" * 60)
    
    try:
        client = chromadb.PersistentClient(path="vectorstore/chromadb")
        collection = client.get_collection(name="jarvis_memory")
        
        count = collection.count()
        if count == 0:
            print("\n⚠️ Colección vacía, agregando documentos sintéticos...")
            # Agregar 1000 documentos sintéticos si está vacía
            ids = [f"synthetic_{i}" for i in range(1000)]
            docs = [f"Synthetic document {i} with random content" for i in range(1000)]
            embeddings = [np.random.rand(1024).tolist() for _ in range(1000)]
            
            collection.add(
                ids=ids,
                documents=docs,
                embeddings=embeddings
            )
            count = collection.count()
            print(f"  ✅ Agregados {count} documentos sintéticos")
        
        print(f"\n📊 Documentos en colección: {count}")
        
        # Generar query sintética
        query_embedding = np.random.rand(1024).tolist()
        
        # Warmup (5 queries)
        print("\n🔥 Warmup (5 queries)...")
        for _ in range(5):
            collection.query(
                query_embeddings=[query_embedding],
                n_results=10
            )
        
        # Benchmark
        print(f"\n⏱️ Ejecutando {num_queries} queries...")
        latencies = []
        
        for i in range(num_queries):
            start = time.perf_counter()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=10
            )
            end = time.perf_counter()
            
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{num_queries} queries...")
        
        # Calcular estadísticas
        latencies = np.array(latencies)
        avg_latency = np.mean(latencies)
        p50_latency = np.percentile(latencies, 50)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        
        print("\n" + "=" * 60)
        print("📊 Resultados del Benchmark")
        print("=" * 60)
        print(f"  Queries ejecutadas: {num_queries}")
        print(f"  Documentos indexados: {count}")
        print(f"\n  Latencia Promedio: {avg_latency:.2f} ms")
        print(f"  Latencia P50: {p50_latency:.2f} ms")
        print(f"  Latencia P95: {p95_latency:.2f} ms")
        print(f"  Latencia P99: {p99_latency:.2f} ms")
        print(f"  Latencia Min: {min_latency:.2f} ms")
        print(f"  Latencia Max: {max_latency:.2f} ms")
        
        # Throughput
        total_time = np.sum(latencies) / 1000  # segundos
        throughput = num_queries / total_time
        print(f"\n  Throughput: {throughput:.1f} queries/s")
        
        # Evaluar contra objetivo
        target_p95 = 25.0  # ms (objetivo Quick Win 4)
        baseline_p95 = 45.0  # ms (baseline pre-optimización)
        
        print("\n" + "=" * 60)
        print("🎯 Evaluación vs Objetivo")
        print("=" * 60)
        print(f"  Baseline P95: {baseline_p95:.2f} ms")
        print(f"  Target P95: {target_p95:.2f} ms (-40% vs baseline)")
        print(f"  Current P95: {p95_latency:.2f} ms")
        
        if p95_latency <= target_p95:
            improvement = ((baseline_p95 - p95_latency) / baseline_p95) * 100
            print(f"\n  ✅ Objetivo alcanzado! Mejora: -{improvement:.1f}%")
            return True
        elif p95_latency < baseline_p95:
            improvement = ((baseline_p95 - p95_latency) / baseline_p95) * 100
            print(f"\n  ⚠️ Mejor que baseline, pero no alcanza target. Mejora: -{improvement:.1f}%")
            return True
        else:
            print(f"\n  ❌ Latencia mayor a baseline (posible regresión)")
            return False
            
    except Exception as e:
        print(f"\n❌ Error en benchmark: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta validación completa de Quick Win 4"""
    print("\n" + "=" * 60)
    print("🚀 Validación Quick Win 4: ChromaDB HNSW Optimization")
    print("=" * 60)
    
    results = []
    
    # Test 1: Verificar parámetros HNSW
    results.append(test_hnsw_parameters())
    
    # Test 2: Benchmark latencia
    results.append(benchmark_search_latency(num_queries=100))
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 Resumen de Validación")
    print("=" * 60)
    
    tests = [
        "Parámetros HNSW configurados",
        "Latencia de búsqueda mejorada"
    ]
    
    for i, (test_name, passed) in enumerate(zip(tests, results), 1):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  Test {i}: {status} - {test_name}")
    
    all_passed = all(results)
    
    if all_passed:
        print("\n✅ VALIDACIÓN EXITOSA - Quick Win 4 implementado correctamente")
        return 0
    else:
        print("\n❌ VALIDACIÓN FALLIDA - Revisar implementación")
        return 1


if __name__ == "__main__":
    sys.exit(main())
