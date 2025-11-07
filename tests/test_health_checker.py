"""
Test Suite - Health Checker
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.utils.health_checker import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    check_gpu_temperature,
    check_disk_space,
    check_memory_usage
)


class TestHealthStatus:
    """Test health status enum"""
    
    def test_status_values(self):
        """Test all status values exist"""
        assert HealthStatus.HEALTHY
        assert HealthStatus.DEGRADED
        assert HealthStatus.UNHEALTHY
        assert HealthStatus.UNKNOWN
    
    def test_status_ordering(self):
        """Test status can be compared"""
        assert HealthStatus.HEALTHY.value < HealthStatus.DEGRADED.value
        assert HealthStatus.DEGRADED.value < HealthStatus.UNHEALTHY.value


class TestComponentHealth:
    """Test component health data structure"""
    
    def test_initialization(self):
        """Test component health initialization"""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="All good"
        )
        
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "All good"
        assert health.details == {}
    
    def test_with_details(self):
        """Test component health with details"""
        details = {"cpu_usage": 45.2, "memory_mb": 1024}
        health = ComponentHealth(
            name="system",
            status=HealthStatus.DEGRADED,
            message="High load",
            details=details
        )
        
        assert health.details["cpu_usage"] == 45.2
        assert health.details["memory_mb"] == 1024


class TestHealthCheckerBasics:
    """Test basic health checker functionality"""
    
    def test_initialization(self):
        """Test health checker initialization"""
        checker = HealthChecker()
        
        assert checker is not None
        assert len(checker.get_all_health()) == 0
    
    def test_register_component(self):
        """Test registering a component"""
        checker = HealthChecker()
        
        def mock_check():
            return ComponentHealth("test", HealthStatus.HEALTHY, "OK")
        
        checker.register_component("test", mock_check)
        
        health = checker.check_component("test")
        assert health.status == HealthStatus.HEALTHY
    
    def test_unregister_component(self):
        """Test unregistering a component"""
        checker = HealthChecker()
        
        def mock_check():
            return ComponentHealth("test", HealthStatus.HEALTHY, "OK")
        
        checker.register_component("test", mock_check)
        assert "test" in checker.get_registered_components()
        
        checker.unregister_component("test")
        assert "test" not in checker.get_registered_components()
    
    def test_check_nonexistent_component(self):
        """Test checking nonexistent component"""
        checker = HealthChecker()
        
        health = checker.check_component("nonexistent")
        
        assert health.status == HealthStatus.UNKNOWN
        assert "not registered" in health.message.lower()


class TestHealthCheckerChecks:
    """Test built-in health checks"""
    
    @patch('src.utils.health_checker.pynvml')
    def test_gpu_temperature_check_healthy(self, mock_nvml):
        """Test GPU temperature check - healthy"""
        mock_nvml.nvmlDeviceGetTemperature.return_value = 60
        mock_nvml.nvmlDeviceGetName.return_value = b"GPU 0"
        
        health = check_gpu_temperature(gpu_id=0, max_temp=80)
        
        assert health.status == HealthStatus.HEALTHY
        assert health.details["temperature"] == 60
    
    @patch('src.utils.health_checker.pynvml')
    def test_gpu_temperature_check_degraded(self, mock_nvml):
        """Test GPU temperature check - degraded"""
        mock_nvml.nvmlDeviceGetTemperature.return_value = 75
        mock_nvml.nvmlDeviceGetName.return_value = b"GPU 0"
        
        health = check_gpu_temperature(gpu_id=0, max_temp=80, warn_threshold=70)
        
        assert health.status == HealthStatus.DEGRADED
        assert health.details["temperature"] == 75
    
    @patch('src.utils.health_checker.pynvml')
    def test_gpu_temperature_check_unhealthy(self, mock_nvml):
        """Test GPU temperature check - unhealthy"""
        mock_nvml.nvmlDeviceGetTemperature.return_value = 85
        mock_nvml.nvmlDeviceGetName.return_value = b"GPU 0"
        
        health = check_gpu_temperature(gpu_id=0, max_temp=80)
        
        assert health.status == HealthStatus.UNHEALTHY
        assert health.details["temperature"] == 85
    
    @patch('src.utils.health_checker.shutil')
    def test_disk_space_check_healthy(self, mock_shutil):
        """Test disk space check - healthy"""
        mock_usage = Mock()
        mock_usage.total = 100 * 1024**3  # 100 GB
        mock_usage.used = 30 * 1024**3    # 30 GB
        mock_usage.free = 70 * 1024**3    # 70 GB
        mock_usage.percent = 30.0
        mock_shutil.disk_usage.return_value = mock_usage
        
        health = check_disk_space(path="/", min_free_gb=10)
        
        assert health.status == HealthStatus.HEALTHY
        assert health.details["free_gb"] > 60
    
    @patch('src.utils.health_checker.shutil')
    def test_disk_space_check_degraded(self, mock_shutil):
        """Test disk space check - degraded"""
        mock_usage = Mock()
        mock_usage.total = 100 * 1024**3
        mock_usage.used = 85 * 1024**3
        mock_usage.free = 15 * 1024**3
        mock_usage.percent = 85.0
        mock_shutil.disk_usage.return_value = mock_usage
        
        health = check_disk_space(path="/", min_free_gb=10, warn_threshold_gb=20)
        
        assert health.status == HealthStatus.DEGRADED
    
    @patch('src.utils.health_checker.psutil')
    def test_memory_usage_check_healthy(self, mock_psutil):
        """Test memory usage check - healthy"""
        mock_vm = Mock()
        mock_vm.total = 16 * 1024**3      # 16 GB
        mock_vm.available = 10 * 1024**3  # 10 GB
        mock_vm.percent = 37.5
        mock_psutil.virtual_memory.return_value = mock_vm
        
        health = check_memory_usage(max_percent=80)
        
        assert health.status == HealthStatus.HEALTHY
        assert health.details["percent_used"] < 40
    
    @patch('src.utils.health_checker.psutil')
    def test_memory_usage_check_unhealthy(self, mock_psutil):
        """Test memory usage check - unhealthy"""
        mock_vm = Mock()
        mock_vm.total = 16 * 1024**3
        mock_vm.available = 1 * 1024**3
        mock_vm.percent = 93.75
        mock_psutil.virtual_memory.return_value = mock_vm
        
        health = check_memory_usage(max_percent=80)
        
        assert health.status == HealthStatus.UNHEALTHY


class TestHealthCheckerAggregation:
    """Test health aggregation"""
    
    def test_get_all_health(self):
        """Test getting all component health"""
        checker = HealthChecker()
        
        def check1():
            return ComponentHealth("comp1", HealthStatus.HEALTHY, "OK")
        
        def check2():
            return ComponentHealth("comp2", HealthStatus.DEGRADED, "Warning")
        
        checker.register_component("comp1", check1)
        checker.register_component("comp2", check2)
        
        all_health = checker.get_all_health()
        
        assert len(all_health) == 2
        assert "comp1" in all_health
        assert "comp2" in all_health
        assert all_health["comp1"].status == HealthStatus.HEALTHY
        assert all_health["comp2"].status == HealthStatus.DEGRADED
    
    def test_overall_health_all_healthy(self):
        """Test overall health when all components healthy"""
        checker = HealthChecker()
        
        def check1():
            return ComponentHealth("comp1", HealthStatus.HEALTHY, "OK")
        
        def check2():
            return ComponentHealth("comp2", HealthStatus.HEALTHY, "OK")
        
        checker.register_component("comp1", check1)
        checker.register_component("comp2", check2)
        
        overall = checker.get_overall_health()
        
        assert overall == HealthStatus.HEALTHY
    
    def test_overall_health_one_degraded(self):
        """Test overall health with one degraded component"""
        checker = HealthChecker()
        
        def check1():
            return ComponentHealth("comp1", HealthStatus.HEALTHY, "OK")
        
        def check2():
            return ComponentHealth("comp2", HealthStatus.DEGRADED, "Warning")
        
        checker.register_component("comp1", check1)
        checker.register_component("comp2", check2)
        
        overall = checker.get_overall_health()
        
        assert overall == HealthStatus.DEGRADED
    
    def test_overall_health_one_unhealthy(self):
        """Test overall health with one unhealthy component"""
        checker = HealthChecker()
        
        def check1():
            return ComponentHealth("comp1", HealthStatus.HEALTHY, "OK")
        
        def check2():
            return ComponentHealth("comp2", HealthStatus.UNHEALTHY, "Error")
        
        checker.register_component("comp1", check1)
        checker.register_component("comp2", check2)
        
        overall = checker.get_overall_health()
        
        assert overall == HealthStatus.UNHEALTHY


class TestHealthCheckerCaching:
    """Test health check caching"""
    
    def test_cache_duration(self):
        """Test health checks are cached"""
        import time
        
        checker = HealthChecker(cache_ttl=1)
        call_count = 0
        
        def expensive_check():
            nonlocal call_count
            call_count += 1
            return ComponentHealth("test", HealthStatus.HEALTHY, "OK")
        
        checker.register_component("test", expensive_check)
        
        # First call
        checker.check_component("test")
        assert call_count == 1
        
        # Second call (should use cache)
        checker.check_component("test")
        assert call_count == 1
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Third call (cache expired, should call again)
        checker.check_component("test")
        assert call_count == 2
    
    def test_force_refresh(self):
        """Test forcing refresh bypasses cache"""
        checker = HealthChecker(cache_ttl=60)
        call_count = 0
        
        def check():
            nonlocal call_count
            call_count += 1
            return ComponentHealth("test", HealthStatus.HEALTHY, "OK")
        
        checker.register_component("test", check)
        
        # First call
        checker.check_component("test")
        assert call_count == 1
        
        # Force refresh
        checker.check_component("test", force_refresh=True)
        assert call_count == 2


class TestHealthCheckerErrorHandling:
    """Test error handling"""
    
    def test_check_function_raises_exception(self):
        """Test when check function raises exception"""
        checker = HealthChecker()
        
        def failing_check():
            raise ValueError("Check failed")
        
        checker.register_component("failing", failing_check)
        
        health = checker.check_component("failing")
        
        assert health.status == HealthStatus.UNKNOWN
        assert "error" in health.message.lower()
    
    def test_register_non_callable(self):
        """Test registering non-callable"""
        checker = HealthChecker()
        
        with pytest.raises(TypeError):
            checker.register_component("invalid", "not a function")
    
    def test_duplicate_registration(self):
        """Test registering same component twice"""
        checker = HealthChecker()
        
        def check1():
            return ComponentHealth("test", HealthStatus.HEALTHY, "v1")
        
        def check2():
            return ComponentHealth("test", HealthStatus.HEALTHY, "v2")
        
        checker.register_component("test", check1)
        checker.register_component("test", check2)  # Should override
        
        health = checker.check_component("test")
        assert health.message == "v2"
