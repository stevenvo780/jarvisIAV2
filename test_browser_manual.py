#!/usr/bin/env python3
"""
Pruebas del navegador usando requests para simular interacciones
Ya que Playwright no está disponible, simulamos las pruebas del navegador
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8090"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_homepage():
    """Prueba que la página principal carga"""
    print_section("🌐 PRUEBA 1: Cargar Página Principal")
    
    try:
        response = requests.get(BASE_URL, timeout=5)
        html = response.text
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Content-Type: {response.headers.get('Content-Type')}")
        print(f"✅ Tamaño HTML: {len(html)} bytes")
        
        # Verificar elementos clave
        checks = {
            "Título": "Jarvis" in html and "<title>" in html,
            "CSS": "<style>" in html and "var(--primary-bg)" in html,
            "JavaScript": "<script>" in html and "sendMessage" in html,
            "Input de chat": 'id="user-input"' in html or 'id="userInput"' in html,
            "Botón enviar": 'id="send-button"' in html or 'button' in html.lower(),
            "Contenedor de mensajes": 'id="messages"' in html or 'class="message' in html
        }
        
        print("\n📋 Elementos verificados:")
        for elemento, presente in checks.items():
            icon = "✅" if presente else "❌"
            print(f"   {icon} {elemento}")
        
        return all(checks.values())
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_send_message(message, wait_time=90):
    """Prueba enviar un mensaje al chat"""
    print_section(f"💬 PRUEBA 2: Enviar Mensaje '{message}'")
    
    try:
        payload = {"message": message}
        print(f"📤 Enviando mensaje...")
        print(f"   Mensaje: {message}")
        print(f"   Esperando respuesta (puede tardar hasta {wait_time}s)...")
        
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            timeout=wait_time
        )
        elapsed = time.time() - start
        
        data = response.json()
        
        print(f"\n✅ Status Code: {response.status_code}")
        print(f"✅ Tiempo de respuesta: {elapsed:.2f}s")
        print(f"✅ Timestamp: {data.get('timestamp', 'N/A')}")
        
        response_text = data.get('response', '')
        if response_text:
            print(f"\n📝 Respuesta del modelo:")
            print(f"   {response_text[:300]}...")
            print(f"\n   Longitud total: {len(response_text)} caracteres")
        
        if data.get('response_time'):
            print(f"   Tiempo reportado: {data['response_time']:.2f}s")
        
        return bool(response_text) and not response_text.startswith("Error:")
    
    except requests.Timeout:
        print(f"❌ Timeout después de {wait_time}s")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_history():
    """Prueba obtener el historial"""
    print_section("📜 PRUEBA 3: Historial de Chat")
    
    try:
        response = requests.get(f"{BASE_URL}/api/history", timeout=5)
        data = response.json()
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Mensajes en historial: {len(data)}")
        
        if data:
            print(f"\n📋 Últimos 3 mensajes:")
            for i, msg in enumerate(data[-3:], 1):
                user_msg = msg.get('user', 'N/A')[:50]
                assistant_msg = msg.get('assistant', 'N/A')[:50]
                print(f"\n   {i}. Usuario: {user_msg}...")
                print(f"      Jarvis: {assistant_msg}...")
        
        return len(data) > 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_multiple_messages():
    """Prueba enviar múltiples mensajes simulando una conversación"""
    print_section("🔄 PRUEBA 4: Conversación Múltiple")
    
    messages = [
        "Hola",
        "¿Qué tiempo hace hoy?",
    ]
    
    results = []
    for i, msg in enumerate(messages, 1):
        print(f"\n--- Mensaje {i}/{len(messages)} ---")
        print(f"💬 Enviando: '{msg}'")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": msg},
                timeout=90
            )
            data = response.json()
            response_text = data.get('response', '')
            
            if response_text and not response_text.startswith("Error:"):
                print(f"✅ Respuesta recibida ({len(response_text)} chars)")
                print(f"   {response_text[:100]}...")
                results.append(True)
            else:
                print(f"❌ Respuesta con error")
                results.append(False)
            
            # Pausa entre mensajes
            if i < len(messages):
                time.sleep(2)
        
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Tasa de éxito: {success_rate:.0f}% ({sum(results)}/{len(results)} mensajes)")
    
    return success_rate >= 50

def test_ui_responsiveness():
    """Prueba que la UI responde rápidamente"""
    print_section("⚡ PRUEBA 5: Velocidad de Respuesta UI")
    
    endpoints = [
        ("/", "Página principal"),
        ("/api/status", "Status API"),
        ("/api/history", "Historial"),
    ]
    
    results = []
    for endpoint, name in endpoints:
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            elapsed = (time.time() - start) * 1000  # en ms
            
            fast = elapsed < 1000  # Menos de 1 segundo
            icon = "✅" if fast else "⚠️"
            print(f"{icon} {name}: {elapsed:.0f}ms")
            results.append(fast)
        
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            results.append(False)
    
    return all(results)

def main():
    print_section("🧪 SUITE DE PRUEBAS DE NAVEGADOR - JARVIS WEB")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Verificar que el servidor esté activo
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code != 200:
            print(f"\n❌ ERROR: Servidor no responde correctamente")
            print(f"   Asegúrate de que el servidor esté corriendo en {BASE_URL}")
            return
    except Exception as e:
        print(f"\n❌ ERROR: No se puede conectar al servidor")
        print(f"   {e}")
        print(f"\n   Ejecuta primero: python3 start_web.py")
        return
    
    print("\n✅ Servidor verificado, iniciando pruebas...\n")
    time.sleep(1)
    
    # Ejecutar pruebas
    tests = [
        ("Cargar Homepage", test_homepage),
        ("Enviar Mensaje Simple", lambda: test_send_message("Hola")),
        ("Verificar Historial", test_history),
        ("Conversación Múltiple", test_multiple_messages),
        ("Velocidad UI", test_ui_responsiveness),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error en prueba '{name}': {e}")
            results.append((name, False))
        
        time.sleep(1)
    
    # Resumen
    print_section("📊 RESUMEN DE PRUEBAS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")
    
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"  Resultado Final: {passed}/{total} pruebas exitosas ({percentage:.0f}%)")
    print(f"{'='*70}\n")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La interfaz web funciona correctamente.")
    elif passed >= total * 0.7:
        print("⚠️  La mayoría de pruebas pasaron, pero hay algunas fallas.")
    else:
        print("❌ Muchas pruebas fallaron. Revisa los logs del servidor.")

if __name__ == "__main__":
    main()
