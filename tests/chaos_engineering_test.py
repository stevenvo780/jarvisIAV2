#!/usr/bin/env python3
"""
💀 CHAOS ENGINEERING TEST - JARVIS IA V2
=========================================

Inspirado en Netflix's Chaos Monkey - Intentar romper el sistema de todas las formas posibles:
- Random failures injection
- Network chaos
- Resource starvation
- Timing attacks
- State corruption
- Fuzzing extremo
- Crash recovery testing

⚠️  ADVERTENCIA: Este test INTENTARÁ romper tu sistema
"""

import requests
import threading
import time
import random
import string
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BASE_URL = "http://localhost:8090"

class ChaosStats:
    def __init__(self):
        self.total_attacks = 0
        self.successful_attacks = 0
        self.failed_attacks = 0
        self.crashes_detected = 0
        self.anomalies = []
        self.lock = threading.Lock()

    def record_attack(self, success, anomaly=None):
        with self.lock:
            self.total_attacks += 1
            if success:
                self.successful_attacks += 1
            else:
                self.failed_attacks += 1
            if anomaly:
                self.anomalies.append(anomaly)

    def record_crash(self):
        with self.lock:
            self.crashes_detected += 1

stats = ChaosStats()

def log(msg, level="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "WARNING": "\033[93m", "ERROR": "\033[91m", "CHAOS": "\033[95m", "RESET": "\033[0m"}
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{colors.get(level, '')}{ts} [{level}] {msg}{colors['RESET']}")

# ===========================================================================
# CHAOS 1: Random Fuzzing - Fuzzing aleatorio total
# ===========================================================================

def chaos_random_fuzzing(iterations=200):
    """Fuzzing completamente aleatorio"""
    log("💀 CHAOS 1: RANDOM FUZZING - Datos completamente aleatorios", "CHAOS")

    def random_bytes(size):
        return ''.join(random.choice(string.printable) for _ in range(size))

    for i in range(iterations):
        # Generar payload completamente aleatorio
        chaos_type = random.choice([
            "random_json",
            "random_text",
            "binary_garbage",
            "unicode_hell",
            "control_chars"
        ])

        try:
            if chaos_type == "random_json":
                payload = {random_bytes(10): random_bytes(random.randint(1, 100)) for _ in range(random.randint(1, 20))}
            elif chaos_type == "random_text":
                payload = {"message": random_bytes(random.randint(1, 10000))}
            elif chaos_type == "binary_garbage":
                payload = {"message": ''.join(chr(random.randint(0, 255)) for _ in range(100))}
            elif chaos_type == "unicode_hell":
                payload = {"message": ''.join(chr(random.randint(0x1000, 0x10000)) for _ in range(100))}
            else:  # control_chars
                payload = {"message": ''.join(chr(random.randint(0, 31)) for _ in range(100))}

            r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=5)

            if r.status_code >= 500:
                stats.record_attack(True, f"Fuzzing causó 5xx: {chaos_type}")
                log(f"  ✓ Fuzzing {i}: Causó 5xx con {chaos_type}", "WARNING")
            else:
                stats.record_attack(False)

        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                stats.record_crash()
                log(f"  💀 CRASH DETECTED: Server unreachable", "CHAOS")
            stats.record_attack(True, f"Fuzzing causó excepción: {str(e)[:50]}")

    log("✅ Random Fuzzing completed", "SUCCESS")

# ===========================================================================
# CHAOS 2: Timing Attacks - Ataques de timing
# ===========================================================================

def chaos_timing_attacks():
    """Intentar causar race conditions y timing issues"""
    log("💀 CHAOS 2: TIMING ATTACKS - Race conditions y timing attacks", "CHAOS")

    def rapid_fire(endpoint, method="GET"):
        """Disparar requests extremadamente rápido"""
        for _ in range(50):
            try:
                if method == "GET":
                    requests.get(f"{BASE_URL}{endpoint}", timeout=0.1)
                elif method == "POST":
                    requests.post(f"{BASE_URL}{endpoint}", json={"message": "x"}, timeout=0.1)
                elif method == "DELETE":
                    requests.delete(f"{BASE_URL}{endpoint}", timeout=0.1)
            except:
                pass

    # Lanzar múltiples threads haciendo rapid-fire en diferentes endpoints
    endpoints = [
        ("/health", "GET"),
        ("/api/status", "GET"),
        ("/api/history", "GET"),
        ("/api/history", "DELETE"),
        ("/api/chat", "POST"),
    ]

    threads = []
    for endpoint, method in endpoints:
        for _ in range(10):  # 10 threads por endpoint
            t = threading.Thread(target=rapid_fire, args=(endpoint, method))
            threads.append(t)
            t.start()

    # Esperar un poco
    time.sleep(5)

    # Verificar si el servidor sigue vivo
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            stats.record_attack(False)
            log("  Server survived timing attacks", "SUCCESS")
        else:
            stats.record_attack(True, "Timing attack causó respuesta anormal")
    except:
        stats.record_crash()
        log("  💀 CRASH: Server unreachable después de timing attacks", "CHAOS")

    log("✅ Timing Attacks completed", "SUCCESS")

# ===========================================================================
# CHAOS 3: State Corruption - Corromper el estado del servidor
# ===========================================================================

def chaos_state_corruption():
    """Intentar corromper el estado interno del servidor"""
    log("💀 CHAOS 3: STATE CORRUPTION - Corromper estado del servidor", "CHAOS")

    # 1. Crear historial grande
    log("  Creating large history...", "INFO")
    for i in range(100):
        try:
            requests.post(f"{BASE_URL}/api/chat", json={"message": f"msg{i}"}, timeout=3)
        except:
            pass

    # 2. Intentar acceder/borrar mientras se está usando
    def simultaneous_operations():
        for _ in range(50):
            try:
                operation = random.choice(["get", "delete", "post"])
                if operation == "get":
                    requests.get(f"{BASE_URL}/api/history", timeout=1)
                elif operation == "delete":
                    requests.delete(f"{BASE_URL}/api/history", timeout=1)
                else:
                    requests.post(f"{BASE_URL}/api/chat", json={"message": "x"}, timeout=1)
            except:
                pass

    threads = [threading.Thread(target=simultaneous_operations) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 3. Verificar consistencia
    try:
        r = requests.get(f"{BASE_URL}/api/history", timeout=5)
        history = r.json()
        if not isinstance(history, list):
            stats.record_attack(True, "State corruption: history no es lista")
            log("  ✓ State corrupted: history is not a list!", "WARNING")
        else:
            stats.record_attack(False)
    except Exception as e:
        stats.record_attack(True, f"State corruption causó: {e}")

    log("✅ State Corruption test completed", "SUCCESS")

# ===========================================================================
# CHAOS 4: Resource Starvation - Agotar todos los recursos
# ===========================================================================

def chaos_resource_starvation():
    """Intentar agotar CPU, memoria, file descriptors, etc."""
    log("💀 CHAOS 4: RESOURCE STARVATION - Agotar todos los recursos", "CHAOS")

    # Crear toneladas de conexiones simultáneas
    def create_hanging_connection():
        try:
            requests.get(f"{BASE_URL}/health", timeout=300, stream=True)
        except:
            pass

    log("  Creating 500 hanging connections...", "WARNING")
    threads = []
    for i in range(500):
        t = threading.Thread(target=create_hanging_connection)
        t.start()
        threads.append(t)

        if i % 50 == 0:
            log(f"  Created {i} connections...", "INFO")

    # Mientras tanto, bombardear con requests
    log("  Bombing server while connections hang...", "WARNING")
    for i in range(100):
        try:
            requests.post(f"{BASE_URL}/api/chat", json={"message": f"bomb{i}"}, timeout=1)
        except:
            pass

    # Verificar si sigue vivo
    time.sleep(5)
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        if r.status_code == 200:
            stats.record_attack(False)
            log("  Server survived resource starvation", "SUCCESS")
        else:
            stats.record_attack(True, "Resource starvation causó respuesta anormal")
    except:
        stats.record_crash()
        log("  💀 CRASH: Server unreachable", "CHAOS")

    log("✅ Resource Starvation test completed", "SUCCESS")

# ===========================================================================
# CHAOS 5: Malicious Payloads - Payloads maliciosos conocidos
# ===========================================================================

def chaos_malicious_payloads():
    """Enviar payloads maliciosos conocidos"""
    log("💀 CHAOS 5: MALICIOUS PAYLOADS - Exploits conocidos", "CHAOS")

    payloads = [
        # Path traversal
        {"message": "../../../etc/passwd"},
        {"message": "..\\..\\..\\windows\\system32"},

        # Command injection
        {"message": "; rm -rf /"},
        {"message": "$(whoami)"},
        {"message": "`ls -la`"},
        {"message": "| cat /etc/shadow"},

        # SQL injection variants
        {"message": "1' OR '1'='1"},
        {"message": "admin'--"},
        {"message": "' UNION SELECT * FROM users--"},

        # NoSQL injection
        {"message": "{'$gt': ''}"},
        {"message": "{'$ne': null}"},

        # XXE
        {"message": "<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><foo>&xxe;</foo>"},

        # SSRF
        {"message": "http://localhost:22"},
        {"message": "http://169.254.169.254/latest/meta-data/"},

        # Log injection
        {"message": "\n[CRITICAL] FAKE LOG ENTRY\n"},

        # Format string
        {"message": "%s%s%s%s%s%s%s%s"},
        {"message": "%x%x%x%x"},

        # Buffer overflow attempts
        {"message": "A" * 1000000},

        # Null byte injection
        {"message": "test\x00admin"},

        # CRLF injection
        {"message": "test\r\nSet-Cookie: admin=true"},
    ]

    for payload in payloads:
        try:
            r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=5)

            # Si pasa sin error, el servidor lo manejó bien
            if r.status_code == 200:
                # Verificar si el payload tuvo efecto
                response = r.json().get("response", "")
                if "etc/passwd" in response or "windows" in response.lower() or "root:" in response:
                    stats.record_attack(True, f"Payload tuvo efecto: {str(payload)[:50]}")
                    log(f"  ⚠️  VULNERABLE: Payload tuvo efecto!", "WARNING")
                else:
                    stats.record_attack(False)
            elif r.status_code >= 500:
                stats.record_attack(True, "Payload causó 5xx")

        except Exception as e:
            if "connection" in str(e).lower():
                stats.record_crash()

    log("✅ Malicious Payloads test completed", "SUCCESS")

# ===========================================================================
# CHAOS 6: Crash Recovery - Verificar recuperación de crashes
# ===========================================================================

def chaos_crash_recovery():
    """Intentar crashear y ver si se recupera"""
    log("💀 CHAOS 6: CRASH RECOVERY - Intentar crashear el servidor", "CHAOS")

    crash_attempts = [
        # Intentar desbordar stack con recursión
        {"message": "a" * 100000},

        # Payload que puede causar regex DoS
        {"message": "a" * 10000 + "!" * 10000},

        # Intentar division by zero
        {"message": "calcula 1/0"},

        # Null pointer
        {"message": "\x00" * 1000},
    ]

    for i, payload in enumerate(crash_attempts):
        log(f"  Crash attempt {i+1}...", "WARNING")

        try:
            r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
            stats.record_attack(False)
        except Exception as e:
            if "connection" in str(e).lower():
                stats.record_crash()
                log(f"  💀 CRASH ATTEMPT SUCCEEDED!", "CHAOS")

                # Esperar recovery
                log(f"  Waiting for recovery...", "INFO")
                time.sleep(10)

                # Verificar si se recuperó
                for attempt in range(5):
                    try:
                        r = requests.get(f"{BASE_URL}/health", timeout=5)
                        if r.status_code == 200:
                            log(f"  ✓ Server recovered after {attempt+1} attempts", "SUCCESS")
                            break
                    except:
                        time.sleep(5)
                else:
                    log(f"  💀 Server did NOT recover", "CHAOS")

    log("✅ Crash Recovery test completed", "SUCCESS")

# ===========================================================================
# CHAOS 7: Chaos Monkey - Aleatorio total
# ===========================================================================

def chaos_monkey(duration_seconds=120):
    """Chaos Monkey - hacer cosas aleatorias durante X segundos"""
    log(f"💀 CHAOS 7: CHAOS MONKEY - {duration_seconds}s de caos aleatorio", "CHAOS")

    chaos_actions = [
        lambda: requests.get(f"{BASE_URL}/health", timeout=1),
        lambda: requests.post(f"{BASE_URL}/api/chat", json={"message": random_string(random.randint(1, 5000))}, timeout=2),
        lambda: requests.delete(f"{BASE_URL}/api/history", timeout=1),
        lambda: requests.post(f"{BASE_URL}/api/chat", json={"message": "\x00" * 100}, timeout=1),
        lambda: requests.post(f"{BASE_URL}/api/chat", json={random_string(10): random_string(10)}, timeout=1),
    ]

    start = time.time()
    action_count = 0

    def monkey_worker():
        nonlocal action_count
        while time.time() - start < duration_seconds:
            try:
                action = random.choice(chaos_actions)
                action()
                action_count += 1
            except:
                pass
            time.sleep(random.uniform(0, 0.5))

    # Lanzar múltiples monkeys
    threads = [threading.Thread(target=monkey_worker) for _ in range(20)]
    for t in threads:
        t.start()

    # Monitorear
    while time.time() - start < duration_seconds:
        elapsed = time.time() - start
        log(f"  Chaos Monkey: {action_count} actions in {elapsed:.0f}s", "INFO")
        time.sleep(10)

    for t in threads:
        t.join()

    # Verificar supervivencia
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            log(f"  ✓ Server survived {action_count} chaos actions", "SUCCESS")
            stats.record_attack(False)
        else:
            stats.record_attack(True, "Server en estado anormal")
    except:
        stats.record_crash()
        log("  💀 CRASH: Server unreachable", "CHAOS")

    log("✅ Chaos Monkey completed", "SUCCESS")

def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ===========================================================================
# MAIN
# ===========================================================================

def print_final_report():
    print("\n" + "="*80)
    print("💀 CHAOS ENGINEERING TEST - FINAL REPORT")
    print("="*80)
    print(f"Total chaos attacks: {stats.total_attacks}")
    print(f"Successful attacks (caused issues): \033[91m{stats.successful_attacks}\033[0m")
    print(f"Failed attacks (server handled): \033[92m{stats.failed_attacks}\033[0m")
    print(f"Crashes detected: \033[95m{stats.crashes_detected}\033[0m")

    if stats.anomalies:
        print(f"\nAnomalies detected: {len(stats.anomalies)}")
        for i, anomaly in enumerate(stats.anomalies[:10], 1):
            print(f"  {i}. {anomaly}")
        if len(stats.anomalies) > 10:
            print(f"  ... and {len(stats.anomalies) - 10} more")

    if stats.crashes_detected > 0:
        print(f"\n⚠️  WARNING: {stats.crashes_detected} crashes detected!")
    else:
        print(f"\n✅ System survived all chaos attacks!")

    print("="*80)

def main():
    log("="*80, "CHAOS")
    log("💀 CHAOS ENGINEERING TEST - JARVIS IA V2", "CHAOS")
    log("="*80, "CHAOS")
    log("⚠️  This will ACTIVELY TRY TO BREAK your system!", "WARNING")
    log("", "INFO")

    start_time = time.time()

    try:
        # CHAOS 1: Random Fuzzing
        chaos_random_fuzzing(iterations=200)
        time.sleep(3)

        # CHAOS 2: Timing Attacks
        chaos_timing_attacks()
        time.sleep(3)

        # CHAOS 3: State Corruption
        chaos_state_corruption()
        time.sleep(3)

        # CHAOS 4: Resource Starvation
        chaos_resource_starvation()
        time.sleep(3)

        # CHAOS 5: Malicious Payloads
        chaos_malicious_payloads()
        time.sleep(3)

        # CHAOS 6: Crash Recovery
        chaos_crash_recovery()
        time.sleep(3)

        # CHAOS 7: Chaos Monkey
        chaos_monkey(duration_seconds=120)

    except KeyboardInterrupt:
        log("\n⚠️  Chaos interrupted!", "WARNING")
    except Exception as e:
        log(f"\n💥 FATAL CHAOS ERROR: {e}", "CHAOS")

    total_time = time.time() - start_time
    log(f"\n🎉 ALL CHAOS COMPLETED in {total_time/60:.1f} minutes", "SUCCESS")

    print_final_report()

if __name__ == "__main__":
    main()
