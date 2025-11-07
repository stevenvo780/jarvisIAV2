"""
Circuit Breaker Pattern Implementation
Prevents cascading failures when calling external APIs
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from threading import Lock


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    success_threshold: int = 2  # Number of successes to close from half-open
    timeout: float = 60.0  # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception type to catch


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation
    
    Usage:
        breaker = CircuitBreaker(name="OpenAI_API")
        
        @breaker
        def call_api():
            return api.query()
        
        result = call_api()  # Will raise CircuitBreakerError if open
    """
    
    def __init__(self, 
                 name: str,
                 config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker
        
        Args:
            name: Name of the circuit (for logging)
            config: Configuration object
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = Lock()
        self.logger = logging.getLogger(f"CircuitBreaker.{name}")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker"""
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
        """
        with self._lock:
            self.stats.total_calls += 1
            
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN",
                        details={
                            "state": self.state.value,
                            "failures": self.stats.failure_count,
                            "last_failure": self.stats.last_failure_time
                        }
                    )
        
        # Try to call the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.config.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.stats.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.stats.last_failure_time
        return elapsed >= self.config.timeout
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = time.time()
            
            if self.stats.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.logger.info(f"Circuit '{self.name}' transitioning to CLOSED")
        self.state = CircuitState.CLOSED
        self.stats.failure_count = 0
        self.stats.success_count = 0
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.logger.warning(
            f"Circuit '{self.name}' transitioning to OPEN "
            f"(failures: {self.stats.failure_count})"
        )
        self.state = CircuitState.OPEN
        self.stats.success_count = 0
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.logger.info(f"Circuit '{self.name}' transitioning to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.stats.failure_count = 0
        self.stats.success_count = 0
    
    def reset(self):
        """Manually reset the circuit breaker"""
        with self._lock:
            self.logger.info(f"Manually resetting circuit '{self.name}'")
            self._transition_to_closed()
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_calls": self.stats.total_calls,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "success_rate": (
                self.stats.total_successes / self.stats.total_calls * 100
                if self.stats.total_calls > 0 else 0
            )
        }


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers
    
    Usage:
        manager = CircuitBreakerManager()
        openai_breaker = manager.get_breaker("openai")
        
        @openai_breaker
        def call_openai():
            ...
    """
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = Lock()
        self.logger = logging.getLogger("CircuitBreakerManager")
    
    def get_breaker(self, 
                    name: str, 
                    config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        Get or create a circuit breaker
        
        Args:
            name: Name of the circuit breaker
            config: Optional configuration
        
        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
                self.logger.info(f"Created circuit breaker: {name}")
            
            return self._breakers[name]
    
    def get_all_stats(self) -> dict:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
