"""
Unit Tests for Core Components
Basic unit tests for validators, config manager, and utilities
"""

import pytest
import os
import json
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.utils.validators import InputValidator, ValidationResult
from src.utils.error_handler import (
    JarvisError, ValidationError, ModelError, ConfigError
)


class TestInputValidator:
    """Tests for InputValidator"""
    
    def test_valid_query(self):
        """Test validation of a valid query"""
        validator = InputValidator()
        result = validator.validate_query("Hello, how are you?")
        
        assert result.is_valid is True
        assert result.cleaned_value is not None
        assert result.error_message is None
    
    def test_empty_query(self):
        """Test validation of empty query"""
        validator = InputValidator(min_length=1)
        result = validator.validate_query("")
        
        assert result.is_valid is False
        assert "too short" in result.error_message.lower()
    
    def test_long_query(self):
        """Test validation of excessively long query"""
        validator = InputValidator(max_length=100)
        long_query = "a" * 200
        result = validator.validate_query(long_query)
        
        assert result.is_valid is False
        assert "too long" in result.error_message.lower()
    
    def test_sql_injection(self):
        """Test detection of SQL injection patterns"""
        validator = InputValidator()
        malicious_query = "SELECT * FROM users; DROP TABLE users;"
        result = validator.validate_query(malicious_query)
        
        assert result.is_valid is False
        assert "sql injection" in result.error_message.lower()
    
    def test_command_injection(self):
        """Test detection of command injection patterns"""
        validator = InputValidator()
        malicious_query = "test && rm -rf /"
        result = validator.validate_query(malicious_query)
        
        assert result.is_valid is False
        assert "command injection" in result.error_message.lower()
    
    def test_xss_sanitization(self):
        """Test XSS pattern sanitization"""
        validator = InputValidator()
        xss_query = "<script>alert('xss')</script>"
        result = validator.validate_query(xss_query)
        
        # Should be sanitized but valid
        assert result.is_valid is True
        assert "<script>" not in result.cleaned_value
    
    def test_null_bytes(self):
        """Test detection of null bytes"""
        validator = InputValidator()
        result = validator.validate_query("test\x00query")
        
        assert result.is_valid is False
        assert "null byte" in result.error_message.lower()
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        validator = InputValidator()
        result = validator.validate_query("test   multiple    spaces")
        
        assert result.is_valid is True
        # Should normalize multiple spaces to single space
        assert "  " not in result.cleaned_value
    
    def test_valid_file_path(self):
        """Test validation of valid file path"""
        validator = InputValidator()
        result = validator.validate_file_path("models/llm/model.bin")
        
        assert result.is_valid is True
    
    def test_path_traversal(self):
        """Test detection of path traversal"""
        validator = InputValidator()
        result = validator.validate_file_path("../../../etc/passwd")
        
        assert result.is_valid is False
        assert "traversal" in result.error_message.lower()
    
    def test_valid_api_key(self):
        """Test validation of valid API key"""
        validator = InputValidator()
        result = validator.validate_api_key("sk-1234567890abcdef")
        
        assert result.is_valid is True
    
    def test_short_api_key(self):
        """Test detection of too short API key"""
        validator = InputValidator()
        result = validator.validate_api_key("short")
        
        assert result.is_valid is False
        assert "too short" in result.error_message.lower()
    
    def test_invalid_api_key_chars(self):
        """Test detection of invalid characters in API key"""
        validator = InputValidator()
        result = validator.validate_api_key("invalid@key#here!")
        
        assert result.is_valid is False
        assert "invalid character" in result.error_message.lower()


class TestCustomExceptions:
    """Tests for custom exceptions"""
    
    def test_jarvis_error_base(self):
        """Test base JarvisError"""
        error = JarvisError("Test error", details={"code": 123})
        
        assert error.message == "Test error"
        assert error.details == {"code": 123}
        assert str(error) == "Test error"
    
    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Invalid input")
        
        assert isinstance(error, JarvisError)
        assert error.message == "Invalid input"
    
    def test_model_error(self):
        """Test ModelError"""
        error = ModelError("Model failed", details={"model": "gpt-4"})
        
        assert isinstance(error, JarvisError)
        assert error.details["model"] == "gpt-4"


class TestErrorHandler:
    """Tests for error handling utilities"""
    
    def test_handle_errors_decorator(self):
        """Test error handling decorator"""
        from src.utils.error_handler import handle_errors
        
        @handle_errors(error_type=ValueError, default_value="error")
        def risky_function():
            raise ValueError("Something went wrong")
        
        result = risky_function()
        assert result == "error"
    
    def test_handle_errors_success(self):
        """Test error handling with successful execution"""
        from src.utils.error_handler import handle_errors
        
        @handle_errors(error_type=ValueError, default_value="error")
        def safe_function():
            return "success"
        
        result = safe_function()
        assert result == "success"


class TestConfigManager:
    """Tests for ConfigManager"""
    
    def test_singleton_pattern(self):
        """Test that ConfigManager follows singleton pattern"""
        from src.config.config_manager import ConfigManager
        
        instance1 = ConfigManager.get_instance()
        instance2 = ConfigManager.get_instance()
        
        assert instance1 is instance2
    
    def test_get_path(self):
        """Test path resolution"""
        from src.config.config_manager import ConfigManager
        
        config = ConfigManager.get_instance()
        path = config.get_path("models/test.bin")
        
        assert isinstance(path, Path)
        assert path.is_absolute()


class TestCircuitBreaker:
    """Tests for Circuit Breaker"""
    
    def test_circuit_closed_initially(self):
        """Test that circuit starts in CLOSED state"""
        from src.utils.circuit_breaker import CircuitBreaker, CircuitState
        
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED
    
    def test_circuit_opens_after_failures(self):
        """Test that circuit opens after threshold failures"""
        from src.utils.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState
        )
        
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)
        
        # Simulate 3 failures
        for _ in range(3):
            try:
                breaker.call(lambda: 1/0)  # Will raise ZeroDivisionError
            except:
                pass
        
        assert breaker.state == CircuitState.OPEN
    
    def test_circuit_stats(self):
        """Test circuit breaker statistics"""
        from src.utils.circuit_breaker import CircuitBreaker
        
        breaker = CircuitBreaker("test")
        
        # Successful call
        breaker.call(lambda: "success")
        
        stats = breaker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 0


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
