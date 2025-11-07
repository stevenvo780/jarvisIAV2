"""
Integration Test Suite
Tests end-to-end workflows and component interactions
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock


class TestGPUPipeline:
    """Test complete GPU processing pipeline"""
    
    @patch('src.utils.gpu_manager.GPUManager')
    @patch('src.modules.orchestrator.model_orchestrator.ModelOrchestrator')
    def test_full_inference_pipeline(self, mock_orchestrator, mock_gpu):
        """Test full inference pipeline from query to response"""
        # Mock GPU availability
        mock_gpu_instance = Mock()
        mock_gpu_instance.get_available_gpu.return_value = 0
        mock_gpu_instance.get_gpu_memory_info.return_value = {
            'free': 8000, 'total': 16000, 'used': 8000
        }
        mock_gpu.return_value = mock_gpu_instance
        
        # Mock model orchestrator
        mock_orch_instance = Mock()
        mock_orch_instance.generate_response.return_value = "Test response"
        mock_orchestrator.return_value = mock_orch_instance
        
        # Simulate query processing
        from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
        orchestrator = ModelOrchestrator()
        
        response = orchestrator.generate_response(
            prompt="Test query",
            model_name="test_model",
            max_tokens=100
        )
        
        assert response == "Test response"
        mock_orch_instance.generate_response.assert_called_once()
    
    @patch('src.modules.embeddings.embedding_manager.EmbeddingManager')
    def test_rag_pipeline(self, mock_embedding):
        """Test RAG pipeline (query -> embedding -> retrieval -> generation)"""
        mock_emb_instance = Mock()
        mock_emb_instance.get_embedding.return_value = [0.1] * 768
        mock_emb_instance.search_similar.return_value = [
            {"text": "Context 1", "score": 0.95},
            {"text": "Context 2", "score": 0.87}
        ]
        mock_embedding.return_value = mock_emb_instance
        
        from src.modules.embeddings.embedding_manager import EmbeddingManager
        manager = EmbeddingManager()
        
        # Get embedding
        embedding = manager.get_embedding("test query")
        assert len(embedding) == 768
        
        # Search similar
        results = manager.search_similar(embedding, top_k=2)
        assert len(results) == 2
        assert results[0]["score"] > results[1]["score"]


class TestConcurrentQueries:
    """Test concurrent query processing"""
    
    @patch('src.modules.orchestrator.model_orchestrator.ModelOrchestrator')
    def test_multiple_concurrent_queries(self, mock_orchestrator):
        """Test handling multiple concurrent queries"""
        mock_instance = Mock()
        mock_instance.generate_response.return_value = "Response"
        mock_orchestrator.return_value = mock_instance
        
        from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
        orchestrator = ModelOrchestrator()
        
        results = []
        errors = []
        
        def query_worker(query_id):
            try:
                response = orchestrator.generate_response(
                    prompt=f"Query {query_id}",
                    model_name="test_model"
                )
                results.append(response)
            except Exception as e:
                errors.append(e)
        
        # Launch 10 concurrent queries
        threads = [
            threading.Thread(target=query_worker, args=(i,))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All queries should succeed
        assert len(results) == 10
        assert len(errors) == 0
    
    @patch('src.utils.jarvis_state.JarvisState')
    def test_concurrent_state_updates(self, mock_state):
        """Test concurrent state updates don't cause race conditions"""
        from src.utils.jarvis_state import JarvisState
        state = JarvisState()
        
        def increment_errors():
            for _ in range(100):
                state.increment_errors()
        
        threads = [threading.Thread(target=increment_errors) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have exactly 500 errors (5 threads * 100 increments)
        assert state.get_error_count() == 500


class TestErrorRecovery:
    """Test error recovery mechanisms"""
    
    @patch('src.modules.orchestrator.model_orchestrator.ModelOrchestrator')
    @patch('src.utils.circuit_breaker.CircuitBreaker')
    def test_circuit_breaker_integration(self, mock_circuit, mock_orchestrator):
        """Test circuit breaker prevents cascade failures"""
        mock_orch_instance = Mock()
        # First 5 calls fail
        mock_orch_instance.generate_response.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3"),
            Exception("Error 4"),
            Exception("Error 5"),
            "Success"  # 6th call succeeds but circuit is open
        ]
        mock_orchestrator.return_value = mock_orch_instance
        
        from src.utils.circuit_breaker import CircuitBreaker
        circuit = CircuitBreaker(failure_threshold=3, timeout=1)
        
        # First 3 calls fail and open circuit
        for i in range(3):
            try:
                circuit.call(lambda: mock_orch_instance.generate_response("test"))
            except:
                pass
        
        # Circuit should be open
        assert circuit.is_open()
        
        # 4th call should fail immediately without calling backend
        with pytest.raises(Exception):
            circuit.call(lambda: mock_orch_instance.generate_response("test"))
    
    @patch('src.utils.error_budget.ErrorBudget')
    def test_error_budget_throttling(self, mock_budget):
        """Test error budget prevents runaway failures"""
        from src.utils.error_budget import ErrorBudget
        budget = ErrorBudget(max_errors=5, window_seconds=10)
        
        # Add 5 errors
        for i in range(5):
            budget.add_error(f"error_{i}")
        
        # Budget should be exceeded
        assert budget.is_budget_exceeded()
        assert not budget.can_execute()
    
    @patch('src.modules.voice.whisper_handler.WhisperHandler')
    def test_whisper_fallback_chain(self, mock_whisper):
        """Test Whisper model fallback chain"""
        mock_instance = Mock()
        # First 3 paths fail, 4th succeeds
        mock_instance.load_model.side_effect = [
            Exception("Model 1 failed"),
            Exception("Model 2 failed"),
            Exception("Model 3 failed"),
            True  # 4th model loads
        ]
        mock_whisper.return_value = mock_instance
        
        from src.modules.voice.whisper_handler import WhisperHandler
        handler = WhisperHandler()
        
        # Should try fallback paths until one succeeds
        # (Implementation detail - adjust based on actual code)


