"""
Tests unitarios para componentes clave de Jarvis IA V2
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


# ============================================================================
# TESTS PARA ERROR_HANDLER
# ============================================================================

class TestErrorHandler:
    """Tests para manejo de errores"""
    
    def test_jarvis_error_creation(self):
        """Test creación de JarvisError"""
        from src.utils.error_handler import JarvisError
        
        error = JarvisError("Test error", details={"key": "value"})
        assert error.message == "Test error"
        assert error.details == {"key": "value"}
        assert "timestamp" in error.to_dict()
    
    def test_error_hierarchy(self):
        """Test jerarquía de excepciones"""
        from src.utils.error_handler import (
            JarvisError, ModelError, ModelLoadError, 
            AudioError, ValidationError
        )
        
        # Verificar jerarquía
        assert issubclass(ModelError, JarvisError)
        assert issubclass(ModelLoadError, ModelError)
        assert issubclass(AudioError, JarvisError)
        assert issubclass(ValidationError, JarvisError)
    
    def test_handle_errors_decorator_success(self):
        """Test decorador handle_errors caso éxito"""
        from src.utils.error_handler import handle_errors
        
        @handle_errors(default_value="default")
        def success_function():
            return "success"
        
        result = success_function()
        assert result == "success"
    
    def test_handle_errors_decorator_failure(self):
        """Test decorador handle_errors caso fallo"""
        from src.utils.error_handler import handle_errors
        
        @handle_errors(error_type=ValueError, default_value="default")
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert result == "default"
    
    def test_handle_errors_with_retries(self):
        """Test decorador con reintentos"""
        from src.utils.error_handler import handle_errors
        
        call_count = 0
        
        @handle_errors(max_retries=2, default_value="default")
        def retry_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = retry_function()
        assert result == "success"
        assert call_count == 3


# ============================================================================
# TESTS PARA VALIDATORS
# ============================================================================

class TestValidators:
    """Tests para validadores"""
    
    def test_input_validator_basic(self):
        """Test validación básica de input"""
        from src.utils.validators import InputValidator
        
        validator = InputValidator()
        result = validator.validate("Hello world")
        
        assert result.is_valid
        assert len(result.cleaned_value) > 0
    
    def test_input_validator_too_short(self):
        """Test input muy corto"""
        from src.utils.validators import InputValidator
        
        validator = InputValidator(min_length=10)
        result = validator.validate("Hi")
        
        assert not result.is_valid
        assert "muy corto" in result.error_message.lower() or len(result.errors) > 0
    
    def test_input_validator_too_long(self):
        """Test input muy largo"""
        from src.utils.validators import InputValidator
        
        validator = InputValidator(max_length=10)
        long_text = "a" * 100
        result = validator.validate(long_text)
        
        assert len(result.cleaned_value) <= 10
    
    def test_sql_injection_detection(self):
        """Test detección de inyección SQL"""
        from src.utils.validators import InputValidator
        
        validator = InputValidator()
        malicious = "SELECT * FROM users WHERE 1=1; DROP TABLE users--"
        result = validator.validate(malicious)
        
        # Debe detectar patrón sospechoso
        assert not result.is_valid or len(result.warnings) > 0
    
    def test_query_validator_difficulty(self):
        """Test validación de dificultad"""
        from src.utils.validators import QueryValidator
        
        # Válido
        valid, msg = QueryValidator.validate_difficulty(50)
        assert valid
        
        # Inválido - fuera de rango
        valid, msg = QueryValidator.validate_difficulty(150)
        assert not valid
        
        # Inválido - tipo incorrecto
        valid, msg = QueryValidator.validate_difficulty("50")
        assert not valid


# ============================================================================
# TESTS PARA CIRCUIT_BREAKER
# ============================================================================

class TestCircuitBreaker:
    """Tests para circuit breaker"""
    
    def test_circuit_breaker_closed_state(self):
        """Test estado CLOSED inicial"""
        from src.utils.circuit_breaker import CircuitBreaker, CircuitState
        
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test apertura tras múltiples fallos"""
        from src.utils.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState
        )
        
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(name="test", config=config)
        
        @breaker
        def failing_function():
            raise Exception("Fail")
        
        # Provocar fallos
        for _ in range(3):
            try:
                failing_function()
            except:
                pass
        
        # Circuito debe abrirse
        assert breaker.state == CircuitState.OPEN
    
    def test_circuit_breaker_success_resets(self):
        """Test que éxitos resetean contador"""
        from src.utils.circuit_breaker import CircuitBreaker
        
        breaker = CircuitBreaker(name="test")
        
        success_count = 0
        
        @breaker
        def sometimes_failing():
            nonlocal success_count
            success_count += 1
            if success_count % 2 == 0:
                return "success"
            raise Exception("Fail")
        
        # Alternar éxito/fallo
        for _ in range(10):
            try:
                sometimes_failing()
            except:
                pass
        
        # No debe haber abierto porque hay éxitos intercalados
        assert breaker.stats.total_successes > 0


