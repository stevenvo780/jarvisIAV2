#!/usr/bin/env python3
"""
🔥 MASSIVE STRESS TEST - Jarvis IA V2 API
==========================================

Script de pruebas exhaustivas para validar:
- Todos los endpoints
- Diferentes tipos de preguntas
- Carga masiva y concurrencia
- Detección de fugas de memoria
- Límites y edge cases
- Recuperación de errores

Ejecutar con: python3 tests/massive_stress_test.py
"""

import requests
import json
import time
import random
import sys
import threading
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import psutil
import os

# Configuración
BASE_URL = "http://localhost:8090"
TIMEOUT = 120  # 2 minutos por request (para que no falle con modelos lentos)
API_KEY = os.getenv("JARVIS_API_KEYS", "").split(",")[0] if os.getenv("JARVIS_API_KEYS") else None

# Estadísticas globales
stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_time": 0,
    "errors": defaultdict(int),
    "endpoint_stats": defaultdict(lambda: {"count": 0, "success": 0, "fail": 0, "total_time": 0}),
}

# Lock para thread-safe stats
stats_lock = threading.Lock()


class Colors:
    """Colores ANSI para output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def log(message: str, level: str = "INFO"):
    """Log con timestamp y color"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": Colors.OKBLUE,
        "SUCCESS": Colors.OKGREEN,
        "WARNING": Colors.WARNING,
        "ERROR": Colors.FAIL,
        "HEADER": Colors.HEADER,
    }
    color = colors.get(level, "")
    print(f"{color}[{timestamp}] {level}: {message}{Colors.ENDC}")


def get_headers():
    """Headers para requests con API key opcional"""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-Api-Key"] = API_KEY
    return headers


def update_stats(endpoint: str, success: bool, elapsed_time: float, error: str = None):
    """Actualizar estadísticas thread-safe"""
    with stats_lock:
        stats["total_requests"] += 1
        stats["total_time"] += elapsed_time

        if success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
            if error:
                stats["errors"][error] += 1

        stats["endpoint_stats"][endpoint]["count"] += 1
        stats["endpoint_stats"][endpoint]["total_time"] += elapsed_time
        if success:
            stats["endpoint_stats"][endpoint]["success"] += 1
        else:
            stats["endpoint_stats"][endpoint]["fail"] += 1


def test_health():
    """Test: Health check endpoint"""
    log("Testing /health endpoint...", "HEADER")
    try:
        start = time.time()
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        elapsed = time.time() - start

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ok", f"Expected status 'ok', got {data.get('status')}"
        assert "timestamp" in data, "Missing timestamp in response"

        update_stats("/health", True, elapsed)
        log(f"✅ Health check passed ({elapsed:.2f}s)", "SUCCESS")
        return True
    except Exception as e:
        update_stats("/health", False, 0, str(e))
        log(f"❌ Health check failed: {e}", "ERROR")
        return False


def test_status():
    """Test: API status endpoint"""
    log("Testing /api/status endpoint...", "HEADER")
    try:
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/status", headers=get_headers(), timeout=10)
        elapsed = time.time() - start

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data, "Missing status in response"
        assert "models_loaded" in data, "Missing models_loaded in response"

        update_stats("/api/status", True, elapsed)
        log(f"✅ Status check passed - {data.get('models_loaded')} models loaded ({elapsed:.2f}s)", "SUCCESS")
        return True
    except Exception as e:
        update_stats("/api/status", False, 0, str(e))
        log(f"❌ Status check failed: {e}", "ERROR")
        return False


def test_chat(message: str, test_name: str = "chat"):
    """Test: Chat endpoint con un mensaje específico"""
    log(f"Testing chat: {test_name} - '{message[:50]}...'", "HEADER")
    try:
        start = time.time()
        payload = {
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            headers=get_headers(),
            timeout=TIMEOUT
        )
        elapsed = time.time() - start

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "response" in data, "Missing response in data"
        assert len(data["response"]) > 0, "Empty response"

        update_stats("/api/chat", True, elapsed)
        log(f"✅ Chat test '{test_name}' passed - Response: {data['response'][:100]}... ({elapsed:.2f}s)", "SUCCESS")
        return True
    except requests.exceptions.Timeout:
        update_stats("/api/chat", False, TIMEOUT, "Timeout")
        log(f"⏱️  Chat test '{test_name}' timed out after {TIMEOUT}s", "WARNING")
        return False
    except Exception as e:
        update_stats("/api/chat", False, 0, str(e))
        log(f"❌ Chat test '{test_name}' failed: {e}", "ERROR")
        return False