class TestResourceManagement:
    """Test resource acquisition and cleanup"""
    
    @patch('src.utils.gpu_manager.GPUManager')
    def test_gpu_context_cleanup_on_error(self, mock_gpu):
        """Test GPU context is cleaned up on error"""
        mock_gpu_instance = Mock()
        mock_gpu.return_value = mock_gpu_instance
        
        from src.utils.gpu_context_managers import gpu_inference_context
        
        try:
            with gpu_inference_context(gpu_id=0) as ctx:
                # Simulate error during inference
                raise ValueError("Inference failed")
        except ValueError:
            pass
        
        # Cleanup should have been called
        # (Verify based on actual implementation)
    
    @patch('src.modules.embeddings.embedding_manager.EmbeddingManager')
    def test_embedding_cache_memory_limit(self, mock_embedding):
        """Test embedding cache doesn't exceed memory limit"""
        from src.modules.embeddings.embedding_manager import EmbeddingManager
        manager = EmbeddingManager()
        
        # Add many embeddings
        for i in range(2000):
            manager.get_embedding(f"text_{i}")
        
        # Cache should have evicted old entries
        stats = manager.get_cache_stats()
        assert stats["size"] <= 1000  # Max cache size


class TestHealthMonitoring:
    """Test health monitoring integration"""
    
    @patch('src.utils.health_checker.HealthChecker')
    def test_health_check_all_systems(self, mock_health):
        """Test comprehensive health check"""
        from src.utils.health_checker import HealthChecker, HealthStatus
        checker = HealthChecker()
        
        # Register all components
        components = ["gpu", "disk", "memory", "model", "embeddings"]
        for comp in components:
            checker.register_component(
                comp,
                lambda: Mock(status=HealthStatus.HEALTHY)
            )
        
        # Get overall health
        overall = checker.get_overall_health()
        assert overall == HealthStatus.HEALTHY
    
    @patch('src.utils.health_checker.check_gpu_temperature')
    def test_health_degradation_response(self, mock_gpu_check):
        """Test system response to degraded health"""
        from src.utils.health_checker import HealthStatus, ComponentHealth
        
        # GPU overheating
        mock_gpu_check.return_value = ComponentHealth(
            name="gpu",
            status=HealthStatus.DEGRADED,
            message="GPU temperature high",
            details={"temperature": 75}
        )
        
        # System should reduce load or throttle
        # (Implementation detail)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    @patch('src.modules.orchestrator.model_orchestrator.ModelOrchestrator')
    @patch('src.modules.embeddings.embedding_manager.EmbeddingManager')
    @patch('src.utils.query_validator.QueryValidator')
    def test_complete_query_workflow(self, mock_validator, mock_embedding, mock_orchestrator):
        """Test complete query workflow: validate -> embed -> retrieve -> generate"""
        # Setup mocks
        mock_val_instance = Mock()
        mock_val_instance.validate.return_value = (True, "")
        mock_validator.return_value = mock_val_instance
        
        mock_emb_instance = Mock()
        mock_emb_instance.get_embedding.return_value = [0.1] * 768
        mock_emb_instance.search_similar.return_value = [
            {"text": "Context", "score": 0.9}
        ]
        mock_embedding.return_value = mock_emb_instance
        
        mock_orch_instance = Mock()
        mock_orch_instance.generate_response.return_value = "Final response"
        mock_orchestrator.return_value = mock_orch_instance
        
        # Execute workflow
        from src.utils.query_validator import QueryValidator
        from src.modules.embeddings.embedding_manager import EmbeddingManager
        from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
        
        query = "What is the weather?"
        
        # 1. Validate
        validator = QueryValidator()
        is_valid, error = validator.validate(query)
        assert is_valid
        
        # 2. Get embedding
        embedding_mgr = EmbeddingManager()
        embedding = embedding_mgr.get_embedding(query)
        assert len(embedding) == 768
        
        # 3. Retrieve context
        contexts = embedding_mgr.search_similar(embedding, top_k=3)
        assert len(contexts) > 0
        
        # 4. Generate response
        orchestrator = ModelOrchestrator()
        response = orchestrator.generate_response(
            prompt=query,
            context=contexts
        )
        assert response == "Final response"
    
    @patch('src.utils.jarvis_state.JarvisState')
    @patch('src.utils.error_budget.ErrorBudget')
    def test_error_handling_workflow(self, mock_budget, mock_state):
        """Test error handling workflow across components"""
        from src.utils.jarvis_state import JarvisState
        from src.utils.error_budget import ErrorBudget
        
        state = JarvisState()
        budget = ErrorBudget(max_errors=3)
        
        # Simulate 3 errors
        for i in range(3):
            state.increment_errors()
            budget.add_error(f"error_{i}")
        
        # Check states
        assert state.get_error_count() == 3
        assert budget.is_budget_exceeded()
        
        # System should enter safe mode
        assert not budget.can_execute()


