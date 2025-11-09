"""
Test suite for Quick Win 6: Healthcheck Endpoint

Validates:
- Health API initialization
- /health endpoint functionality
- /health/live liveness probe
- /health/ready readiness probe
- GPU/models/RAG checks
"""
import os
import pytest
import torch
import time
from unittest.mock import Mock, MagicMock, patch
from src.api.healthcheck import HealthcheckAPI, HealthStatus, start_healthcheck_api


class TestHealthcheckAPI:
    """Tests para el Health API."""
    
    @pytest.fixture
    def mock_jarvis(self):
        """Mock de instancia de Jarvis."""
        jarvis = Mock()
        
        # Mock state
        jarvis.state = Mock()
        jarvis.state.running = True
        jarvis.state.voice_active = False
        jarvis.state.listening_active = False
        jarvis.state.error_count = 0
        jarvis.state.max_errors = 5
        
        # Mock orchestrator
        jarvis.orchestrator = Mock()
        jarvis.orchestrator.model = Mock()  # Modelo principal cargado
        jarvis.orchestrator.fallback_models = {}
        
        # Mock embeddings
        jarvis.embeddings = Mock()
        jarvis.embeddings.collection = Mock()
        jarvis.embeddings.collection.count.return_value = 150  # 150 documentos
        jarvis.embeddings.model = Mock()
        
        return jarvis
    
    @pytest.fixture
    def health_api(self, mock_jarvis):
        """Instancia de HealthcheckAPI."""
        return HealthcheckAPI(jarvis_instance=mock_jarvis, port=8081)
    
    def test_initialization(self, health_api):
        """Test: Inicialización correcta del API."""
        assert health_api.app is not None
        assert health_api.port == 8081
        assert health_api.start_time is not None
    
    def test_gpu_check_available(self, health_api):
        """Test: Check de GPU cuando CUDA está disponible."""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        result = health_api._check_gpu()
        
        assert result["available"] is True
        assert result["count"] > 0
        assert "gpus" in result
        assert len(result["gpus"]) == result["count"]
        
        # Verificar info de cada GPU
        for gpu in result["gpus"]:
            assert "id" in gpu
            assert "name" in gpu
            assert "memory_total_gb" in gpu
            assert "memory_used_gb" in gpu
            assert "memory_free_gb" in gpu
            assert "memory_usage_percent" in gpu
    
    def test_gpu_check_unavailable(self, health_api):
        """Test: Check de GPU cuando CUDA NO está disponible."""
        with patch('torch.cuda.is_available', return_value=False):
            result = health_api._check_gpu()
            
            assert result["available"] is False
            assert result["count"] == 0
            assert "reason" in result
    
    def test_models_check_loaded(self, health_api, mock_jarvis):
        """Test: Check de modelos cuando están cargados."""
        result = health_api._check_models()
        
        assert result["loaded"] is True
        assert result["primary_model"] is True
        assert "total_models" in result
    
    def test_models_check_no_jarvis(self):
        """Test: Check de modelos sin instancia de Jarvis."""
        api = HealthcheckAPI(jarvis_instance=None, port=8082)
        result = api._check_models()
        
        assert result["loaded"] is False
        assert "reason" in result
    
    def test_rag_check_operational(self, health_api):
        """Test: Check de RAG cuando está operacional."""
        result = health_api._check_rag()
        
        assert result["operational"] is True
        assert result["chromadb_ok"] is True
        assert result["model_ok"] is True
        assert result["documents_count"] == 150
    
    def test_rag_check_disabled(self):
        """Test: Check de RAG cuando está deshabilitado."""
        jarvis = Mock()
        jarvis.embeddings = None
        
        api = HealthcheckAPI(jarvis_instance=jarvis, port=8083)
        result = api._check_rag()
        
        assert result["operational"] is False
        assert "reason" in result
    
    def test_disk_check(self, health_api):
        """Test: Check de espacio en disco."""
        result = health_api._check_disk()
        
        assert result["available"] is True
        assert result["total_gb"] > 0
        assert result["free_gb"] >= 0
        assert 0 <= result["usage_percent"] <= 100
    
    def test_memory_check(self, health_api):
        """Test: Check de memoria RAM."""
        result = health_api._check_memory()
        
        assert result["available"] is True
        assert result["total_gb"] > 0
        assert result["free_gb"] >= 0
        assert 0 <= result["usage_percent"] <= 100
    
    def test_jarvis_state_check(self, health_api):
        """Test: Check de estado de Jarvis."""
        result = health_api._check_jarvis_state()
        
        assert result["running"] is True
        assert result["error_count"] == 0
        assert result["max_errors"] == 5
    
    @pytest.mark.asyncio
    async def test_health_endpoint_healthy(self, health_api):
        """Test: Endpoint /health retorna estado healthy."""
        from fastapi.testclient import TestClient
        
        with TestClient(health_api.app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "status" in data
            assert data["status"] in ["healthy", "degraded", "unhealthy"]
            assert "timestamp" in data
            assert "uptime_seconds" in data
            assert "checks" in data
            assert "version" in data
            
            # Verificar checks individuales
            checks = data["checks"]
            assert "gpu" in checks
            assert "models" in checks
            assert "rag" in checks
            assert "disk" in checks
            assert "memory" in checks
            assert "jarvis" in checks
    
    @pytest.mark.asyncio
    async def test_liveness_probe(self, health_api):
        """Test: Endpoint /health/live (liveness probe)."""
        from fastapi.testclient import TestClient
        
        with TestClient(health_api.app) as client:
            response = client.get("/health/live")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "alive"
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_readiness_probe_ready(self, health_api):
        """Test: Endpoint /health/ready (readiness probe) cuando está listo."""
        from fastapi.testclient import TestClient
        
        with TestClient(health_api.app) as client:
            response = client.get("/health/ready")
            
            # Puede ser 200 (ready) o 503 (not ready) dependiendo de si hay GPU
            assert response.status_code in [200, 503]
            data = response.json()
            
            assert "status" in data
            assert data["status"] in ["ready", "not_ready"]
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, health_api):
        """Test: Root endpoint (/)."""
        from fastapi.testclient import TestClient
        
        with TestClient(health_api.app) as client:
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["service"] == "JarvisIA V2 Health API"
            assert data["version"] == "2.0"
            assert "endpoints" in data
    
    def test_start_healthcheck_helper(self, mock_jarvis):
        """Test: Helper start_healthcheck_api."""
        api = start_healthcheck_api(
            jarvis_instance=mock_jarvis,
            port=8084,
            background=False  # No iniciar servidor real
        )
        
        assert api is not None
        assert isinstance(api, HealthcheckAPI)
        assert api.port == 8084


