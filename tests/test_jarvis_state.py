"""
Test Suite - JarvisState Thread-Safety
"""

import pytest
import threading
import time
from src.utils.jarvis_state import JarvisState


class TestJarvisStateThreadSafety:
    """Test thread-safety of JarvisState"""
    
    def test_concurrent_error_increment(self):
        """Test that concurrent error increments are atomic"""
        state = JarvisState(max_errors=100)
        num_threads = 10
        increments_per_thread = 10
        
        def increment_errors():
            for _ in range(increments_per_thread):
                state.increment_errors()
        
        threads = [threading.Thread(target=increment_errors) for _ in range(num_threads)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should be exactly num_threads * increments_per_thread
        assert state.get_error_count() == num_threads * increments_per_thread
    
    def test_concurrent_state_changes(self):
        """Test concurrent state modifications"""
        state = JarvisState()
        
        def toggle_voice():
            for _ in range(100):
                state.set_voice_active(True)
                time.sleep(0.001)
                state.set_voice_active(False)
        
        threads = [threading.Thread(target=toggle_voice) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without crashes
        assert state.to_dict() is not None
    
    def test_error_budget_exceeded(self):
        """Test max errors exceeded check"""
        state = JarvisState(max_errors=5)
        
        for i in range(4):
            result = state.increment_errors()
            assert not result  # Not exceeded yet
        
        result = state.increment_errors()
        assert result  # Now exceeded
    
    def test_reset_errors(self):
        """Test error reset"""
        state = JarvisState()
        state.increment_errors()
        state.increment_errors()
        state.reset_errors()
        
        assert state.get_error_count() == 0


class TestJarvisStateBasics:
    """Test basic JarvisState functionality"""
    
    def test_initialization(self):
        """Test default initialization"""
        state = JarvisState()
        
        assert state.running == True
        assert state.voice_active == False
        assert state.error_count == 0
        assert state.max_errors == 5
    
    def test_custom_initialization(self):
        """Test custom initialization"""
        state = JarvisState(
            running=False,
            voice_active=True,
            max_errors=10
        )
        
        assert state.running == False
        assert state.voice_active == True
        assert state.max_errors == 10
    
    def test_to_dict(self):
        """Test state serialization"""
        state = JarvisState(v2_mode=True)
        d = state.to_dict()
        
        assert isinstance(d, dict)
        assert 'running' in d
        assert 'voice_active' in d
        assert d['v2_mode'] == True
