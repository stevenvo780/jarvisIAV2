"""
Enhanced query validation with injection detection and sanitization
"""

import re
import logging
from typing import Tuple, Optional


logger = logging.getLogger(__name__)


class QueryValidator:
    """
    Robust query validator with multiple security checks
    
    Features:
    - Length validation
    - Prompt injection detection
    - Blocked terms filtering
    - Character sanitization
    """
    
    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        r'ignore\s+(previous|all|prior)\s+(instructions?|prompts?|rules?)',
        r'system\s*:\s*(you\s+are|act\s+as)',
        r'</s>\s*<\|im_start\|>',  # Token injection
        r'<\|.*?\|>',  # Special tokens
        r'\[INST\]|\[/INST\]',  # Llama instruction tokens
        r'assistant\s*:\s*\[',  # Role manipulation
        r'human\s*:\s*ignore',
        r'new\s+instructions?\s*:',
        r'disregard\s+(previous|all)',
    ]
    
    def __init__(
        self, 
        max_length: int = 5000,
        blocked_terms: Optional[list] = None,
        strict_mode: bool = True
    ):
        """
        Initialize validator
        
        Args:
            max_length: Maximum query length
            blocked_terms: List of blocked terms
            strict_mode: If True, apply strict validation
        """
        self.max_length = max_length
        self.blocked_terms = blocked_terms or []
        self.strict_mode = strict_mode
        
        # Compile patterns for performance
        self._compiled_injection_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.INJECTION_PATTERNS
        ]
    
    def validate(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate query with multiple security checks
        
        Args:
            query: User query to validate
        
        Returns:
            (is_valid, error_message)
        """
        # Empty check
        if not query or query.isspace():
            return False, "Query cannot be empty"
        
        # Length check
        if len(query) > self.max_length:
            return False, f"Query too long ({len(query)} > {self.max_length})"
        
        # Injection detection
        for pattern in self._compiled_injection_patterns:
            if pattern.search(query):
                logger.warning(f"Injection attempt detected: {pattern.pattern}")
                return False, "Potential prompt injection detected"
        
        # Blocked terms check (word boundaries)
        for term in self.blocked_terms:
            if re.search(rf'\b{re.escape(term)}\b', query, re.IGNORECASE):
                logger.warning(f"Blocked term detected: {term}")
                return False, f"Query contains blocked content"
        
        # Excessive special characters (potential obfuscation)
        if self.strict_mode:
            special_chars = sum(1 for c in query if not c.isalnum() and not c.isspace())
            if special_chars > len(query) * 0.3:  # >30% special chars
                return False, "Excessive special characters"
        
        # Repeated characters (potential attack)
        if re.search(r'(.)\1{20,}', query):  # 20+ repeated chars
            return False, "Suspicious character repetition detected"
        
        return True, None
    
    def sanitize(self, query: str) -> str:
        """
        Sanitize query by removing dangerous patterns
        
        Args:
            query: Query to sanitize
        
        Returns:
            Sanitized query
        """
        # Remove control characters
        query = ''.join(char for char in query if ord(char) >= 32 or char in '\n\r\t')
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        # Remove special tokens
        query = re.sub(r'<\|.*?\|>', '', query)
        query = re.sub(r'\[/?INST\]', '', query)
        
        return query.strip()