class TestHealthStatusModel:
    """Tests para el modelo Pydantic HealthStatus."""
    
    def test_health_status_creation(self):
        """Test: Creación del modelo HealthStatus."""
        status = HealthStatus(
            status="healthy",
            timestamp="2025-01-15T19:00:00",
            uptime_seconds=120.5,
            checks={
                "gpu": {"available": True},
                "models": {"loaded": True}
            }
        )
        
        assert status.status == "healthy"
        assert status.version == "2.0"
        assert status.uptime_seconds == 120.5
    
    def test_health_status_dict(self):
        """Test: Conversión a dict."""
        status = HealthStatus(
            status="degraded",
            timestamp="2025-01-15T19:00:00",
            uptime_seconds=60.0,
            checks={}
        )
        
        data = status.dict()
        
        assert data["status"] == "degraded"
        assert data["version"] == "2.0"
        assert isinstance(data["checks"], dict)


@pytest.mark.integration
class TestHealthcheckIntegration:
    """Tests de integración del Health API."""
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires GPU")
    def test_full_health_check_with_gpu(self):
        """Test: Healthcheck completo con GPU real."""
        jarvis = Mock()
        jarvis.state = Mock(running=True, error_count=0, max_errors=5)
        jarvis.orchestrator = Mock(model=Mock(), fallback_models={})
        jarvis.embeddings = Mock(
            collection=Mock(count=Mock(return_value=100)),
            model=Mock()
        )
        
        api = HealthcheckAPI(jarvis_instance=jarvis, port=8085)
        
        # Simular request
        from fastapi.testclient import TestClient
        with TestClient(api.app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # GPU debe estar disponible
            assert data["checks"]["gpu"]["available"] is True
            assert data["checks"]["gpu"]["count"] > 0


def test_health_api_environment_variables():
    """Test: Variables de entorno para configuración."""
    # Test ENABLE_HEALTH_API
    with patch.dict(os.environ, {'ENABLE_HEALTH_API': 'false'}):
        enable = os.getenv('ENABLE_HEALTH_API', 'true').lower() == 'true'
        assert enable is False
    
    # Test HEALTH_API_PORT
    with patch.dict(os.environ, {'HEALTH_API_PORT': '9090'}):
        port = int(os.getenv('HEALTH_API_PORT', '8080'))
        assert port == 9090


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
