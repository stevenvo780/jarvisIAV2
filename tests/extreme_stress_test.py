#!/usr/bin/env python3
"""
💥 EXTREME STRESS TEST - JARVIS IA V2
=====================================

Este script va a DESTRUIR tu sistema con pruebas extremas:
- Concurrencia masiva (50+ threads)
- Payloads gigantes
- Request bombing
- Memory exhaustion
- GPU saturation
- Race conditions
- Resource leaks

⚠️  ADVERTENCIA: Puede hacer que el sistema se vuelva inestable
Ejecutar solo en entorno de pruebas.
"""

import requests
import threading
import multiprocessing
import time
import random
import string
import json
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import signal
import sys

BASE_URL = "http://localhost:8090"
TOTAL_REQUESTS = 0
SUCCESSFUL_REQUESTS = 0
FAILED_REQUESTS = 0
ERRORS = []
lock = threading.Lock()

def log(msg, level="INFO"):
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[95m",
        "RESET": "\033[0m"
    }
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{colors.get(level, '')}{timestamp} [{level}] {msg}{colors['RESET']}")

def update_stats(success=True, error=None):
    global TOTAL_REQUESTS, SUCCESSFUL_REQUESTS, FAILED_REQUESTS, ERRORS
    with lock:
        TOTAL_REQUESTS += 1
        if success:
            SUCCESSFUL_REQUESTS += 1
        else:
            FAILED_REQUESTS += 1
            if error:
                ERRORS.append(str(error))

def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_system_stats():
    """Obtener estadísticas del sistema"""
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    return {
        "cpu": cpu,
        "memory_percent": mem.percent,
        "memory_used_gb": mem.used / (1024**3)
    }

# ============================================================================
# FASE 1: CONCURRENCY HELL - Bombardeo masivo de requests
# ============================================================================

def test_concurrent_bomb(num_threads=50, requests_per_thread=10):
    """Bombardeo masivo de requests concurrentes"""
    log(f"🔥 FASE 1: CONCURRENT BOMB - {num_threads} threads x {requests_per_thread} requests", "CRITICAL")

    def worker(thread_id):
        for i in range(requests_per_thread):
            try:
                # Enviar requests muy rápido sin pausas
                r = requests.post(
                    f"{BASE_URL}/api/chat",
                    json={"message": f"Thread {thread_id} Request {i}"},
                    timeout=5  # Timeout corto intencional
                )
                if r.status_code == 200:
                    update_stats(True)
                    log(f"Thread {thread_id}-{i}: OK", "SUCCESS")
                else:
                    update_stats(False, f"Status {r.status_code}")
            except Exception as e:
                update_stats(False, e)
                log(f"Thread {thread_id}-{i}: ERROR - {e}", "ERROR")

    start = time.time()
    threads = []

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        # No sleep - lanzar todos lo más rápido posible

    for t in threads:
        t.join()

    elapsed = time.time() - start
    log(f"✅ Concurrent bomb completed: {num_threads*requests_per_thread} requests in {elapsed:.2f}s", "SUCCESS")
    log(f"   Rate: {(num_threads*requests_per_thread)/elapsed:.2f} req/s", "INFO")

# ============================================================================
# FASE 2: PAYLOAD HELL - Payloads gigantes y maliciosos
# ============================================================================

def test_payload_hell():
    """Enviar payloads extremos"""
    log("🔥 FASE 2: PAYLOAD HELL - Payloads gigantes y maliciosos", "CRITICAL")

    payloads = [
        # Payload gigante - 10MB de texto
        ("giant_10mb", "A" * (10 * 1024 * 1024)),

        # Payload con caracteres especiales
        ("special_chars", "".join(chr(i) for i in range(32, 127)) * 1000),

        # Payload con emojis masivos
        ("emoji_bomb", "🔥💥🚀" * 10000),

        # Payload con HTML/JavaScript malicioso
        ("xss_bomb", "<script>alert(1)</script>" * 5000),

        # Payload con SQL injection masivo
        ("sql_bomb", "'; DROP TABLE users; --" * 5000),

        # Payload con null bytes
        ("null_bytes", "test\x00" * 5000),

        # Payload con Unicode exótico
        ("unicode_hell", "𝕳𝖊𝖑𝖑𝖔 𝖂𝖔𝖗𝖑𝖉" * 1000),

        # Payload con formato JSON inválido
        ("json_hell", '{"unclosed": "json' * 1000),
    ]

    for name, payload in payloads:
        log(f"  Testing payload: {name} ({len(payload)} bytes)", "INFO")
        try:
            r = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": payload},
                timeout=10
            )
            log(f"    {name}: Status {r.status_code}", "WARNING" if r.status_code != 200 else "SUCCESS")
            update_stats(r.status_code in [200, 422])
        except Exception as e:
            log(f"    {name}: ERROR - {e}", "ERROR")
            update_stats(False, e)

