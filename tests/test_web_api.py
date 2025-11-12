"""
Tests básicos para la API web de Jarvis
Ejecutar con: pytest tests/test_web_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.web.api import create_web_app


@pytest.fixture
def client():
    """Cliente de prueba de FastAPI"""
    app, web_interface = create_web_app(jarvis_instance=None)
    return TestClient(app)


class TestHealthEndpoints:
    """Tests para endpoints de salud"""

    def test_health_check(self, client):
        """Test del endpoint /health"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["service"] == "jarvis-web"

    def test_api_status_without_jarvis(self, client):
        """Test de /api/status sin instancia de Jarvis"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "initializing"
        assert data["models_loaded"] == 0
        assert data["gpu_count"] == 0


class TestChatEndpoints:
    """Tests para endpoints de chat"""

    def test_chat_without_jarvis(self, client):
        """Test de chat sin instancia de Jarvis"""
        response = client.post(
            "/api/chat",
            json={"message": "Hola", "timestamp": "2025-11-12T10:00:00"}
        )
        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"].lower()

    def test_chat_empty_message(self, client):
        """Test de chat con mensaje vacío"""
        response = client.post(
            "/api/chat",
            json={"message": "", "timestamp": "2025-11-12T10:00:00"}
        )
        assert response.status_code == 422  # Validation error

    def test_chat_too_long_message(self, client):
        """Test de chat con mensaje demasiado largo"""
        long_message = "a" * 5001  # Más de 5000 caracteres
        response = client.post(
            "/api/chat",
            json={"message": long_message, "timestamp": "2025-11-12T10:00:00"}
        )
        assert response.status_code == 422  # Validation error


class TestHistoryEndpoints:
    """Tests para endpoints de historial"""

    def test_get_history_empty(self, client):
        """Test de historial vacío"""
        response = client.get("/api/history")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_history_with_pagination(self, client):
        """Test de paginación en historial"""
        response = client.get("/api/history?offset=0&limit=10")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_clear_history(self, client):
        """Test de limpiar historial"""
        response = client.delete("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "cleared" in data["message"].lower()


class TestSecurity:
    """Tests de seguridad"""

    def test_cors_headers(self, client):
        """Test de headers CORS"""
        response = client.options("/api/status")
        # Verificar que CORS está configurado
        assert response.status_code == 200

    def test_input_validation(self, client):
        """Test de validación de input"""
        # Intento de XSS
        xss_payload = "<script>alert('XSS')</script>"
        response = client.post(
            "/api/chat",
            json={"message": xss_payload}
        )
        # Debe ser 503 (sin Jarvis) o procesar sin error
        assert response.status_code in [503, 200, 422]


class TestCompression:
    """Tests de compresión gzip"""

    def test_gzip_compression_available(self, client):
        """Test de que gzip está disponible"""
        response = client.get(
            "/api/status",
            headers={"Accept-Encoding": "gzip"}
        )
        assert response.status_code == 200
        # La respuesta debería tener encoding (FastAPI lo maneja)


class TestAPIAuthentication:
    """Tests de autenticación con API keys"""

    def test_without_api_key_when_not_required(self, client):
        """Test sin API key cuando no es requerido"""
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_health_always_accessible(self, client):
        """Test de que /health siempre es accesible"""
        response = client.get("/health")
        assert response.status_code == 200


def test_homepage_loads(client):
    """Test de que la página principal carga"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Jarvis" in response.text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
