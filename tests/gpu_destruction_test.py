#!/usr/bin/env python3
"""
🔥 GPU DESTRUCTION TEST - JARVIS IA V2
=======================================

Este test está diseñado específicamente para SATURAR la GPU:
- Múltiples requests simultáneos al modelo
- Prompts largos y complejos
- Intentar llenar completamente la VRAM
- Forzar OOM (Out of Memory) errors
- Medir degradación de rendimiento bajo carga

⚠️  ADVERTENCIA: Puede hacer crash al driver de NVIDIA
⚠️  Tu GPU puede llegar a temperaturas altas
"""

import requests
import threading
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

BASE_URL = "http://localhost:8090"

stats = {
    "total": 0,
    "success": 0,
    "failed": 0,
    "timeouts": 0,
    "oom_errors": 0,
    "response_times": []
}
lock = threading.Lock()

def log(msg, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "WARNING": "\033[93m", "ERROR": "\033[91m", "CRITICAL": "\033[95m", "RESET": "\033[0m"}
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{colors.get(level, '')}{ts} [{level}] {msg}{colors['RESET']}")

def update_stats(success=True, response_time=None, timeout=False, oom=False):
    with lock:
        stats["total"] += 1
        if success:
            stats["success"] += 1
            if response_time:
                stats["response_times"].append(response_time)
        else:
            stats["failed"] += 1
        if timeout:
            stats["timeouts"] += 1
        if oom:
            stats["oom_errors"] += 1

# Prompts diseñados para consumir mucha VRAM
HEAVY_PROMPTS = [
    "Escribe una historia épica de fantasía de 5000 palabras con personajes complejos, descripciones detalladas del mundo, diálogos profundos y múltiples arcos narrativos entrelazados.",
    "Genera un análisis completo y exhaustivo de la teoría de la relatividad de Einstein, incluyendo todas las ecuaciones, ejemplos prácticos, experimentos históricos, aplicaciones modernas y sus implicaciones filosóficas.",
    "Crea un tutorial paso a paso extremadamente detallado sobre cómo construir un sistema operativo desde cero, incluyendo boot loader, kernel, sistema de archivos, drivers, shell y aplicaciones básicas.",
    "Explica en profundidad todos los conceptos de machine learning, deep learning, redes neuronales, transformers, attention mechanisms, backpropagation, optimizadores y regularización con ejemplos de código.",
    "Escribe un análisis literario completo de todas las obras de Shakespeare, incluyendo contexto histórico, análisis de personajes, temas recurrentes, estilo literario y su influencia en la literatura moderna.",
]

def generate_extreme_prompt():
    """Generar un prompt extremadamente largo y complejo"""
    base = random.choice(HEAVY_PROMPTS)
    # Agregar más contexto para hacerlo más pesado
    additions = [
        " Incluye todos los detalles posibles.",
        " Sé extremadamente específico y exhaustivo.",
        " Proporciona ejemplos para cada punto.",
        " Explica desde los fundamentos hasta conceptos avanzados.",
        " No omitas ningún detalle, por pequeño que sea.",
    ]
    return base + "".join(random.sample(additions, k=3))

# ===========================================================================
# TEST 1: GPU Saturation - Llenar completamente la GPU
# ===========================================================================

def test_gpu_saturation(num_parallel=10):
    """Enviar múltiples requests pesados en paralelo para saturar GPU"""
    log(f"🔥 TEST 1: GPU SATURATION - {num_parallel} requests pesados simultáneos", "CRITICAL")

    def heavy_request(req_id):
        prompt = generate_extreme_prompt()
        log(f"  Request {req_id} iniciado ({len(prompt)} chars)", "INFO")

        start = time.time()
        try:
            r = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": prompt},
                timeout=600  # 10 minutos
            )
            elapsed = time.time() - start

            if r.status_code == 200:
                response_len = len(r.json().get("response", ""))
                log(f"  Request {req_id} completado: {elapsed:.1f}s, {response_len} chars", "SUCCESS")
                update_stats(True, elapsed)
            else:
                log(f"  Request {req_id} falló: Status {r.status_code}", "ERROR")
                update_stats(False)

        except requests.exceptions.Timeout:
            log(f"  Request {req_id} TIMEOUT después de 10 minutos", "WARNING")
            update_stats(False, timeout=True)
        except Exception as e:
            error_str = str(e).lower()
            if "out of memory" in error_str or "oom" in error_str or "cuda" in error_str:
                log(f"  Request {req_id} OOM ERROR: {e}", "CRITICAL")
                update_stats(False, oom=True)
            else:
                log(f"  Request {req_id} ERROR: {e}", "ERROR")
                update_stats(False)

    with ThreadPoolExecutor(max_workers=num_parallel) as executor:
        futures = [executor.submit(heavy_request, i) for i in range(num_parallel)]
        for future in as_completed(futures):
            future.result()

    log("✅ GPU Saturation test completed", "SUCCESS")

