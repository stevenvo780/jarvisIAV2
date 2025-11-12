#!/usr/bin/env python3
"""Test simple final - Validación completa rápida"""
import requests
import time

BASE_URL = "http://localhost:8090"

print("="*60)
print("🔥 TEST SIMPLE FINAL - JARVIS IA V2")
print("="*60)

# Test 1: Health
print("\n1. Testing /health...")
r = requests.get(f"{BASE_URL}/health", timeout=5)
assert r.status_code == 200
print(f"✅ Health: {r.json()}")

# Test 2: Status
print("\n2. Testing /api/status...")
r = requests.get(f"{BASE_URL}/api/status", timeout=5)
assert r.status_code == 200
data = r.json()
print(f"✅ Status: {data['status']}, Models: {data['models_loaded']}")

# Test 3: Chat simple
print("\n3. Testing /api/chat (puede tomar 1-3 minutos)...")
start = time.time()
r = requests.post(
    f"{BASE_URL}/api/chat",
    json={"message": "Di solo: OK"},
    timeout=300  # 5 minutos máximo
)
elapsed = time.time() - start
assert r.status_code == 200
response = r.json()["response"]
print(f"✅ Chat completado en {elapsed:.1f}s")
print(f"   Respuesta: {response[:100]}...")

# Test 4: History
print("\n4. Testing /api/history...")
r = requests.get(f"{BASE_URL}/api/history", timeout=5)
assert r.status_code == 200
count = len(r.json())
print(f"✅ History: {count} mensajes")

print("\n" + "="*60)
print("✅ TODOS LOS TESTS PASARON!")
print("="*60)
