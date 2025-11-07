"""
Error Budget System - Prevent cascading failures with time-windowed error tracking
"""

import time
import logging
from collections import deque
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from threading import Lock


@dataclass
class ErrorBudgetConfig:
    """Configuration for error budget"""
    max_errors: int = 5
    window_seconds: int = 60
    cooldown_seconds: int = 30


class ErrorBudget:
    """
    Time-windowed error budget tracker
    
    Prevents cascading failures by tracking errors within a sliding time window
    and enforcing cooldowns when budget is exceeded.
    
    Features:
    - Sliding window error tracking
    - Per-error-type categorization
    - Automatic cooldown periods
    - Thread-safe operations
    
    Usage:
        budget = ErrorBudget(max_errors=5, window_seconds=60)
        
        if budget.record_error("model_load"):
            # Budget exceeded - take action
            logger.error("Too many errors, initiating fallback")
            use_fallback()
        else:
            # Within budget - continue normal operation
            normal_operation()
    """
    
    def __init__(
        self,
        max_errors: int = 5,
        window_seconds: int = 60,
        cooldown_seconds: int = 30
    ):
        """
        Initialize error budget
        
        Args:
            max_errors: Maximum errors allowed in time window
            window_seconds: Time window for error tracking (seconds)
            cooldown_seconds: Cooldown period after budget exceeded
        """
        self.max_errors = max_errors
        self.window = window_seconds
        self.cooldown = cooldown_seconds
        
        # Error tracking: deque of (timestamp, error_type)
        self.errors = deque()
        
        # Cooldown tracking
        self.in_cooldown = False
        self.cooldown_until: Optional[float] = None
        
        # Statistics
        self.total_errors = 0
        self.budget_exceeded_count = 0
        self.errors_by_type: Dict[str, int] = {}
        
        # Thread safety
        self._lock = Lock()
        
        self.logger = logging.getLogger("ErrorBudget")
    
    def record_error(self, error_type: str = "general") -> bool:
        """
        Record an error and check if budget exceeded
        
        Args:
            error_type: Category of error
        
        Returns:
            True if budget exceeded, False otherwise
        """
        with self._lock:
            now = time.time()
            
            # Check if in cooldown
            if self.in_cooldown:
                if now < self.cooldown_until:
                    self.logger.warning(
                        f"In cooldown until {self.cooldown_until - now:.1f}s remaining"
                    )
                    return True
                else:
                    # Cooldown expired
                    self._end_cooldown()
            
            # Remove old errors outside window
            self._cleanup_old_errors(now)
            
            # Add new error
            self.errors.append((now, error_type))
            self.total_errors += 1
            self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
            
            # Check if budget exceeded
            if len(self.errors) >= self.max_errors:
                self._trigger_cooldown(now)
                return True
            
            self.logger.debug(
                f"Error recorded: {error_type} "
                f"({len(self.errors)}/{self.max_errors} in window)"
            )
            
            return False
    
    def _cleanup_old_errors(self, current_time: float):
        """Remove errors outside the time window"""
        cutoff = current_time - self.window
        
        while self.errors and self.errors[0][0] < cutoff:
            self.errors.popleft()
    
    def _trigger_cooldown(self, current_time: float):
        """Trigger cooldown period"""
        self.in_cooldown = True
        self.cooldown_until = current_time + self.cooldown
        self.budget_exceeded_count += 1
        
        self.logger.error(
            f"🚨 Error budget exceeded! "
            f"({self.max_errors} errors in {self.window}s) "
            f"Cooldown for {self.cooldown}s"
        )
    
    def _end_cooldown(self):
        """End cooldown period"""
        self.in_cooldown = False
        self.cooldown_until = None
        
        # Clear old errors
        self.errors.clear()
        
        self.logger.info("✅ Cooldown ended, error budget reset")
    
    def reset(self):
        """Manually reset error budget"""
        with self._lock:
            self.errors.clear()
            self.in_cooldown = False
            self.cooldown_until = None
            self.logger.info("Error budget manually reset")
    
    def get_status(self) -> Dict:
        """
        Get current error budget status
        
        Returns:
            Status dictionary with current state
        """
        with self._lock:
            now = time.time()
            self._cleanup_old_errors(now)
            
            return {
                'current_errors': len(self.errors),
                'max_errors': self.max_errors,
                'budget_remaining': self.max_errors - len(self.errors),
                'in_cooldown': self.in_cooldown,
                'cooldown_remaining': max(0, self.cooldown_until - now) if self.cooldown_until else 0,
                'total_errors_lifetime': self.total_errors,
                'budget_exceeded_count': self.budget_exceeded_count,
                'errors_by_type': dict(self.errors_by_type)
            }
    
    def is_healthy(self) -> bool:
        """
        Check if system is healthy (not in cooldown and budget not close to exceeded)
        
        Returns:
            True if healthy, False otherwise
        """
        with self._lock:
            if self.in_cooldown:
                return False
            
            # Consider unhealthy if >80% of budget used
            threshold = int(self.max_errors * 0.8)
            return len(self.errors) < threshold
    
    def get_error_rate(self) -> float:
        """
        Calculate error rate (errors per second) in current window
        
        Returns:
            Error rate as float
        """
        with self._lock:
            if len(self.errors) == 0:
                return 0.0
            
            return len(self.errors) / self.window
