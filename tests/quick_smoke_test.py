#!/usr/bin/env python3
"""
Quick smoke test - Prueba rápida de funcionalidad básica
Ejecutar con: python3 tests/quick_smoke_test.py
"""

import requests
import time
import json

BASE_URL = "http://localhost:8090"

def test(name, func):
    """Ejecutar un test y mostrar resultado"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    try:
        start = time.time()
        result = func()
        elapsed = time.time() - start
        if result:
            print(f"✅ PASSED ({elapsed:.2f}s)")
            return True
        else:
            print(f"❌ FAILED ({elapsed:.2f}s)")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_health():
    """Test health endpoint"""
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return r.status_code == 200 and data["status"] == "ok"

def test_status():
    """Test status endpoint"""
    r = requests.get(f"{BASE_URL}/api/status", timeout=5)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return r.status_code == 200

def test_simple_chat():
    """Test chat con pregunta simple"""
    message = "Hola, responde solo con una palabra"
    print(f"Sending: {message}")
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": message},
        timeout=60
    )
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Response: {data.get('response', 'NO RESPONSE')[:200]}")
    return r.status_code == 200 and len(data.get('response', '')) > 0

def test_history():
    """Test history endpoint"""
    r = requests.get(f"{BASE_URL}/api/history", timeout=5)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"History items: {len(data)}")
    return r.status_code == 200

def main():
    print("\n" + "="*60)
    print("🔥 QUICK SMOKE TEST - Jarvis IA V2")
    print("="*60)

    results = []
    results.append(test("Health Check", test_health))
    results.append(test("API Status", test_status))
    results.append(test("Simple Chat", test_simple_chat))
    results.append(test("History", test_history))

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total-passed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    exit(main())
