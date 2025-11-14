#!/usr/bin/env python3
"""
Test Suite Simple usando unittest (no requiere pytest)
Prueba todos los componentes críticos del sistema
"""

import unittest
import time
import sys
from pathlib import Path
import urllib.request
import urllib.error
import json

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

BASE_URL = "http://localhost:8090"


class TestWebAPIHealth(unittest.TestCase):
    """Tests básicos de la API Web"""
    
    @classmethod
    def setUpClass(cls):
        """Espera a que el servidor esté disponible"""
        print("\n🔍 Esperando a que el servidor esté listo...")
        max_retries = 30
        for i in range(max_retries):
            try:
                req = urllib.request.Request(f"{BASE_URL}/health")
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        print("✅ Servidor listo\n")
                        return
            except (urllib.error.URLError, Exception):
                if i < max_retries - 1:
                    time.sleep(2)
                    print(".", end="", flush=True)
        raise Exception("❌ Servidor no disponible después de 60 segundos")
    
    def test_01_health_endpoint(self):
        """Verifica el endpoint de health"""
        print("\n🧪 Test 1: Health endpoint...")
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode())
            self.assertIn("status", data)
            print(f"   ✓ Status: {data['status']}")
    
    def test_02_health_response_time(self):
        """Verifica que health responda rápidamente"""
        print("\n🧪 Test 2: Tiempo de respuesta de health...")
        start = time.time()
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            elapsed = time.time() - start
            self.assertEqual(response.status, 200)
            self.assertLess(elapsed, 2.0, f"Health tardó {elapsed:.2f}s")
            print(f"   ✓ Tiempo de respuesta: {elapsed:.3f}s")


class TestWebAPIChatBasic(unittest.TestCase):
    """Tests básicos del endpoint de chat"""
    
    def test_03_chat_endpoint_simple(self):
        """Prueba básica del endpoint de chat"""
        print("\n🧪 Test 3: Chat endpoint simple...")
        
        payload = json.dumps({
            "message": "¿Qué es 2+2?",
            "stream": False
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{BASE_URL}/api/chat",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())
                self.assertIn("response", data)
                self.assertGreater(len(data["response"]), 0)
                print(f"   ✓ Respuesta recibida: {len(data['response'])} caracteres")
                print(f"   📝 Respuesta: {data['response'][:100]}...")
        except urllib.error.HTTPError as e:
            print(f"   ⚠️ Error HTTP {e.code}: {e.read().decode()}")
            raise
    
    def test_04_chat_with_context(self):
        """Prueba chat con contexto simple"""
        print("\n🧪 Test 4: Chat con contexto...")
        
        payload = json.dumps({
            "message": "¿Cuál es la capital de Francia?",
            "stream": False
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{BASE_URL}/api/chat",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())
                self.assertIn("response", data)
                response_lower = data["response"].lower()
                # Verificar que mencione París en alguna forma
                self.assertTrue(
                    "parís" in response_lower or "paris" in response_lower,
                    f"Respuesta no menciona París: {data['response'][:200]}"
                )
                print(f"   ✓ Respuesta correcta sobre París")
                print(f"   📝 Respuesta: {data['response'][:150]}...")
        except urllib.error.HTTPError as e:
            print(f"   ⚠️ Error HTTP {e.code}: {e.read().decode()}")
            raise


class TestErrorHandling(unittest.TestCase):
    """Tests para manejo de errores"""
    
    def test_05_invalid_endpoint(self):
        """Verifica manejo de endpoints inválidos"""
        print("\n🧪 Test 5: Endpoint inválido...")
        
        req = urllib.request.Request(f"{BASE_URL}/invalid/endpoint")
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("Debería haber lanzado un error 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            print(f"   ✓ Error 404 manejado correctamente")
    
    def test_06_empty_chat_message(self):
        """Verifica manejo de mensajes vacíos"""
        print("\n🧪 Test 6: Mensaje vacío...")
        
        payload = json.dumps({"message": "", "stream": False}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{BASE_URL}/api/chat",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            urllib.request.urlopen(req, timeout=5)
            # Si no da error, al menos verificar que responda
            print(f"   ⚠️ Servidor acepta mensajes vacíos")
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, [400, 422])
            print(f"   ✓ Error {e.code} manejado correctamente")


class TestSystemState(unittest.TestCase):
    """Tests para el estado del sistema"""
    
    def test_07_logs_directory(self):
        """Verifica que el directorio de logs exista"""
        print("\n🧪 Test 7: Directorio de logs...")
        logs_dir = PROJECT_ROOT / "logs"
        self.assertTrue(logs_dir.exists(), "Directorio de logs no existe")
        print(f"   ✓ Directorio de logs existe: {logs_dir}")
    
    def test_08_models_directory(self):
        """Verifica que el directorio de modelos exista"""
        print("\n🧪 Test 8: Directorio de modelos...")
        models_dir = PROJECT_ROOT / "models"
        self.assertTrue(models_dir.exists(), "Directorio de modelos no existe")
        print(f"   ✓ Directorio de modelos existe: {models_dir}")
    
    def test_09_required_files(self):
        """Verifica que existan archivos requeridos"""
        print("\n🧪 Test 9: Archivos requeridos...")
        required_files = [
            "start_web.py",
            "main.py",
            "requirements.txt",
            "pyproject.toml"
        ]
        for filename in required_files:
            filepath = PROJECT_ROOT / filename
            self.assertTrue(filepath.exists(), f"{filename} no existe")
            print(f"   ✓ {filename} existe")


class TestGPUResources(unittest.TestCase):
    """Tests para recursos GPU"""
    
    def test_10_gpu_check(self):
        """Verifica estado de la GPU"""
        print("\n🧪 Test 10: Estado de GPU...")
        try:
            import torch
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                print(f"   ✓ GPU disponible: {device_count} dispositivo(s)")
                
                for i in range(device_count):
                    memory_allocated = torch.cuda.memory_allocated(i)
                    memory_total = torch.cuda.get_device_properties(i).total_memory
                    usage_mb = memory_allocated / (1024 * 1024)
                    total_gb = memory_total / (1024 * 1024 * 1024)
                    print(f"   📊 GPU {i}: {usage_mb:.0f}MB / {total_gb:.1f}GB")
            else:
                print(f"   ⚠️ GPU no disponible (ejecutando en CPU)")
        except ImportError:
            print(f"   ⚠️ PyTorch no instalado, saltando test GPU")


def run_tests():
    """Ejecuta todos los tests con output detallado"""
    print("=" * 60)
    print("🧪 SUITE DE TESTS AUTOMATIZADOS - JARVIS IA V2")
    print("=" * 60)
    
    # Crear test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar tests en orden
    suite.addTests(loader.loadTestsFromTestCase(TestWebAPIHealth))
    suite.addTests(loader.loadTestsFromTestCase(TestWebAPIChatBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestSystemState))
    suite.addTests(loader.loadTestsFromTestCase(TestGPUResources))
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE TESTS")
    print("=" * 60)
    print(f"✅ Tests exitosos: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Tests fallidos: {len(result.failures)}")
    print(f"⚠️  Errores: {len(result.errors)}")
    print(f"⏭️  Tests omitidos: {len(result.skipped)}")
    print("=" * 60)
    
    if result.wasSuccessful():
        print("\n🎉 ¡TODOS LOS TESTS PASARON EXITOSAMENTE!")
        return 0
    else:
        print("\n⚠️  ALGUNOS TESTS FALLARON")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