def test_history():
    """Test: History endpoints"""
    log("Testing /api/history endpoints...", "HEADER")
    try:
        # GET history
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/history", headers=get_headers(), timeout=10)
        elapsed = time.time() - start

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        history = response.json()
        assert isinstance(history, list), "History should be a list"

        update_stats("/api/history", True, elapsed)
        log(f"✅ GET history passed - {len(history)} items ({elapsed:.2f}s)", "SUCCESS")

        # DELETE history
        start = time.time()
        response = requests.delete(f"{BASE_URL}/api/history", headers=get_headers(), timeout=10)
        elapsed = time.time() - start

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ok", "Delete should return ok status"

        update_stats("/api/history", True, elapsed)
        log(f"✅ DELETE history passed ({elapsed:.2f}s)", "SUCCESS")
        return True
    except Exception as e:
        update_stats("/api/history", False, 0, str(e))
        log(f"❌ History test failed: {e}", "ERROR")
        return False


def test_input_validation():
    """Test: Input validation y edge cases"""
    log("Testing input validation...", "HEADER")

    test_cases = [
        ("", "empty_message", 422),  # Should fail validation
        ("a" * 6000, "too_long_message", 422),  # Exceeds 5000 char limit
        ("<script>alert('XSS')</script>", "xss_attempt", 200),  # Should sanitize
        ("¿Qué es Python?", "unicode", 200),  # Unicode characters
        ("SELECT * FROM users;", "sql_injection", 200),  # SQL injection attempt
    ]

    for message, test_name, expected_code in test_cases:
        log(f"  Testing: {test_name}", "INFO")
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": message, "timestamp": datetime.now().isoformat()},
                headers=get_headers(),
                timeout=TIMEOUT
            )

            if response.status_code == expected_code:
                log(f"    ✅ {test_name} - Got expected status {expected_code}", "SUCCESS")
            else:
                log(f"    ⚠️  {test_name} - Expected {expected_code}, got {response.status_code}", "WARNING")
        except Exception as e:
            log(f"    ❌ {test_name} failed: {e}", "ERROR")


def test_concurrent_requests(num_threads: int = 5, requests_per_thread: int = 3):
    """Test: Concurrencia - múltiples requests simultáneos"""
    log(f"Testing concurrent requests: {num_threads} threads x {requests_per_thread} requests...", "HEADER")

    messages = [
        "¿Qué hora es?",
        "Explica Python en una línea",
        "¿Cuál es la capital de Francia?",
        "Dame un número aleatorio",
        "¿Qué es machine learning?",
    ]

    def worker(thread_id: int):
        for i in range(requests_per_thread):
            message = random.choice(messages)
            log(f"  Thread {thread_id} - Request {i+1}/{requests_per_thread}", "INFO")
            test_chat(message, f"concurrent_t{thread_id}_r{i}")
            time.sleep(random.uniform(0.1, 0.5))

    threads = []
    start_time = time.time()

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    log(f"✅ Concurrent test completed in {elapsed:.2f}s", "SUCCESS")