# ===========================================================================
# TEST 2: Sequential Pressure - Presión sostenida
# ===========================================================================

def test_sequential_pressure(num_requests=50):
    """Enviar requests pesados uno tras otro sin descanso"""
    log(f"🔥 TEST 2: SEQUENTIAL PRESSURE - {num_requests} requests pesados consecutivos", "CRITICAL")

    for i in range(num_requests):
        prompt = generate_extreme_prompt()
        log(f"  Request {i+1}/{num_requests} iniciado", "INFO")

        start = time.time()
        try:
            r = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": prompt},
                timeout=600
            )
            elapsed = time.time() - start

            if r.status_code == 200:
                log(f"  Request {i+1} OK: {elapsed:.1f}s", "SUCCESS")
                update_stats(True, elapsed)

                # Monitorear degradación de rendimiento
                if stats["response_times"]:
                    avg_time = sum(stats["response_times"]) / len(stats["response_times"])
                    if elapsed > avg_time * 1.5:
                        log(f"  ⚠️  Degradación detectada: {elapsed:.1f}s vs avg {avg_time:.1f}s", "WARNING")
            else:
                update_stats(False)

        except requests.exceptions.Timeout:
            log(f"  Request {i+1} TIMEOUT", "WARNING")
            update_stats(False, timeout=True)
        except Exception as e:
            if "out of memory" in str(e).lower():
                log(f"  Request {i+1} OOM: {e}", "CRITICAL")
                update_stats(False, oom=True)
                log("  🛑 Deteniendo test por OOM", "CRITICAL")
                break
            else:
                log(f"  Request {i+1} ERROR: {e}", "ERROR")
                update_stats(False)

    log("✅ Sequential Pressure test completed", "SUCCESS")

# ===========================================================================
# TEST 3: Burst Wave - Olas de requests
# ===========================================================================

def test_burst_wave(num_waves=5, requests_per_wave=20):
    """Enviar olas de requests para ver cómo se recupera el sistema"""
    log(f"🔥 TEST 3: BURST WAVE - {num_waves} olas de {requests_per_wave} requests", "CRITICAL")

    for wave in range(num_waves):
        log(f"  🌊 Wave {wave+1}/{num_waves} iniciando", "WARNING")

        def wave_request(req_id):
            try:
                r = requests.post(
                    f"{BASE_URL}/api/chat",
                    json={"message": generate_extreme_prompt()},
                    timeout=300
                )
                update_stats(r.status_code == 200, time.time())
            except:
                update_stats(False)

        with ThreadPoolExecutor(max_workers=requests_per_wave) as executor:
            futures = [executor.submit(wave_request, i) for i in range(requests_per_wave)]
            for future in as_completed(futures):
                future.result()

        log(f"  🌊 Wave {wave+1} completada", "SUCCESS")

        # Pausa corta entre olas
        if wave < num_waves - 1:
            log(f"  Pausa de 10s antes de la siguiente ola...", "INFO")
            time.sleep(10)

    log("✅ Burst Wave test completed", "SUCCESS")

# ===========================================================================
# TEST 4: Memory Leak Hunt - Buscar fugas de memoria en GPU
# ===========================================================================

