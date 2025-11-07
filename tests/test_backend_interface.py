"""
Test Suite - Backend Interface
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.modules.backend_interface import (
    ModelBackendInterface,
    V1BackendAdapter,
    V2BackendAdapter,
    BackendFactory,
    BackendType
)


class TestV1BackendAdapter:
    """Test V1 backend adapter"""
    
    @patch('src.modules.backend_interface.ModelManager')
    def test_initialization(self, mock_manager):
        """Test V1 adapter initialization"""
        adapter = V1BackendAdapter()
        
        assert adapter.backend_type == BackendType.V1
        assert adapter.backend is not None
    
    @patch('src.modules.backend_interface.ModelManager')
    def test_generate_text(self, mock_manager):
        """Test text generation"""
        mock_instance = Mock()
        mock_instance.generate_response.return_value = "Generated response"
        mock_manager.return_value = mock_instance
        
        adapter = V1BackendAdapter()
        result = adapter.generate_text("Test prompt", max_tokens=100)
        
        assert result == "Generated response"
        mock_instance.generate_response.assert_called_once()
    
    @patch('src.modules.backend_interface.ModelManager')
    def test_get_available_models(self, mock_manager):
        """Test getting available models"""
        mock_instance = Mock()
        mock_instance.get_available_models.return_value = ["model1", "model2"]
        mock_manager.return_value = mock_instance
        
        adapter = V1BackendAdapter()
        models = adapter.get_available_models()
        
        assert "model1" in models
        assert "model2" in models
    
    @patch('src.modules.backend_interface.ModelManager')
    def test_cleanup(self, mock_manager):
        """Test cleanup"""
        mock_instance = Mock()
        mock_manager.return_value = mock_instance
        
        adapter = V1BackendAdapter()
        adapter.cleanup()
        
        mock_instance.cleanup.assert_called_once()


class TestV2BackendAdapter:
    """Test V2 backend adapter"""
    
    @patch('src.modules.backend_interface.ModelOrchestrator')
    def test_initialization(self, mock_orchestrator):
        """Test V2 adapter initialization"""
        adapter = V2BackendAdapter()
        
        assert adapter.backend_type == BackendType.V2
        assert adapter.backend is not None
    
    @patch('src.modules.backend_interface.ModelOrchestrator')
    def test_generate_text(self, mock_orchestrator):
        """Test text generation"""
        mock_instance = Mock()
        mock_instance.generate_response.return_value = "V2 generated response"
        mock_orchestrator.return_value = mock_instance
        
        adapter = V2BackendAdapter()
        result = adapter.generate_text("Test prompt", max_tokens=100)
        
        assert result == "V2 generated response"
        mock_instance.generate_response.assert_called_once()
    
    @patch('src.modules.backend_interface.ModelOrchestrator')
    def test_get_available_models(self, mock_orchestrator):
        """Test getting available models"""
        mock_instance = Mock()
        mock_instance.get_available_models.return_value = ["model_v2_1", "model_v2_2"]
        mock_orchestrator.return_value = mock_instance
        
        adapter = V2BackendAdapter()
        models = adapter.get_available_models()
        
        assert "model_v2_1" in models
        assert "model_v2_2" in models
    
    @patch('src.modules.backend_interface.ModelOrchestrator')
    def test_is_healthy(self, mock_orchestrator):
        """Test health check"""
        mock_instance = Mock()
        mock_instance.is_healthy.return_value = True
        mock_orchestrator.return_value = mock_instance
        
        adapter = V2BackendAdapter()
        health = adapter.is_healthy()
        
        assert health == True


class TestBackendFactory:
    """Test backend factory"""
    
    @patch('src.modules.backend_interface.V2BackendAdapter')
    def test_create_auto_v2_success(self, mock_v2):
        """Test auto creation with V2 success"""
        mock_v2_instance = Mock()
        mock_v2_instance.is_healthy.return_value = True
        mock_v2.return_value = mock_v2_instance
        
        backend = BackendFactory.create(backend_type=BackendType.AUTO)
        
        assert backend.backend_type == BackendType.V2
    
    @patch('src.modules.backend_interface.V2BackendAdapter')
    @patch('src.modules.backend_interface.V1BackendAdapter')
    def test_create_auto_v2_fails_fallback_v1(self, mock_v1, mock_v2):
        """Test auto creation with V2 failure, fallback to V1"""
        # V2 fails
        mock_v2.side_effect = Exception("V2 initialization failed")
        
        # V1 succeeds
        mock_v1_instance = Mock()
        mock_v1.return_value = mock_v1_instance
        
        backend = BackendFactory.create(backend_type=BackendType.AUTO)
        
        assert backend.backend_type == BackendType.V1
    
    @patch('src.modules.backend_interface.V1BackendAdapter')
    def test_create_explicit_v1(self, mock_v1):
        """Test explicit V1 creation"""
        mock_v1_instance = Mock()
        mock_v1.return_value = mock_v1_instance
        
        backend = BackendFactory.create(backend_type=BackendType.V1)
        
        assert backend.backend_type == BackendType.V1
        mock_v1.assert_called_once()
    
    @patch('src.modules.backend_interface.V2BackendAdapter')
    def test_create_explicit_v2(self, mock_v2):
        """Test explicit V2 creation"""
        mock_v2_instance = Mock()
        mock_v2.return_value = mock_v2_instance
        
        backend = BackendFactory.create(backend_type=BackendType.V2)
        
        assert backend.backend_type == BackendType.V2
        mock_v2.assert_called_once()


class TestBackendInterfaceContract:
    """Test that all backends implement the interface contract"""
    
    @patch('src.modules.backend_interface.ModelManager')
    def test_v1_implements_interface(self, mock_manager):
        """Test V1 adapter implements all interface methods"""
        adapter = V1BackendAdapter()
        
        # Check all required methods exist
        assert hasattr(adapter, 'generate_text')
        assert hasattr(adapter, 'get_available_models')
        assert hasattr(adapter, 'is_healthy')
        assert hasattr(adapter, 'get_model_info')
        assert hasattr(adapter, 'cleanup')
        
        # Check callable
        assert callable(adapter.generate_text)
        assert callable(adapter.get_available_models)
    
    @patch('src.modules.backend_interface.ModelOrchestrator')
    def test_v2_implements_interface(self, mock_orchestrator):
        """Test V2 adapter implements all interface methods"""
        adapter = V2BackendAdapter()
        
        # Check all required methods exist
        assert hasattr(adapter, 'generate_text')
        assert hasattr(adapter, 'get_available_models')
        assert hasattr(adapter, 'is_healthy')
        assert hasattr(adapter, 'get_model_info')
        assert hasattr(adapter, 'cleanup')
        
        # Check callable
        assert callable(adapter.generate_text)
        assert callable(adapter.get_available_models)


class TestBackendSwitching:
    """Test backend switching scenarios"""
    
    @patch('src.modules.backend_interface.V1BackendAdapter')
    @patch('src.modules.backend_interface.V2BackendAdapter')
    def test_fallback_on_v2_failure(self, mock_v2, mock_v1):
        """Test fallback to V1 when V2 fails during operation"""
        # V2 initialization succeeds
        mock_v2_instance = Mock()
        mock_v2_instance.is_healthy.return_value = True
        mock_v2_instance.generate_text.side_effect = Exception("V2 runtime error")
        mock_v2.return_value = mock_v2_instance
        
        # V1 works
        mock_v1_instance = Mock()
        mock_v1_instance.generate_text.return_value = "V1 response"
        mock_v1.return_value = mock_v1_instance
        
        # Create V2 backend
        backend_v2 = BackendFactory.create(backend_type=BackendType.V2)
        
        # V2 fails
        with pytest.raises(Exception):
            backend_v2.generate_text("test")
        
        # Fallback to V1
        backend_v1 = BackendFactory.create(backend_type=BackendType.V1)
        result = backend_v1.generate_text("test")
        
        assert result == "V1 response"


class TestBackendEdgeCases:
    """Test edge cases"""
    
    @patch('src.modules.backend_interface.V1BackendAdapter')
    @patch('src.modules.backend_interface.V2BackendAdapter')
    def test_both_backends_fail(self, mock_v2, mock_v1):
        """Test when both backends fail"""
        mock_v2.side_effect = Exception("V2 failed")
        mock_v1.side_effect = Exception("V1 failed")
        
        with pytest.raises(Exception):
            BackendFactory.create(backend_type=BackendType.AUTO)
    
    @patch('src.modules.backend_interface.ModelManager')
    def test_empty_prompt(self, mock_manager):
        """Test handling empty prompt"""
        mock_instance = Mock()
        mock_manager.return_value = mock_instance
        
        adapter = V1BackendAdapter()
        
        # Should handle gracefully or raise appropriate error
        try:
            adapter.generate_text("")
        except (ValueError, AssertionError):
            pass  # Expected
    
    @patch('src.modules.backend_interface.ModelOrchestrator')
    def test_get_model_info_nonexistent(self, mock_orchestrator):
        """Test getting info for nonexistent model"""
        mock_instance = Mock()
        mock_instance.get_model_info.return_value = None
        mock_orchestrator.return_value = mock_instance
        
        adapter = V2BackendAdapter()
        info = adapter.get_model_info("nonexistent_model")
        
        # Should return None or empty dict
        assert info is None or info == {}