def test_different_question_types():
    """Test: Diferentes tipos de preguntas para ejercitar todas las funcionalidades"""
    log("Testing different question types...", "HEADER")

    questions = [
        # Preguntas simples
        ("Hola", "greeting"),
        ("¿Cómo estás?", "status_question"),
        ("Adiós", "farewell"),

        # Preguntas de conocimiento
        ("¿Qué es Python?", "knowledge_programming"),
        ("Explica qué es la inteligencia artificial", "knowledge_ai"),
        ("¿Quién fue Albert Einstein?", "knowledge_history"),

        # Preguntas matemáticas
        ("¿Cuánto es 2 + 2?", "math_simple"),
        ("Calcula la raíz cuadrada de 144", "math_sqrt"),
        ("Resuelve: 15 * 8 + 20", "math_complex"),

        # Preguntas de programación
        ("Escribe un hola mundo en Python", "code_hello_world"),
        ("¿Cómo hacer un loop en JavaScript?", "code_loop"),
        ("Explica qué es una clase en POO", "code_oop"),

        # Preguntas de razonamiento
        ("Si tengo 5 manzanas y como 2, ¿cuántas me quedan?", "reasoning_simple"),
        ("¿Por qué el cielo es azul?", "reasoning_science"),
        ("Dame 3 ventajas de usar Docker", "reasoning_pros"),

        # Preguntas creativas
        ("Inventa un nombre para una startup de IA", "creative_naming"),
        ("Escribe un haiku sobre el código", "creative_poetry"),
        ("Dame una metáfora para explicar las APIs", "creative_metaphor"),

        # Preguntas con contexto
        ("Recuerda: mi color favorito es el azul. ¿Cuál es mi color favorito?", "context_memory"),
        ("Basándote en lo anterior, ¿qué otros colores podrían gustarme?", "context_inference"),

        # Preguntas de análisis
        ("¿Cuáles son los pros y contras de Python vs Java?", "analysis_comparison"),
        ("Analiza las ventajas de usar microservicios", "analysis_architecture"),

        # Preguntas multilingües
        ("What time is it?", "multilang_english"),
        ("Qu'est-ce que c'est?", "multilang_french"),
        ("¿Cómo se dice 'hola' en italiano?", "multilang_translation"),

        # Edge cases
        ("a", "edge_single_char"),
        ("?" * 10, "edge_many_questions"),
        ("123456789", "edge_only_numbers"),
        ("🤖💻🚀", "edge_only_emojis"),
    ]

    successful = 0
    failed = 0

    for message, test_name in questions:
        if test_chat(message, f"type_{test_name}"):
            successful += 1
        else:
            failed += 1
        time.sleep(0.5)  # Pequeña pausa entre preguntas

    log(f"✅ Question types test completed: {successful} successful, {failed} failed", "SUCCESS")


def test_load_sustained(duration_seconds: int = 60, requests_per_second: float = 0.5):
    """Test: Carga sostenida durante X segundos"""
    log(f"Testing sustained load: {duration_seconds}s at {requests_per_second} req/s...", "HEADER")

    messages = [
        "¿Qué es esto?",
        "Explica brevemente",
        "Dame info",
        "¿Cuál es tu opinión?",
        "Responde rápido",
    ]

    start_time = time.time()
    request_count = 0

    while time.time() - start_time < duration_seconds:
        message = random.choice(messages)
        test_chat(message, f"load_{request_count}")
        request_count += 1

        # Control de tasa de requests
        sleep_time = 1.0 / requests_per_second
        time.sleep(sleep_time)

    elapsed = time.time() - start_time
    log(f"✅ Sustained load test completed: {request_count} requests in {elapsed:.2f}s", "SUCCESS")


def test_memory_leak_detection():
    """Test: Detección de fugas de memoria"""
    log("Testing for memory leaks...", "HEADER")

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    log(f"  Initial memory: {initial_memory:.2f} MB", "INFO")

    # Hacer 20 requests y monitorear memoria
    for i in range(20):
        test_chat(f"Test memory leak {i}", f"memleak_{i}")

        if i % 5 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024
            increase = current_memory - initial_memory
            log(f"  After {i} requests: {current_memory:.2f} MB (+{increase:.2f} MB)", "INFO")

    final_memory = process.memory_info().rss / 1024 / 1024
    total_increase = final_memory - initial_memory

    if total_increase > 500:  # Si aumenta más de 500MB
        log(f"⚠️  Possible memory leak detected: +{total_increase:.2f} MB", "WARNING")
    else:
        log(f"✅ No significant memory leak detected: +{total_increase:.2f} MB", "SUCCESS")


def test_error_recovery():
    """Test: Recuperación de errores"""
    log("Testing error recovery...", "HEADER")

    # Enviar un request inválido
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"wrong_field": "test"},
            headers=get_headers(),
            timeout=10
        )
        log(f"  Invalid request returned: {response.status_code}", "INFO")
    except Exception as e:
        log(f"  Invalid request raised: {e}", "INFO")

    # Verificar que el servidor sigue respondiendo correctamente
    time.sleep(1)
    if test_health():
        log("✅ Server recovered from error", "SUCCESS")
    else:
        log("❌ Server failed to recover", "ERROR")