def test_memory_leak_hunt():
    """Enviar el mismo request muchas veces para detectar leaks"""
    log("🔥 TEST 4: MEMORY LEAK HUNT - Detectar fugas de memoria en GPU", "CRITICAL")

    # Enviar el mismo request 100 veces
    prompt = "Di solo: OK"

    for i in range(100):
        try:
            start = time.time()
            r = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": prompt},
                timeout=120
            )
            elapsed = time.time() - start

            update_stats(r.status_code == 200, elapsed)

            if i % 10 == 0:
                avg = sum(stats["response_times"]) / len(stats["response_times"]) if stats["response_times"] else 0
                log(f"  Iteration {i}: {elapsed:.1f}s (avg: {avg:.1f}s)", "INFO")

                # Si los tiempos aumentan significativamente, hay leak
                if i > 0 and elapsed > stats["response_times"][0] * 2:
                    log(f"  ⚠️  POSIBLE LEAK: tiempo aumentó de {stats['response_times'][0]:.1f}s a {elapsed:.1f}s", "WARNING")

        except Exception as e:
            log(f"  Iteration {i} ERROR: {e}", "ERROR")
            update_stats(False)

    log("✅ Memory Leak Hunt completed", "SUCCESS")

# ===========================================================================
# TEST 5: Maximum Context - Requests con contexto máximo
# ===========================================================================

def test_maximum_context():
    """Enviar requests que requieran máximo contexto RAG"""
    log("🔥 TEST 5: MAXIMUM CONTEXT - Requests con contexto RAG máximo", "CRITICAL")

    # Prompts que fuerzan búsqueda en RAG
    rag_prompts = [
        "Basándote en todas nuestras conversaciones anteriores y todo lo que sabes sobre mí, dame un resumen completo de nuestra relación.",
        "Revisa todo el historial y dame estadísticas detalladas de cada interacción que hemos tenido.",
        "Busca en toda tu base de conocimiento y lista absolutamente todo lo que sabes sobre Python, JavaScript, y todos los lenguajes de programación.",
        "Analiza todos los datos históricos y patrones de uso que tienes guardados.",
    ]

    for prompt in rag_prompts:
        log(f"  Testing: {prompt[:50]}...", "INFO")
        try:
            start = time.time()
            r = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": prompt},
                timeout=300
            )
            elapsed = time.time() - start
            update_stats(r.status_code == 200, elapsed)
            log(f"  Completado en {elapsed:.1f}s", "SUCCESS")
        except Exception as e:
            log(f"  ERROR: {e}", "ERROR")
            update_stats(False)

    log("✅ Maximum Context test completed", "SUCCESS")

# ===========================================================================
# MAIN
# ===========================================================================

def print_final_stats():
    print("\n" + "="*80)
    print("🔥 GPU DESTRUCTION TEST - FINAL RESULTS")
    print("="*80)
    print(f"Total requests: {stats['total']}")
    print(f"Success: \033[92m{stats['success']}\033[0m")
    print(f"Failed: \033[91m{stats['failed']}\033[0m")
    print(f"Timeouts: \033[93m{stats['timeouts']}\033[0m")
    print(f"OOM Errors: \033[95m{stats['oom_errors']}\033[0m")

    if stats["response_times"]:
        times = stats["response_times"]
        print(f"\nResponse Times:")
        print(f"  Min: {min(times):.1f}s")
        print(f"  Max: {max(times):.1f}s")
        print(f"  Avg: {sum(times)/len(times):.1f}s")
        print(f"  Median: {sorted(times)[len(times)//2]:.1f}s")

    print("="*80)

def main():
    log("="*80, "CRITICAL")
    log("🔥 GPU DESTRUCTION TEST - JARVIS IA V2", "CRITICAL")
    log("="*80, "CRITICAL")

    start_time = time.time()

    try:
        # TEST 1: GPU Saturation
        test_gpu_saturation(num_parallel=10)
        time.sleep(5)

        # TEST 2: Sequential Pressure
        test_sequential_pressure(num_requests=30)
        time.sleep(5)

        # TEST 3: Burst Wave
        test_burst_wave(num_waves=5, requests_per_wave=15)
        time.sleep(5)

        # TEST 4: Memory Leak Hunt
        test_memory_leak_hunt()
        time.sleep(5)

        # TEST 5: Maximum Context
        test_maximum_context()

    except KeyboardInterrupt:
        log("\n⚠️  Test interrupted!", "WARNING")
    except Exception as e:
        log(f"\n💥 FATAL: {e}", "CRITICAL")

    total_time = time.time() - start_time
    log(f"\n✅ ALL TESTS COMPLETED in {total_time/60:.1f} minutes", "SUCCESS")

    print_final_stats()

if __name__ == "__main__":
    main()
