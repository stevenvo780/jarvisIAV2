#!/usr/bin/env python3
"""
Test Suite Automatizada Completa para JarvisIA V2
Prueba todos los componentes críticos del sistema
"""

import pytest
import asyncio
import os
import sys
import time
from pathlib import Path
import requests
import torch

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))


class TestGPUResources:
    """Tests para verificar recursos GPU"""
    
    def test_gpu_available(self):
        """Verifica que la GPU esté disponible"""
        assert torch.cuda.is_available(), "GPU no disponible"
        
    def test_gpu_memory_clean(self):
        """Verifica que la memoria GPU esté limpia al inicio"""
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                memory_allocated = torch.cuda.memory_allocated(i)
                memory_total = torch.cuda.get_device_properties(i).total_memory
                usage_percent = (memory_allocated / memory_total) * 100
                assert usage_percent < 50, f"GPU {i} tiene {usage_percent:.1f}% de memoria ocupada"


class TestWebAPI:
    """Tests para la API Web"""
    
    BASE_URL = "http://localhost:8090"
    
    @pytest.fixture(autouse=True)
    def wait_for_server(self):
        """Espera a que el servidor esté disponible"""
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.BASE_URL}/health", timeout=2)
                if response.status_code == 200:
                    return
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    time.sleep(2)
                else:
                    pytest.skip("Servidor no disponible después de 60 segundos")
    
    def test_health_endpoint(self):
        """Verifica el endpoint de health"""
        response = requests.get(f"{self.BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime" in data
        
    def test_models_status(self):
        """Verifica el estado de los modelos"""
        response = requests.get(f"{self.BASE_URL}/models/status", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        
    def test_chat_endpoint_basic(self):
        """Prueba básica del endpoint de chat"""
        payload = {
            "message": "Hola, ¿qué hora es?",
            "stream": False
        }
        response = requests.post(
            f"{self.BASE_URL}/chat",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
        
    def test_chat_with_history(self):
        """Prueba chat con historial"""
        payload = {
            "message": "¿Cuál es la capital de Francia?",
            "history": [
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "Hola, ¿en qué puedo ayudarte?"}
            ],
            "stream": False
        }
        response = requests.post(
            f"{self.BASE_URL}/chat",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "París" in data["response"] or "Paris" in data["response"]


class TestSystemState:
    """Tests para el estado del sistema"""
    
    def test_logs_directory(self):
        """Verifica que el directorio de logs exista"""
        logs_dir = PROJECT_ROOT / "logs"
        assert logs_dir.exists(), "Directorio de logs no existe"
        
    def test_models_directory(self):
        """Verifica que el directorio de modelos exista"""
        models_dir = PROJECT_ROOT / "models"
        assert models_dir.exists(), "Directorio de modelos no existe"
        
    def test_vectorstore_directory(self):
        """Verifica que el directorio de vectorstore exista"""
        vectorstore_dir = PROJECT_ROOT / "vectorstore"
        assert vectorstore_dir.exists(), "Directorio de vectorstore no existe"


class TestModelOrchestrator:
    """Tests para el orquestador de modelos"""
    
    @pytest.fixture
    def orchestrator(self):
        """Crea una instancia del orquestador"""
        from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
        return ModelOrchestrator()
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Verifica que el orquestador se inicialice correctamente"""
        assert orchestrator is not None
        
    @pytest.mark.asyncio
    async def test_simple_query(self, orchestrator):
        """Prueba una consulta simple"""
        response = await orchestrator.process_query("¿Qué es Python?")
        assert response is not None
        assert len(response) > 0
        assert "Python" in response or "python" in response


class TestErrorHandling:
    """Tests para manejo de errores"""
    
    BASE_URL = "http://localhost:8090"
    
    def test_invalid_endpoint(self):
        """Verifica manejo de endpoints inválidos"""
        response = requests.get(f"{self.BASE_URL}/invalid/endpoint", timeout=5)
        assert response.status_code == 404
        
    def test_empty_chat_message(self):
        """Verifica manejo de mensajes vacíos"""
        payload = {"message": "", "stream": False}
        response = requests.post(f"{self.BASE_URL}/chat", json=payload, timeout=5)
        assert response.status_code in [400, 422]
        
    def test_malformed_request(self):
        """Verifica manejo de requests mal formados"""
        response = requests.post(
            f"{self.BASE_URL}/chat",
            json={"invalid_field": "test"},
            timeout=5
        )
        assert response.status_code in [400, 422]


class TestPerformance:
    """Tests de rendimiento básicos"""
    
    BASE_URL = "http://localhost:8090"
    
    def test_health_response_time(self):
        """Verifica que health responda rápidamente"""
        start = time.time()
        response = requests.get(f"{self.BASE_URL}/health", timeout=5)
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"Health tardó {elapsed:.2f}s"
        
    def test_concurrent_health_checks(self):
        """Verifica múltiples health checks concurrentes"""
        import concurrent.futures
        
        def check_health():
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            return response.status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_health) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert all(results), "Algunos health checks fallaron"


class TestMemoryManagement:
    """Tests para manejo de memoria"""
    
    def test_gpu_memory_not_leaking(self):
        """Verifica que no haya memory leaks en GPU"""
        if not torch.cuda.is_available():
            pytest.skip("GPU no disponible")
            
        initial_memory = torch.cuda.memory_allocated(0)
        
        # Simular operaciones
        for _ in range(5):
            tensor = torch.randn(100, 100).cuda()
            del tensor
            torch.cuda.empty_cache()
        
        final_memory = torch.cuda.memory_allocated(0)
        memory_diff = abs(final_memory - initial_memory)
        
        # Permitir una diferencia pequeña
        assert memory_diff < 10 * 1024 * 1024, f"Memory leak detectado: {memory_diff / 1024 / 1024:.2f} MB"


@pytest.mark.integration
class TestIntegrationFlow:
    """Tests de flujo de integración completo"""
    
    BASE_URL = "http://localhost:8090"
    
    def test_complete_conversation_flow(self):
        """Prueba un flujo completo de conversación"""
        # 1. Verificar salud
        health_response = requests.get(f"{self.BASE_URL}/health", timeout=5)
        assert health_response.status_code == 200
        
        # 2. Primera pregunta
        response1 = requests.post(
            f"{self.BASE_URL}/chat",
            json={"message": "Hola, ¿cómo te llamas?", "stream": False},
            timeout=30
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert "response" in data1
        
        # 3. Segunda pregunta con contexto
        response2 = requests.post(
            f"{self.BASE_URL}/chat",
            json={
                "message": "¿Qué es un algoritmo?",
                "history": [
                    {"role": "user", "content": "Hola, ¿cómo te llamas?"},
                    {"role": "assistant", "content": data1["response"]}
                ],
                "stream": False
            },
            timeout=30
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert "algoritmo" in data2["response"].lower()
        
        # 4. Verificar estado final
        final_health = requests.get(f"{self.BASE_URL}/health", timeout=5)
        assert final_health.status_code == 200


if __name__ == "__main__":
    # Ejecutar tests con verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