# ============================================================================
# FASE 3: MEMORY EXHAUSTION - Intentar agotar memoria
# ============================================================================

def test_memory_exhaustion(iterations=100):
    """Intentar agotar la memoria del servidor"""
    log(f"🔥 FASE 3: MEMORY EXHAUSTION - {iterations} requests sin liberar", "CRITICAL")

    initial_mem = get_system_stats()
    log(f"  Memoria inicial: {initial_mem['memory_used_gb']:.2f} GB ({initial_mem['memory_percent']:.1f}%)", "INFO")

    # Enviar muchos requests grandes simultáneamente
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(iterations):
            # Payload grande pero no tan grande como para ser rechazado
            message = random_string(4000)  # Cerca del límite de 5000
            future = executor.submit(
                lambda m: requests.post(
                    f"{BASE_URL}/api/chat",
                    json={"message": m},
                    timeout=5
                ),
                message
            )
            futures.append(future)

        # Recoger resultados
        completed = 0
        for future in as_completed(futures):
            try:
                r = future.result()
                update_stats(r.status_code == 200)
                completed += 1
                if completed % 10 == 0:
                    current_mem = get_system_stats()
                    log(f"  Progress: {completed}/{iterations} | Mem: {current_mem['memory_used_gb']:.2f} GB ({current_mem['memory_percent']:.1f}%)", "INFO")
            except Exception as e:
                update_stats(False, e)

    final_mem = get_system_stats()
    mem_increase = final_mem['memory_used_gb'] - initial_mem['memory_used_gb']
    log(f"  Memoria final: {final_mem['memory_used_gb']:.2f} GB ({final_mem['memory_percent']:.1f}%)", "INFO")
    log(f"  Incremento: {mem_increase:.2f} GB", "WARNING" if mem_increase > 1 else "SUCCESS")

# ============================================================================
# FASE 4: REQUEST BOMBING - Ráfagas rápidas sin tregua
# ============================================================================

def test_request_bombing(duration_seconds=60):
    """Bombardear el servidor sin parar durante X segundos"""
    log(f"🔥 FASE 4: REQUEST BOMBING - {duration_seconds}s de bombardeo continuo", "CRITICAL")

    start_time = time.time()
    request_count = 0

    def bomb_worker():
        nonlocal request_count
        while time.time() - start_time < duration_seconds:
            try:
                r = requests.post(
                    f"{BASE_URL}/api/chat",
                    json={"message": random_string(random.randint(10, 100))},
                    timeout=2
                )
                update_stats(r.status_code == 200)
                request_count += 1
            except:
                update_stats(False)
                request_count += 1

    # Lanzar múltiples threads bombardeando
    threads = []
    for _ in range(10):
        t = threading.Thread(target=bomb_worker)
        t.start()
        threads.append(t)

    # Monitorear mientras bombardean
    while time.time() - start_time < duration_seconds:
        stats = get_system_stats()
        elapsed = time.time() - start_time
        rate = request_count / elapsed if elapsed > 0 else 0
        log(f"  Bombing... {request_count} requests @ {rate:.1f} req/s | CPU: {stats['cpu']:.1f}% | Mem: {stats['memory_percent']:.1f}%", "WARNING")
        time.sleep(5)

    for t in threads:
        t.join()

    total_time = time.time() - start_time
    log(f"✅ Bombing completed: {request_count} requests in {total_time:.1f}s ({request_count/total_time:.1f} req/s)", "SUCCESS")