def print_final_stats():
    """Imprimir estadísticas finales"""
    log("=" * 80, "HEADER")
    log("FINAL STATISTICS", "HEADER")
    log("=" * 80, "HEADER")

    print(f"\n{Colors.BOLD}Overall Stats:{Colors.ENDC}")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Successful: {Colors.OKGREEN}{stats['successful_requests']}{Colors.ENDC}")
    print(f"  Failed: {Colors.FAIL}{stats['failed_requests']}{Colors.ENDC}")

    if stats['total_requests'] > 0:
        success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
        avg_time = stats['total_time'] / stats['total_requests']
        print(f"  Success rate: {Colors.OKGREEN}{success_rate:.2f}%{Colors.ENDC}")
        print(f"  Average response time: {avg_time:.2f}s")

    print(f"\n{Colors.BOLD}Per-Endpoint Stats:{Colors.ENDC}")
    for endpoint, data in stats['endpoint_stats'].items():
        if data['count'] > 0:
            avg = data['total_time'] / data['count']
            success_rate = (data['success'] / data['count']) * 100
            print(f"  {endpoint}:")
            print(f"    Requests: {data['count']} | Success: {data['success']} | Fail: {data['fail']}")
            print(f"    Avg time: {avg:.2f}s | Success rate: {success_rate:.2f}%")

    if stats['errors']:
        print(f"\n{Colors.BOLD}Error Summary:{Colors.ENDC}")
        for error, count in sorted(stats['errors'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {Colors.FAIL}{error}{Colors.ENDC}: {count} times")

    log("=" * 80, "HEADER")


def main():
    """Ejecutar todas las pruebas"""
    log("=" * 80, "HEADER")
    log("🔥 STARTING MASSIVE STRESS TEST FOR JARVIS IA V2", "HEADER")
    log("=" * 80, "HEADER")

    test_start = time.time()

    # Fase 1: Tests básicos
    log("\n" + "=" * 80, "HEADER")
    log("PHASE 1: BASIC ENDPOINT TESTS", "HEADER")
    log("=" * 80, "HEADER")
    test_health()
    time.sleep(1)
    test_status()
    time.sleep(1)
    test_history()

    # Fase 2: Input validation
    log("\n" + "=" * 80, "HEADER")
    log("PHASE 2: INPUT VALIDATION & EDGE CASES", "HEADER")
    log("=" * 80, "HEADER")
    test_input_validation()

    # Fase 3: Diferentes tipos de preguntas
    log("\n" + "=" * 80, "HEADER")
    log("PHASE 3: DIFFERENT QUESTION TYPES (COMPREHENSIVE)", "HEADER")
    log("=" * 80, "HEADER")
    test_different_question_types()

    # Fase 4: Tests de concurrencia
    log("\n" + "=" * 80, "HEADER")
    log("PHASE 4: CONCURRENCY TESTS", "HEADER")
    log("=" * 80, "HEADER")
    test_concurrent_requests(num_threads=3, requests_per_thread=2)

    # Fase 5: Carga sostenida
    log("\n" + "=" * 80, "HEADER")
    log("PHASE 5: SUSTAINED LOAD TEST", "HEADER")
    log("=" * 80, "HEADER")
    test_load_sustained(duration_seconds=30, requests_per_second=0.3)

    # Fase 6: Memory leak detection
    log("\n" + "=" * 80, "HEADER")
    log("PHASE 6: MEMORY LEAK DETECTION", "HEADER")
    log("=" * 80, "HEADER")
    test_memory_leak_detection()

    # Fase 7: Error recovery
    log("\n" + "=" * 80, "HEADER")
    log("PHASE 7: ERROR RECOVERY", "HEADER")
    log("=" * 80, "HEADER")
    test_error_recovery()

    # Resultados finales
    test_duration = time.time() - test_start
    log(f"\n🎉 ALL TESTS COMPLETED IN {test_duration:.2f}s", "HEADER")

    print_final_stats()

    # Exit code basado en tasa de éxito
    if stats['total_requests'] > 0:
        success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
        if success_rate >= 90:
            log(f"\n✅ TEST SUITE PASSED (Success rate: {success_rate:.2f}%)", "SUCCESS")
            sys.exit(0)
        elif success_rate >= 70:
            log(f"\n⚠️  TEST SUITE PARTIALLY PASSED (Success rate: {success_rate:.2f}%)", "WARNING")
            sys.exit(1)
        else:
            log(f"\n❌ TEST SUITE FAILED (Success rate: {success_rate:.2f}%)", "ERROR")
            sys.exit(2)
    else:
        log("\n❌ NO TESTS WERE EXECUTED", "ERROR")
        sys.exit(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\n⚠️  Test interrupted by user", "WARNING")
        print_final_stats()
        sys.exit(130)
    except Exception as e:
        log(f"\n\n❌ Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
