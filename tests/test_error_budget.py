"""
Test Suite - Error Budget System
"""

import pytest
import time
from datetime import datetime, timedelta
from src.utils.error_budget import ErrorBudget


class TestErrorBudgetBasics:
    """Test basic error budget functionality"""
    
    def test_initialization(self):
        """Test error budget initialization"""
        budget = ErrorBudget(window_seconds=60, max_errors=10)
        
        assert budget.window_seconds == 60
        assert budget.max_errors == 10
        assert budget.get_error_count() == 0
        assert not budget.is_budget_exceeded()
    
    def test_add_error(self):
        """Test adding errors"""
        budget = ErrorBudget(max_errors=5)
        
        budget.add_error("test_error")
        assert budget.get_error_count() == 1
        
        budget.add_error("test_error")
        budget.add_error("test_error")
        assert budget.get_error_count() == 3
    
    def test_budget_exceeded(self):
        """Test budget exceeded detection"""
        budget = ErrorBudget(max_errors=3)
        
        assert not budget.is_budget_exceeded()
        
        budget.add_error("error1")
        budget.add_error("error2")
        assert not budget.is_budget_exceeded()
        
        budget.add_error("error3")
        assert budget.is_budget_exceeded()
    
    def test_reset(self):
        """Test budget reset"""
        budget = ErrorBudget(max_errors=5)
        
        budget.add_error("error1")
        budget.add_error("error2")
        assert budget.get_error_count() == 2
        
        budget.reset()
        assert budget.get_error_count() == 0
        assert not budget.is_budget_exceeded()


class TestErrorBudgetTimeWindow:
    """Test time window functionality"""
    
    def test_sliding_window(self):
        """Test sliding time window"""
        budget = ErrorBudget(window_seconds=2, max_errors=5)
        
        # Add errors
        budget.add_error("error1")
        budget.add_error("error2")
        assert budget.get_error_count() == 2
        
        # Wait for window to pass
        time.sleep(2.1)
        
        # Old errors should be cleaned
        assert budget.get_error_count() == 0
    
    def test_partial_window_cleanup(self):
        """Test that only expired errors are removed"""
        budget = ErrorBudget(window_seconds=2, max_errors=10)
        
        # Add first error
        budget.add_error("error1")
        time.sleep(1)
        
        # Add second error
        budget.add_error("error2")
        time.sleep(1.1)
        
        # First error expired, second still valid
        count = budget.get_error_count()
        assert count == 1


class TestErrorBudgetCooldown:
    """Test cooldown functionality"""
    
    def test_cooldown_period(self):
        """Test cooldown after budget exceeded"""
        budget = ErrorBudget(max_errors=2, cooldown_seconds=2)
        
        # Exceed budget
        budget.add_error("error1")
        budget.add_error("error2")
        assert budget.is_budget_exceeded()
        
        # Should remain in cooldown even after reset
        budget.reset()
        assert budget.is_in_cooldown()
        
        # Wait for cooldown
        time.sleep(2.1)
        assert not budget.is_in_cooldown()
    
    def test_can_execute_during_cooldown(self):
        """Test execution blocking during cooldown"""
        budget = ErrorBudget(max_errors=1, cooldown_seconds=1)
        
        budget.add_error("error1")
        assert not budget.can_execute()
        
        time.sleep(1.1)
        assert budget.can_execute()


class TestErrorBudgetTypes:
    """Test error type tracking"""
    
    def test_error_type_tracking(self):
        """Test tracking errors by type"""
        budget = ErrorBudget(max_errors=10)
        
        budget.add_error("network_error")
        budget.add_error("network_error")
        budget.add_error("gpu_error")
        
        stats = budget.get_error_stats()
        
        assert stats["network_error"] == 2
        assert stats["gpu_error"] == 1
        assert stats.get("other_error", 0) == 0
    
    def test_multiple_error_types(self):
        """Test multiple error types don't interfere"""
        budget = ErrorBudget(max_errors=5)
        
        # Different error types
        budget.add_error("type_a")
        budget.add_error("type_b")
        budget.add_error("type_c")
        
        # Total count should be 3
        assert budget.get_error_count() == 3
        
        # Each type tracked separately
        stats = budget.get_error_stats()
        assert len(stats) == 3


class TestErrorBudgetThreadSafety:
    """Test thread safety"""
    
    def test_concurrent_error_addition(self):
        """Test concurrent error additions"""
        import threading
        
        budget = ErrorBudget(max_errors=100)
        
        def add_errors():
            for _ in range(10):
                budget.add_error("concurrent_error")
        
        threads = [threading.Thread(target=add_errors) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have exactly 100 errors
        assert budget.get_error_count() == 100
    
    def test_concurrent_reset_and_add(self):
        """Test concurrent reset and add operations"""
        import threading
        
        budget = ErrorBudget(max_errors=50)
        
        def add_errors():
            for _ in range(5):
                budget.add_error("error")
                time.sleep(0.01)
        
        def reset_budget():
            time.sleep(0.025)
            budget.reset()
        
        add_thread = threading.Thread(target=add_errors)
        reset_thread = threading.Thread(target=reset_budget)
        
        add_thread.start()
        reset_thread.start()
        
        add_thread.join()
        reset_thread.join()
        
        # Should complete without errors
        assert budget.get_error_count() >= 0


class TestErrorBudgetEdgeCases:
    """Test edge cases"""
    
    def test_zero_max_errors(self):
        """Test with zero max errors"""
        budget = ErrorBudget(max_errors=0)
        
        assert budget.is_budget_exceeded()
        budget.add_error("error")
        assert budget.is_budget_exceeded()
    
    def test_negative_window(self):
        """Test with negative window (should use absolute value or fail)"""
        # This depends on implementation - adjust test as needed
        try:
            budget = ErrorBudget(window_seconds=-10)
            # If allowed, window should be positive
            assert budget.window_seconds > 0
        except ValueError:
            # If not allowed, should raise error
            pass
    
    def test_very_large_window(self):
        """Test with very large window"""
        budget = ErrorBudget(window_seconds=86400 * 365)  # 1 year
        
        budget.add_error("error1")
        assert budget.get_error_count() == 1
        
        # Error should still be counted after short time
        time.sleep(0.1)
        assert budget.get_error_count() == 1
