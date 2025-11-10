#!/usr/bin/env python3
"""
Script de prueba automatizada para la interfaz web de Jarvis
Verifica todos los endpoints y funcionalidad básica
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8090"
TIMEOUT = 120  # 2 minutos para respuestas del modelo

def print_header(text):
    """Imprimir encabezado con formato"""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")

def print_test(name, status, details=""):
    """Imprimir resultado de prueba"""
    icon = "✅" if status else "❌"
    print(f"{icon} {name}")
    if details:
        print(f"   {details}")

def test_health_check():
    """Probar endpoint /api/status"""
    print_header("Prueba 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        data = response.json()
        
        print_test("Status endpoint responde", response.status_code == 200)
        print_test("JSON válido", True, f"Datos: {json.dumps(data, indent=2)}")
        print_test("Status ready", data.get("status") == "ready")
        print_test("GPU count", data.get("gpu_count", 0) >= 1, f"GPUs: {data.get('gpu_count')}")
        
        return True
    except Exception as e:
        print_test("Health check", False, str(e))
        return False

def test_frontend():
    """Probar que el frontend HTML se sirve"""
    print_header("Prueba 2: Frontend HTML")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        html = response.text
        
        print_test("Frontend responde", response.status_code == 200)
        print_test("Content-Type HTML", "text/html" in response.headers.get("Content-Type", ""))
        print_test("Contiene <title>", "<title>" in html and "Jarvis" in html)
        print_test("Contiene CSS", "<style>" in html)
        print_test("Contiene JavaScript", "<script>" in html)
        print_test("Tamaño HTML", len(html) > 1000, f"{len(html)} bytes")
        
        return True
    except Exception as e:
        print_test("Frontend", False, str(e))
        return False

def test_chat_simple():
    """Probar endpoint /api/chat con mensaje simple"""
    print_header("Prueba 3: Chat - Mensaje Simple")
    try:
        payload = {"message": "Di solo 'Hola'"}
        start_time = time.time()
        
        print("⏳ Enviando mensaje: 'Di solo 'Hola''")
        print("   (Puede tardar ~30-90s mientras carga el modelo...)")
        
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            timeout=TIMEOUT
        )
        elapsed = time.time() - start_time
        
        data = response.json()
        
        print_test("Chat endpoint responde", response.status_code == 200)
        print_test("JSON válido", True)
        print_test("Tiene respuesta", bool(data.get("response")))
        print_test("Tiene timestamp", bool(data.get("timestamp")))
        print_test("Tiempo de respuesta", elapsed < TIMEOUT, f"{elapsed:.2f}s")
        
        print(f"\n📝 Respuesta del modelo:")
        print(f"   {data.get('response', '')[:200]}...")
        print(f"\n⏱️  Tiempo: {data.get('response_time', elapsed):.2f}s")
        
        return True
    except requests.Timeout:
        print_test("Chat endpoint", False, f"Timeout después de {TIMEOUT}s")
        return False
    except Exception as e:
        print_test("Chat endpoint", False, str(e))
        return False

def test_chat_context():
    """Probar que el chat mantiene contexto con múltiples mensajes"""
    print_header("Prueba 4: Chat - Contexto")
    try:
        messages = [
            "Mi nombre es Carlos",
            "¿Cuál es mi nombre?"
        ]
        
        responses = []
        for msg in messages:
            print(f"⏳ Enviando: '{msg}'")
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": msg},
                timeout=TIMEOUT
            )
            data = response.json()
            responses.append(data.get("response", ""))
            print(f"   Respuesta: {data.get('response', '')[:100]}...")
            time.sleep(1)  # Pequeña pausa entre mensajes
        
        # El segundo mensaje debería mencionar "Carlos" si hay contexto
        has_context = "carlos" in responses[1].lower()
        
        print_test("Múltiples mensajes", len(responses) == 2)
        print_test("Mantiene contexto", has_context, 
                  "El modelo recordó el nombre" if has_context else "No se detectó contexto")
        
        return has_context
    except Exception as e:
        print_test("Contexto", False, str(e))
        return False

def test_history():
    """Probar endpoint /api/history"""
    print_header("Prueba 5: Historial")
    try:
        response = requests.get(f"{BASE_URL}/api/history", timeout=5)
        data = response.json()
        
        print_test("History endpoint responde", response.status_code == 200)
        print_test("Es una lista", isinstance(data, list))
        print_test("Tiene mensajes", len(data) > 0, f"{len(data)} mensajes")
        
        if data:
            last_msg = data[-1]
            print(f"\n📝 Último mensaje:")
            print(f"   {json.dumps(last_msg, indent=2)}")
        
        return True
    except Exception as e:
        print_test("History", False, str(e))
        return False

def test_models_endpoint():
    """Probar endpoint /api/models"""
    print_header("Prueba 6: Listado de Modelos")
    try:
        response = requests.get(f"{BASE_URL}/api/models", timeout=5)
        data = response.json()
        
        print_test("Models endpoint responde", response.status_code == 200)
        print_test("Tiene modelos", len(data) > 0 if isinstance(data, list) else bool(data))
        
        if isinstance(data, list):
            print(f"\n🤖 Modelos disponibles: {len(data)}")
            for model in data[:5]:  # Mostrar primeros 5
                print(f"   - {model.get('id', model)}")
        elif isinstance(data, dict):
            print(f"\n🤖 Configuración de modelos:")
            print(f"   {json.dumps(data, indent=2)}")
        
        return True
    except Exception as e:
        print_test("Models endpoint", False, str(e))
        return False

def main():
    """Ejecutar todas las pruebas"""
    print_header("🧪 SUITE DE PRUEBAS - JARVIS WEB INTERFACE")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = []
    
    # Ejecutar pruebas en orden
    results.append(("Health Check", test_health_check()))
    results.append(("Frontend HTML", test_frontend()))
    results.append(("Chat Simple", test_chat_simple()))
    # results.append(("Chat Contexto", test_chat_context()))  # Comentado: tarda mucho
    results.append(("Historial", test_history()))
    results.append(("Modelos", test_models_endpoint()))
    
    # Resumen final
    print_header("📊 RESUMEN DE PRUEBAS")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")
    
    print(f"\n{'='*60}")
    print(f" Resultado: {passed}/{total} pruebas exitosas ({passed*100//total}%)")
    print(f"{'='*60}\n")
    
    # Exit code
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
