"""
Input Validation Utilities
Comprehensive input validation and sanitization
"""

import re
import html
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

from src.utils.error_handler import ValidationError


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    cleaned_value: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class InputValidator:
    """
    Comprehensive input validator for queries and commands
    
    Usage:
        validator = InputValidator()
        result = validator.validate_query("User input here")
        if result.is_valid:
            process(result.cleaned_value)
    """
    
    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--\s*$)",
        r"(;\s*DROP\b)",
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\$\(",
        r"`.*`",
        r"\|\s*bash",
        r"\|\s*sh",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
    ]
    
    # Blocked terms for inappropriate content
    BLOCKED_TERMS = [
        "hack", "crack", "exploit", "malware", "virus",
        # Add more as needed
    ]
    
    def __init__(self, 
                 max_length: int = 5000,
                 min_length: int = 1,
                 allow_special_chars: bool = True,
                 strict_mode: bool = False):
        """
        Initialize validator
        
        Args:
            max_length: Maximum allowed input length
            min_length: Minimum allowed input length
            allow_special_chars: Whether to allow special characters
            strict_mode: If True, apply stricter validation
        """
        self.max_length = max_length
        self.min_length = min_length
        self.allow_special_chars = allow_special_chars
        self.strict_mode = strict_mode
        self.logger = logging.getLogger("InputValidator")
    
    def validate_query(self, query: str) -> ValidationResult:
        """
        Validate and sanitize a user query
        
        Args:
            query: User input query
        
        Returns:
            ValidationResult with validation status and cleaned value
        """
        if not isinstance(query, str):
            return ValidationResult(
                is_valid=False,
                error_message="Query must be a string"
            )
        
        # Check length
        if len(query) < self.min_length:
            return ValidationResult(
                is_valid=False,
                error_message=f"Query too short (min {self.min_length} characters)"
            )
        
        if len(query) > self.max_length:
            return ValidationResult(
                is_valid=False,
                error_message=f"Query too long (max {self.max_length} characters)"
            )
        
        # Check for null bytes
        if '\x00' in query:
            return ValidationResult(
                is_valid=False,
                error_message="Query contains invalid null bytes"
            )
        
        warnings = []
        
        # Security checks
        if self._check_sql_injection(query):
            return ValidationResult(
                is_valid=False,
                error_message="Query contains potential SQL injection patterns"
            )
        
        if self._check_command_injection(query):
            return ValidationResult(
                is_valid=False,
                error_message="Query contains potential command injection patterns"
            )
        
        if self._check_xss(query):
            warnings.append("Query contains HTML/JavaScript patterns (sanitized)")
        
        # Check blocked terms
        blocked_found = self._check_blocked_terms(query)
        if blocked_found:
            if self.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Query contains blocked terms: {', '.join(blocked_found)}"
                )
            else:
                warnings.append(f"Query contains sensitive terms: {', '.join(blocked_found)}")
        
        # Sanitize
        cleaned = self._sanitize_input(query)
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=cleaned,
            warnings=warnings
        )
    
    def _check_sql_injection(self, text: str) -> bool:
        """Check for SQL injection patterns"""
        text_upper = text.upper()
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                self.logger.warning(f"SQL injection pattern detected: {pattern}")
                return True
        return False
    
    def _check_command_injection(self, text: str) -> bool:
        """Check for command injection patterns"""
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text):
                self.logger.warning(f"Command injection pattern detected: {pattern}")
                return True
        return False
    
    def _check_xss(self, text: str) -> bool:
        """Check for XSS patterns"""
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _check_blocked_terms(self, text: str) -> List[str]:
        """Check for blocked terms"""
        text_lower = text.lower()
        found = []
        
        for term in self.BLOCKED_TERMS:
            if term.lower() in text_lower:
                found.append(term)
        
        return found
    
    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize input text
        
        Args:
            text: Input text
        
        Returns:
            Sanitized text
        """
        # Remove null bytes
        cleaned = text.replace('\x00', '')
        
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        
        # HTML escape if XSS patterns detected
        if self._check_xss(cleaned):
            cleaned = html.escape(cleaned)
        
        # Remove control characters except newlines and tabs
        cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', cleaned)
        
        # Trim
        cleaned = cleaned.strip()
        
        return cleaned
    
    def validate_file_path(self, path: str) -> ValidationResult:
        """
        Validate a file path
        
        Args:
            path: File path to validate
        
        Returns:
            ValidationResult
        """
        if not isinstance(path, str):
            return ValidationResult(
                is_valid=False,
                error_message="Path must be a string"
            )
        
        # Check for path traversal
        if '..' in path or path.startswith('/'):
            return ValidationResult(
                is_valid=False,
                error_message="Path contains invalid traversal patterns"
            )
        
        # Check for null bytes
        if '\x00' in path:
            return ValidationResult(
                is_valid=False,
                error_message="Path contains null bytes"
            )
        
        # Sanitize
        cleaned = path.strip()
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=cleaned
        )
    
    def validate_api_key(self, api_key: str) -> ValidationResult:
        """
        Validate an API key format
        
        Args:
            api_key: API key to validate
        
        Returns:
            ValidationResult
        """
        if not isinstance(api_key, str):
            return ValidationResult(
                is_valid=False,
                error_message="API key must be a string"
            )
        
        # Remove whitespace
        cleaned = api_key.strip()
        
        # Check minimum length
        if len(cleaned) < 10:
            return ValidationResult(
                is_valid=False,
                error_message="API key too short"
            )
        
        # Check for invalid characters
        if not re.match(r'^[A-Za-z0-9_\-\.]+$', cleaned):
            return ValidationResult(
                is_valid=False,
                error_message="API key contains invalid characters"
            )
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=cleaned
        )