# ============================================================================
# TESTS PARA CONFIG_MANAGER
# ============================================================================

class TestConfigManager:
    """Tests para gestor de configuración"""
    
    def test_config_manager_singleton(self):
        """Test patrón Singleton"""
        from src.config.config_manager_v2 import ConfigManager
        
        instance1 = ConfigManager.get_instance()
        instance2 = ConfigManager.get_instance()
        
        assert instance1 is instance2
    
    def test_gpu_config_validation(self):
        """Test validación de configuración GPU"""
        from src.config.config_manager_v2 import GPUConfig
        
        # Válido
        config = GPUConfig(gpu_memory_utilization=0.8)
        assert config.gpu_memory_utilization == 0.8
        
        # Inválido - fuera de rango
        with pytest.raises(ValueError):
            GPUConfig(gpu_memory_utilization=1.5)
    
    def test_inference_config_validation(self):
        """Test validación de configuración de inferencia"""
        from src.config.config_manager_v2 import InferenceConfig
        
        # Válido
        config = InferenceConfig(default_temperature=0.7)
        assert config.default_temperature == 0.7
        
        # Inválido
        with pytest.raises(ValueError):
            InferenceConfig(default_temperature=3.0)
    
    def test_config_to_dict(self):
        """Test exportación a diccionario"""
        from src.config.config_manager_v2 import ConfigManager
        
        config = ConfigManager.get_instance()
        config_dict = config.to_dict()
        
        assert 'gpu' in config_dict
        assert 'inference' in config_dict
        assert 'rag' in config_dict


# ============================================================================
# TESTS PARA STORAGE_MANAGER
# ============================================================================

class TestStorageManager:
    """Tests para gestor de almacenamiento"""
    
    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Fixture para storage temporal"""
        from src.modules.storage_manager import StorageManager
        
        history_path = tmp_path / "history.json"
        context_path = tmp_path / "context.json"
        
        return StorageManager(
            history_path=str(history_path),
            context_path=str(context_path)
        )
    
    def test_add_interaction(self, temp_storage):
        """Test añadir interacción"""
        interaction = {
            "query": "test query",
            "response": "test response",
            "model": "test_model"
        }
        
        temp_storage.add_interaction(interaction)
        
        # Verificar que se guardó
        history = temp_storage.get_recent_history(limit=10)
        assert len(history) >= 1
        assert history[-1]["query"] == "test query"
    
    def test_get_recent_history_limit(self, temp_storage):
        """Test límite de historial reciente"""
        # Añadir múltiples interacciones
        for i in range(10):
            temp_storage.add_interaction({
                "query": f"query_{i}",
                "response": f"response_{i}",
                "model": "test"
            })
        
        # Obtener solo 3 más recientes
        recent = temp_storage.get_recent_history(limit=3)
        assert len(recent) == 3


# ============================================================================
# TESTS PARA GPU_CONTEXT_MANAGERS
# ============================================================================

class TestGPUContextManagers:
    """Tests para context managers GPU"""
    
    @pytest.mark.skipif(not os.getenv("CUDA_VISIBLE_DEVICES"), 
                       reason="GPU no disponible")
    def test_gpu_context_manager(self):
        """Test context manager GPU"""
        from src.utils.gpu_context_managers import GPUContextManager
        
        with GPUContextManager(device_id=0) as gpu:
            assert gpu is not None
    
    def test_gpu_pool_acquire(self):
        """Test adquisición de GPU del pool"""
        from src.utils.gpu_context_managers import GPUPool
        
        pool = GPUPool([0, 1])
        
        with pool.acquire() as gpu_id:
            assert gpu_id in [0, 1]
    
    def test_gpu_pool_stats(self):
        """Test estadísticas del pool"""
        from src.utils.gpu_context_managers import GPUPool
        
        pool = GPUPool([0, 1])
        stats = pool.get_stats()
        
        assert stats['total_gpus'] == 2
        assert 'usage' in stats
        assert 'available' in stats


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================

class TestIntegration:
    """Tests de integración entre componentes"""
    
    def test_config_and_validator(self):
        """Test integración config manager y validator"""
        from src.config.config_manager_v2 import ConfigManager
        from src.utils.validators import InputValidator
        
        config = ConfigManager.get_instance()
        validator = InputValidator(
            max_length=config.security.max_query_length,
            blocked_terms=config.security.blocked_terms
        )
        
        result = validator.validate("test query")
        assert result.is_valid
    
    def test_error_handling_with_circuit_breaker(self):
        """Test manejo de errores con circuit breaker"""
        from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError
        from src.utils.error_handler import handle_errors
        
        breaker = CircuitBreaker(name="integration_test")
        
        @handle_errors(default_value="fallback")
        @breaker
        def api_call():
            raise Exception("API fail")
        
        # Debe retornar fallback
        result = api_call()
        assert result == "fallback"


# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