# ============================================================================
# FASE 5: RACE CONDITIONS - Operaciones concurrentes conflictivas
# ============================================================================

def test_race_conditions():
    """Intentar causar race conditions con operaciones concurrentes"""
    log("🔥 FASE 5: RACE CONDITIONS - Operaciones conflictivas simultáneas", "CRITICAL")

    def rapid_history_operations(op_id):
        """Operaciones rápidas de history"""
        for i in range(20):
            try:
                # GET
                requests.get(f"{BASE_URL}/api/history", timeout=2)
                # POST chat
                requests.post(f"{BASE_URL}/api/chat", json={"message": f"Race {op_id}-{i}"}, timeout=2)
                # DELETE
                requests.delete(f"{BASE_URL}/api/history", timeout=2)
                # GET again
                requests.get(f"{BASE_URL}/api/history", timeout=2)
                update_stats(True)
            except Exception as e:
                update_stats(False, e)

    # Lanzar muchos threads haciendo operaciones conflictivas
    threads = []
    for i in range(20):
        t = threading.Thread(target=rapid_history_operations, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    log("✅ Race conditions test completed", "SUCCESS")

# ============================================================================
# FASE 6: ENDPOINT ABUSE - Abusar de cada endpoint
# ============================================================================

def test_endpoint_abuse():
    """Abusar sistemáticamente de cada endpoint"""
    log("🔥 FASE 6: ENDPOINT ABUSE - Abusar de todos los endpoints", "CRITICAL")

    endpoints = [
        ("GET", "/health", None),
        ("GET", "/api/status", None),
        ("GET", "/api/history", None),
        ("DELETE", "/api/history", None),
        ("POST", "/api/chat", {"message": "abuse"}),
    ]

    for _ in range(10):  # 10 rondas de abuso
        for method, endpoint, data in endpoints:
            with ThreadPoolExecutor(max_workers=30) as executor:
                futures = []
                for i in range(100):  # 100 requests por endpoint
                    if method == "GET":
                        future = executor.submit(lambda: requests.get(f"{BASE_URL}{endpoint}", timeout=3))
                    elif method == "POST":
                        future = executor.submit(lambda: requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=3))
                    elif method == "DELETE":
                        future = executor.submit(lambda: requests.delete(f"{BASE_URL}{endpoint}", timeout=3))
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        r = future.result()
                        update_stats(r.status_code in [200, 422])
                    except:
                        update_stats(False)

    log("✅ Endpoint abuse completed", "SUCCESS")

# ============================================================================
# FASE 7: MALFORMED REQUESTS - Requests inválidos
# ============================================================================

