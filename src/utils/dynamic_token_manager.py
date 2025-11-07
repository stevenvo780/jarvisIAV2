"""
Dynamic Token Manager - Adaptive max_tokens calculation for JarvisIA V2

Automatically adjusts max_tokens based on:
- Query difficulty (1-100)
- Query type (chat, code, reasoning, analysis)
- Available VRAM
- Conversation context length

Author: JarvisIA Team
Version: 1.0
"""

import re
import logging
from typing import Tuple, Optional, Dict
from enum import Enum


class QueryType(Enum):
    """Types of queries with different token requirements"""
    MINIMAL = "minimal"          # Greetings, confirmations
    CHAT = "chat"                # Simple conversation
    EXPLANATION = "explanation"  # Detailed explanations
    CODE = "code"                # Code generation/analysis
    REASONING = "reasoning"      # Step-by-step reasoning
    ANALYSIS = "analysis"        # Deep analysis
    MULTIPART = "multipart"      # Complex multi-step tasks


class DynamicTokenManager:
    """
    Intelligent token allocation for optimal response quality vs efficiency
    
    Features:
    - Difficulty-based scaling
    - Query type detection
    - VRAM-aware limits
    - Conversation length adjustment
    - Debug mode for tuning
    """
    
    # Token ranges by category (min, max)
    TOKEN_RANGES: Dict[str, Tuple[int, int]] = {
        "minimal": (64, 128),        # "Hola", "Sí", "Gracias"
        "short": (128, 256),         # Simple questions
        "medium": (256, 512),        # Normal conversation
        "long": (512, 1024),         # Detailed explanations
        "extended": (1024, 2048),    # Deep analysis
        "code": (512, 4096),         # Code generation
        "reasoning": (1024, 4096),   # Chain-of-thought
        "max": (2048, 8192)          # Complex multi-step
    }
    
    # Query type patterns (regex)
    QUERY_PATTERNS = {
        QueryType.MINIMAL: [
            r"^(hola|hi|hey|gracias|ok|sí|no|claro|perfecto|bien)[\s\.\!]*$",
        ],
        QueryType.CODE: [
            r"\b(código|code|función|function|clase|class|script|programa|implementa|debug)\b",
            r"```",
            r"\bdef\b|\bclass\b|\bimport\b|\bfor\b|\bwhile\b",
        ],
        QueryType.REASONING: [
            r"\b(explica|analiza|por qué|cómo funciona|paso a paso|razona|demuestra)\b",
            r"\b(explain|analyze|why|how does|step by step|reason|prove)\b",
        ],
        QueryType.ANALYSIS: [
            r"\b(compara|evalúa|diferencia|ventajas|desventajas|pros|cons)\b",
            r"\b(compare|evaluate|difference|advantages|disadvantages)\b",
        ],
    }
    
    def __init__(
        self,
        base_range: Tuple[int, int] = (256, 2048),
        vram_limit_gb: Optional[float] = None,
        debug: bool = False
    ):
        """
        Initialize Dynamic Token Manager
        
        Args:
            base_range: Default (min, max) tokens
            vram_limit_gb: VRAM limit in GB (auto-adjust if low)
            debug: Enable debug logging
        """
        self.logger = logging.getLogger("DynamicTokenManager")
        self.base_range = base_range
        self.vram_limit_gb = vram_limit_gb
        self.debug = debug
        
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        self.logger.info("✅ DynamicTokenManager initialized")
    
    def detect_query_type(self, query: str) -> QueryType:
        """
        Detect query type from content
        
        Args:
            query: User query text
        
        Returns:
            Detected QueryType
        """
        query_lower = query.lower().strip()
        
        # Check patterns in order of specificity
        for query_type, patterns in self.QUERY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    self.logger.debug(f"Detected type: {query_type.value} (pattern: {pattern[:30]}...)")
                    return query_type
        
        # Fallback based on length and complexity
        word_count = len(query_lower.split())
        
        if word_count <= 3:
            return QueryType.MINIMAL
        elif word_count <= 10:
            return QueryType.CHAT
        else:
            return QueryType.EXPLANATION
    
    def calculate_max_tokens(
        self,
        query: str,
        difficulty: int,
        query_type: Optional[QueryType] = None,
        available_vram_gb: Optional[float] = None,
        conversation_length: int = 0,
        force_range: Optional[str] = None
    ) -> int:
        """
        Calculate optimal max_tokens dynamically
        
        Args:
            query: User query text
            difficulty: Query difficulty score (1-100)
            query_type: Override auto-detection
            available_vram_gb: Current available VRAM
            conversation_length: Length of conversation history (turns)
            force_range: Force specific range ("minimal", "short", etc.)
        
        Returns:
            Optimal max_tokens value
        """
        # 1. Detect query type if not provided
        if query_type is None:
            query_type = self.detect_query_type(query)
        
        # 2. Base tokens from difficulty
        base_tokens = self._tokens_from_difficulty(difficulty)
        
        # 3. Adjust by query type
        type_multiplier = self._get_type_multiplier(query_type)
        adjusted_tokens = int(base_tokens * type_multiplier)
        
        # 4. Apply VRAM constraints
        vram_gb = available_vram_gb or self.vram_limit_gb
        if vram_gb is not None:
            adjusted_tokens = self._apply_vram_limit(adjusted_tokens, vram_gb)
        
        # 5. Adjust for conversation length (reduce for long contexts)
        if conversation_length > 5:
            # Reduce tokens by 10% per 5 turns (max -30%)
            reduction_factor = max(0.7, 1.0 - (conversation_length // 5) * 0.1)
            adjusted_tokens = int(adjusted_tokens * reduction_factor)
            self.logger.debug(f"Reduced tokens by {int((1-reduction_factor)*100)}% due to long conversation")
        
        # 6. Force specific range if requested
        if force_range and force_range in self.TOKEN_RANGES:
            min_tok, max_tok = self.TOKEN_RANGES[force_range]
            adjusted_tokens = max(min_tok, min(adjusted_tokens, max_tok))
        
        # 7. Clamp to reasonable bounds
        final_tokens = self._clamp_tokens(adjusted_tokens)
        
        if self.debug:
            self.logger.debug(
                f"Token calculation: difficulty={difficulty}, type={query_type.value}, "
                f"base={base_tokens}, multiplier={type_multiplier:.2f}, "
                f"vram_gb={vram_gb}, conv_len={conversation_length}, "
                f"final={final_tokens}"
            )
        
        return final_tokens
    
    def _tokens_from_difficulty(self, difficulty: int) -> int:
        """
        Map difficulty (1-100) to base tokens
        
        Mapping:
        - 1-20: 128-256 (minimal/short)
        - 21-40: 256-512 (short/medium)
        - 41-60: 512-1024 (medium/long)
        - 61-80: 1024-2048 (long/extended)
        - 81-100: 2048-4096 (extended/max)
        """
        if difficulty <= 20:
            return int(128 + (difficulty / 20) * (256 - 128))
        elif difficulty <= 40:
            return int(256 + ((difficulty - 20) / 20) * (512 - 256))
        elif difficulty <= 60:
            return int(512 + ((difficulty - 40) / 20) * (1024 - 512))
        elif difficulty <= 80:
            return int(1024 + ((difficulty - 60) / 20) * (2048 - 1024))
        else:
            return int(2048 + ((difficulty - 80) / 20) * (4096 - 2048))
    
    def _get_type_multiplier(self, query_type: QueryType) -> float:
        """
        Get token multiplier based on query type
        
        Multipliers:
        - MINIMAL: 0.5x
        - CHAT: 0.8x
        - EXPLANATION: 1.0x (baseline)
        - CODE: 1.5x
        - REASONING: 2.0x
        - ANALYSIS: 1.8x
        - MULTIPART: 2.5x
        """
        multipliers = {
            QueryType.MINIMAL: 0.5,
            QueryType.CHAT: 0.8,
            QueryType.EXPLANATION: 1.0,
            QueryType.CODE: 1.5,
            QueryType.REASONING: 2.0,
            QueryType.ANALYSIS: 1.8,
            QueryType.MULTIPART: 2.5,
        }
        
        return multipliers.get(query_type, 1.0)
    
    def _apply_vram_limit(self, tokens: int, available_vram_gb: float) -> int:
        """
        Cap tokens based on available VRAM to prevent OOM
        
        VRAM budgets:
        - < 4GB: cap at 512
        - 4-8GB: cap at 1024
        - 8-12GB: cap at 2048
        - > 12GB: no cap (use 8192 max)
        """
        if available_vram_gb < 4.0:
            cap = 512
        elif available_vram_gb < 8.0:
            cap = 1024
        elif available_vram_gb < 12.0:
            cap = 2048
        else:
            cap = 8192
        
        if tokens > cap:
            self.logger.debug(f"VRAM limit: capping {tokens} → {cap} (VRAM: {available_vram_gb:.1f}GB)")
            return cap
        
        return tokens
    
    def _clamp_tokens(self, tokens: int, min_tokens: int = 64, max_tokens: int = 8192) -> int:
        """Clamp tokens to global min/max bounds"""
        return max(min_tokens, min(tokens, max_tokens))
    
    def get_token_stats(self, tokens: int) -> Dict:
        """
        Get statistics about token allocation
        
        Returns:
            Dict with category, range, efficiency score
        """
        for category, (min_tok, max_tok) in self.TOKEN_RANGES.items():
            if min_tok <= tokens <= max_tok:
                efficiency = (tokens - min_tok) / (max_tok - min_tok) if max_tok > min_tok else 1.0
                return {
                    "category": category,
                    "tokens": tokens,
                    "range": (min_tok, max_tok),
                    "efficiency": round(efficiency, 2),
                    "is_optimal": 0.4 <= efficiency <= 0.8  # Sweet spot
                }
        
        return {
            "category": "custom",
            "tokens": tokens,
            "range": (64, 8192),
            "efficiency": 0.5,
            "is_optimal": False
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    manager = DynamicTokenManager(debug=True)
    
    # Test cases
    test_cases = [
        ("Hola", 10, None),
        ("¿Cómo estás?", 15, None),
        ("Explica qué es una red neuronal", 45, None),
        ("Escribe código Python para ordenar una lista", 55, None),
        ("Analiza paso a paso cómo funciona el algoritmo quicksort", 70, None),
        ("Compara ventajas y desventajas de React vs Vue con ejemplos", 85, None),
    ]
    
    print("\n" + "="*80)
    print("DYNAMIC TOKEN MANAGER - TEST CASES")
    print("="*80 + "\n")
    
    for query, difficulty, _ in test_cases:
        tokens = manager.calculate_max_tokens(
            query=query,
            difficulty=difficulty,
            available_vram_gb=10.0
        )
        
        stats = manager.get_token_stats(tokens)
        query_type = manager.detect_query_type(query)
        
        print(f"Query: {query[:50]}...")
        print(f"  Difficulty: {difficulty}")
        print(f"  Type: {query_type.value}")
        print(f"  Tokens: {tokens}")
        print(f"  Category: {stats['category']}")
        print(f"  Optimal: {'✅' if stats['is_optimal'] else '⚠️'}")
        print()