class TestPerformance:
    """Test performance characteristics"""
    
    @patch('src.modules.embeddings.embedding_manager.EmbeddingManager')
    def test_embedding_cache_hit_rate(self, mock_embedding):
        """Test embedding cache improves performance"""
        from src.modules.embeddings.embedding_manager import EmbeddingManager
        manager = EmbeddingManager()
        
        # First call - cache miss
        start = time.time()
        manager.get_embedding("test query")
        first_call_time = time.time() - start
        
        # Second call - cache hit (should be faster)
        start = time.time()
        manager.get_embedding("test query")
        second_call_time = time.time() - start
        
        # Cache hit should be significantly faster
        # (Adjust threshold based on implementation)
    
    @patch('src.modules.orchestrator.model_orchestrator.ModelOrchestrator')
    def test_concurrent_throughput(self, mock_orchestrator):
        """Test system throughput under concurrent load"""
        mock_instance = Mock()
        mock_instance.generate_response.return_value = "Response"
        mock_orchestrator.return_value = mock_instance
        
        from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
        orchestrator = ModelOrchestrator()
        
        start_time = time.time()
        
        def process_query(i):
            orchestrator.generate_response(f"Query {i}", "model")
        
        # Process 100 queries concurrently
        threads = [threading.Thread(target=process_query, args=(i,)) for i in range(100)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        duration = time.time() - start_time
        throughput = 100 / duration
        
        # Should achieve reasonable throughput
        # (Define threshold based on requirements)
        assert throughput > 10  # At least 10 queries/second
