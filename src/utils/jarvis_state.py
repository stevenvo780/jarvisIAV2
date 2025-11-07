"""
Thread-safe state management for Jarvis
"""

from dataclasses import dataclass, field
from threading import Lock
from typing import Optional


@dataclass
class JarvisState:
    """
    Thread-safe state container for Jarvis system
    
    All state modifications are protected by locks to prevent race conditions
    in multi-threaded environments.
    """
    running: bool = True
    voice_active: bool = False
    listening_active: bool = False
    error_count: int = 0
    max_errors: int = 5
    v2_mode: bool = False
    
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    
    def increment_errors(self) -> bool:
        """
        Thread-safe error increment
        
        Returns:
            True if max errors exceeded, False otherwise
        """
        with self._lock:
            self.error_count += 1
            return self.error_count >= self.max_errors
    
    def reset_errors(self):
        """Reset error count to zero"""
        with self._lock:
            self.error_count = 0
    
    def set_voice_active(self, active: bool):
        """Thread-safe voice active setter"""
        with self._lock:
            self.voice_active = active
    
    def set_listening_active(self, active: bool):
        """Thread-safe listening active setter"""
        with self._lock:
            self.listening_active = active
    
    def set_running(self, running: bool):
        """Thread-safe running state setter"""
        with self._lock:
            self.running = running
    
    def is_running(self) -> bool:
        """Thread-safe running state getter"""
        with self._lock:
            return self.running
    
    def get_error_count(self) -> int:
        """Thread-safe error count getter"""
        with self._lock:
            return self.error_count
    
    def to_dict(self) -> dict:
        """Get current state as dictionary (thread-safe)"""
        with self._lock:
            return {
                'running': self.running,
                'voice_active': self.voice_active,
                'listening_active': self.listening_active,
                'error_count': self.error_count,
                'max_errors': self.max_errors,
                'v2_mode': self.v2_mode
            }