def test_malformed_requests():
    """Enviar requests malformados de todo tipo"""
    log("🔥 FASE 7: MALFORMED REQUESTS - Requests inválidos masivos", "CRITICAL")

    malformed = [
        # JSON inválido
        ({"Content-Type": "application/json"}, '{"invalid": json}'),
        # Headers raros
        ({"Content-Type": "text/xml", "X-Evil": "true"}, '{"message": "test"}'),
        # Sin Content-Type
        ({}, '{"message": "test"}'),
        # Charset raro
        ({"Content-Type": "application/json; charset=utf-32"}, '{"message": "test"}'),
        # Body vacío
        ({"Content-Type": "application/json"}, ''),
        # Body no-JSON
        ({"Content-Type": "application/json"}, 'this is not json at all'),
    ]

    for headers, data in malformed:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for _ in range(50):
                future = executor.submit(
                    lambda h, d: requests.post(f"{BASE_URL}/api/chat", headers=h, data=d, timeout=3),
                    headers, data
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    r = future.result()
                    update_stats(r.status_code in [400, 422, 500])
                except:
                    update_stats(False)

    log("✅ Malformed requests test completed", "SUCCESS")

# ============================================================================
# FASE 8: RESOURCE EXHAUSTION - Intentar agotar recursos del sistema
# ============================================================================

def test_resource_exhaustion():
    """Intentar agotar CPU, memoria, descriptores de archivos, etc."""
    log("🔥 FASE 8: RESOURCE EXHAUSTION - Agotar recursos del sistema", "CRITICAL")

    initial = get_system_stats()
    log(f"  Estado inicial: CPU {initial['cpu']:.1f}%, Mem {initial['memory_percent']:.1f}%", "INFO")

    # Crear una cantidad absurda de threads
    def keep_alive_request():
        try:
            requests.get(f"{BASE_URL}/health", timeout=300)  # Timeout largo para mantener conexión
        except:
            pass

    threads = []
    max_threads = 200  # Intentar crear 200 threads

    for i in range(max_threads):
        try:
            t = threading.Thread(target=keep_alive_request)
            t.start()
            threads.append(t)

            if i % 20 == 0:
                stats = get_system_stats()
                log(f"  {i} threads activos | CPU: {stats['cpu']:.1f}% | Mem: {stats['memory_percent']:.1f}%", "WARNING")
        except Exception as e:
            log(f"  Failed to create thread {i}: {e}", "ERROR")
            break

    log(f"  Created {len(threads)} threads", "INFO")

    # Esperar un poco con todas las conexiones activas
    time.sleep(10)

    final = get_system_stats()
    log(f"  Estado final: CPU {final['cpu']:.1f}%, Mem {final['memory_percent']:.1f}%", "INFO")

    # No hacer join() - dejar que mueran solos
    log("✅ Resource exhaustion test completed", "SUCCESS")

# ============================================================================
# MAIN - Ejecutar todas las fases
# ============================================================================

def print_stats():
    """Imprimir estadísticas finales"""
    print("\n" + "="*80)
    print("💥 EXTREME STRESS TEST - FINAL STATISTICS")
    print("="*80)
    print(f"Total requests: {TOTAL_REQUESTS}")
    print(f"Successful: \033[92m{SUCCESSFUL_REQUESTS}\033[0m")
    print(f"Failed: \033[91m{FAILED_REQUESTS}\033[0m")

    if TOTAL_REQUESTS > 0:
        success_rate = (SUCCESSFUL_REQUESTS / TOTAL_REQUESTS) * 100
        print(f"Success rate: {success_rate:.2f}%")

    if ERRORS:
        print(f"\nTop 5 errors:")
        from collections import Counter
        for error, count in Counter(ERRORS).most_common(5):
            print(f"  - {error}: {count} times")

    stats = get_system_stats()
    print(f"\nFinal system state:")
    print(f"  CPU: {stats['cpu']:.1f}%")
    print(f"  Memory: {stats['memory_used_gb']:.2f} GB ({stats['memory_percent']:.1f}%)")
    print("="*80)

def signal_handler(sig, frame):
    """Handler para Ctrl+C"""
    log("\n⚠️  Test interrupted by user!", "WARNING")
    print_stats()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)

    log("="*80, "CRITICAL")
    log("💥 EXTREME STRESS TEST - JARVIS IA V2", "CRITICAL")
    log("="*80, "CRITICAL")
    log("⚠️  WARNING: This will HAMMER your system!", "WARNING")
    log("", "INFO")

    start_time = time.time()

    try:
        # FASE 1: Concurrent bomb
        test_concurrent_bomb(num_threads=50, requests_per_thread=10)
        time.sleep(2)

        # FASE 2: Payload hell
        test_payload_hell()
        time.sleep(2)

        # FASE 3: Memory exhaustion
        test_memory_exhaustion(iterations=100)
        time.sleep(2)

        # FASE 4: Request bombing
        test_request_bombing(duration_seconds=60)
        time.sleep(2)

        # FASE 5: Race conditions
        test_race_conditions()
        time.sleep(2)

        # FASE 6: Endpoint abuse
        test_endpoint_abuse()
        time.sleep(2)

        # FASE 7: Malformed requests
        test_malformed_requests()
        time.sleep(2)

        # FASE 8: Resource exhaustion
        test_resource_exhaustion()

    except Exception as e:
        log(f"💥 FATAL ERROR: {e}", "CRITICAL")

    total_time = time.time() - start_time
    log(f"\n🎉 ALL PHASES COMPLETED in {total_time:.1f}s", "SUCCESS")

    print_stats()

if __name__ == "__main__":
    main()
