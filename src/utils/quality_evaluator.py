"""
Quality Evaluator - Métricas de calidad para respuestas de JarvisIA V2

Evalúa automáticamente la calidad de respuestas usando métricas cuantitativas:
- Coherencia: estructura lógica y flujo
- Relevancia: pertinencia al query
- Completitud: coverage del topic
- Precisión: corrección factual (heurísticas)

Author: JarvisIA Team
Version: 1.0
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class QualityMetric(Enum):
    """Métricas de calidad medibles"""
    COHERENCE = "coherence"          # Estructura y flujo lógico
    RELEVANCE = "relevance"          # Pertinencia al query
    COMPLETENESS = "completeness"    # Coverage del topic
    PRECISION = "precision"          # Corrección (heurística)
    CLARITY = "clarity"              # Claridad de expresión


class ResponseCategory(Enum):
    """Categorías de respuesta"""
    EXCELLENT = "excellent"    # Score >= 0.9
    GOOD = "good"              # Score >= 0.7
    ACCEPTABLE = "acceptable"  # Score >= 0.5
    POOR = "poor"              # Score >= 0.3
    CRITICAL = "critical"      # Score < 0.3


class QualityEvaluator:
    """
    Evaluador de calidad automático para respuestas de LLM
    
    Usa heurísticas y análisis de texto para estimar calidad
    sin necesidad de modelos adicionales.
    """
    
    # Error markers que indican respuesta problemática
    ERROR_MARKERS = [
        "error", "failed", "unable", "cannot", "sorry", "apologize",
        "disculpa", "no puedo", "imposible", "error", "fallo"
    ]
    
    # Filler words que indican poca densidad de información
    FILLER_WORDS = [
        "en realidad", "básicamente", "literalmente", "obviamente",
        "actually", "basically", "literally", "obviously", "like", "you know"
    ]
    
    def __init__(
        self,
        log_file: str = "logs/quality_evaluations.jsonl",
        enable_detailed_logging: bool = True,
        debug: bool = False
    ):
        """
        Initialize Quality Evaluator
        
        Args:
            log_file: File to log evaluations
            enable_detailed_logging: Log detailed metrics
            debug: Enable debug logging
        """
        self.logger = logging.getLogger("QualityEvaluator")
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        self.log_file = log_file
        self.enable_detailed_logging = enable_detailed_logging
        self.debug = debug
        
        self.logger.info("✅ QualityEvaluator initialized")
    
    def evaluate(
        self,
        query: str,
        response: str,
        expected_length_range: Optional[Tuple[int, int]] = None,
        expected_keywords: Optional[List[str]] = None,
        task_type: Optional[str] = None
    ) -> Dict:
        """
        Evalúa calidad de respuesta con múltiples métricas
        
        Args:
            query: User query
            response: Model response
            expected_length_range: (min, max) expected response length
            expected_keywords: Keywords that should appear
            task_type: Optional task type for specialized evaluation
        
        Returns:
            Dict with detailed metrics and overall score
        """
        # Calculate individual metrics
        coherence = self._evaluate_coherence(response)
        relevance = self._evaluate_relevance(query, response, expected_keywords)
        completeness = self._evaluate_completeness(
            response, expected_length_range, task_type
        )
        precision = self._evaluate_precision(response)
        clarity = self._evaluate_clarity(response)
        
        # Weighted overall score
        overall_score = (
            0.25 * coherence +
            0.30 * relevance +
            0.20 * completeness +
            0.15 * precision +
            0.10 * clarity
        )
        
        # Categorize
        category = self._categorize_score(overall_score)
        
        # Issues detected
        issues = self._detect_issues(response)
        
        evaluation = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:200],
            "response_length": len(response),
            "metrics": {
                "coherence": round(coherence, 2),
                "relevance": round(relevance, 2),
                "completeness": round(completeness, 2),
                "precision": round(precision, 2),
                "clarity": round(clarity, 2)
            },
            "overall_score": round(overall_score, 2),
            "category": category.value,
            "issues": issues,
            "passed": overall_score >= 0.5
        }
        
        # Log if enabled
        if self.enable_detailed_logging:
            self._log_evaluation(evaluation)
        
        self.logger.debug(
            f"Evaluation: score={overall_score:.2f}, category={category.value}, "
            f"coherence={coherence:.2f}, relevance={relevance:.2f}"
        )
        
        return evaluation
    
    def _evaluate_coherence(self, response: str) -> float:
        """
        Evalúa coherencia estructural
        
        Checks:
        - Estructura en párrafos/frases
        - Uso de conectores lógicos
        - Progresión lógica (sin repeticiones excesivas)
        """
        score = 0.0
        
        # Check 1: Estructura (sentences, paragraphs)
        sentences = len(re.findall(r'[.!?]+', response))
        paragraphs = len(response.split('\n\n'))
        
        if sentences >= 2:
            score += 0.3
        if paragraphs >= 1:
            score += 0.2
        
        # Check 2: Conectores lógicos
        connectors = [
            "por lo tanto", "sin embargo", "además", "así que", "entonces",
            "therefore", "however", "furthermore", "thus", "then"
        ]
        connector_count = sum(1 for c in connectors if c in response.lower())
        if connector_count >= 1:
            score += 0.2
        
        # Check 3: No repeticiones excesivas (bigrams únicos)
        words = response.lower().split()
        if len(words) > 5:
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
            unique_ratio = len(set(bigrams)) / len(bigrams) if bigrams else 1.0
            score += 0.3 * unique_ratio
        
        return min(1.0, score)
    
    def _evaluate_relevance(
        self,
        query: str,
        response: str,
        expected_keywords: Optional[List[str]] = None
    ) -> float:
        """
        Evalúa relevancia al query
        
        Checks:
        - Términos del query presentes en response
        - Keywords esperados presentes
        - No respuestas genéricas/off-topic
        """
        score = 0.0
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Check 1: Query terms overlap
        query_words = set(re.findall(r'\w+', query_lower))
        response_words = set(re.findall(r'\w+', response_lower))
        
        # Remove stop words
        stop_words = {"el", "la", "de", "que", "y", "a", "en", "un", "por", "con",
                      "the", "a", "an", "and", "or", "but", "in", "on", "at", "to"}
        query_words = query_words - stop_words
        response_words = response_words - stop_words
        
        if query_words:
            overlap = len(query_words & response_words) / len(query_words)
            score += 0.4 * overlap
        
        # Check 2: Expected keywords
        if expected_keywords:
            found = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
            keyword_ratio = found / len(expected_keywords)
            score += 0.4 * keyword_ratio
        else:
            score += 0.4  # No penalty if not provided
        
        # Check 3: Not generic response
        generic_phrases = [
            "i don't know", "no sé", "no estoy seguro", "not sure",
            "no tengo información", "no information", "cannot answer"
        ]
        is_generic = any(phrase in response_lower for phrase in generic_phrases)
        if not is_generic:
            score += 0.2
        
        return min(1.0, score)
    
    def _evaluate_completeness(
        self,
        response: str,
        expected_length_range: Optional[Tuple[int, int]] = None,
        task_type: Optional[str] = None
    ) -> float:
        """
        Evalúa completitud de la respuesta
        
        Checks:
        - Longitud apropiada para el tipo de tarea
        - Coverage de aspectos esperados (estructura)
        """
        score = 0.0
        response_len = len(response)
        
        # Check 1: Length in expected range
        if expected_length_range:
            min_len, max_len = expected_length_range
            if min_len <= response_len <= max_len:
                score += 0.5
            elif response_len < min_len:
                score += 0.3 * (response_len / min_len)
            else:  # Too long but not necessarily bad
                score += 0.4
        else:
            # Default: at least 50 chars
            if response_len >= 50:
                score += 0.5
            else:
                score += 0.3 * (response_len / 50)
        
        # Check 2: Estructura completa (task-specific)
        if task_type == "code" or "código" in task_type.lower() if task_type else False:
            # Code should have code blocks
            if "```" in response or "def " in response or "class " in response:
                score += 0.3
        elif task_type == "reasoning" or task_type == "analysis":
            # Should have multiple points/steps
            bullets = response.count("•") + response.count("-") + response.count("*")
            numbered = len(re.findall(r'\d+\.', response))
            if bullets >= 2 or numbered >= 2:
                score += 0.3
        else:
            # Generic: has paragraphs
            if "\n\n" in response or response.count('.') >= 2:
                score += 0.3
        
        # Check 3: No truncamiento obvio
        if not response.endswith("..."):
            score += 0.2
        
        return min(1.0, score)
    
    def _evaluate_precision(self, response: str) -> float:
        """
        Evalúa precisión (heurística)
        
        Checks:
        - No errores evidentes
        - No contradicciones internas
        - Uso de datos concretos (números, ejemplos)
        """
        score = 0.5  # Base score
        
        # Check 1: No error markers
        has_errors = any(marker in response.lower() for marker in self.ERROR_MARKERS)
        if not has_errors:
            score += 0.2
        else:
            score -= 0.3
        
        # Check 2: Has concrete data (numbers, examples)
        has_numbers = bool(re.search(r'\d+', response))
        has_examples = "ejemplo" in response.lower() or "example" in response.lower()
        if has_numbers or has_examples:
            score += 0.2
        
        # Check 3: Not overly hedged (too many "quizás", "tal vez")
        hedge_words = ["quizás", "tal vez", "posiblemente", "maybe", "perhaps", "possibly"]
        hedge_count = sum(response.lower().count(word) for word in hedge_words)
        if hedge_count > 3:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _evaluate_clarity(self, response: str) -> float:
        """
        Evalúa claridad de expresión
        
        Checks:
        - Frases no demasiado largas
        - Poco uso de filler words
        - Vocabulario apropiado (no demasiado técnico sin explicación)
        """
        score = 0.0
        
        # Check 1: Sentence length (not too long)
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_len <= 25:  # Sweet spot
                score += 0.4
            elif avg_sentence_len <= 40:
                score += 0.2
        
        # Check 2: Low filler word count
        filler_count = sum(1 for word in self.FILLER_WORDS if word in response.lower())
        if filler_count <= 2:
            score += 0.3
        elif filler_count <= 5:
            score += 0.1
        
        # Check 3: Formatting for readability
        has_formatting = (
            "```" in response or  # Code blocks
            "\n\n" in response or  # Paragraphs
            bool(re.search(r'\n[-•*]', response))  # Lists
        )
        if has_formatting:
            score += 0.3
        
        return min(1.0, score)
    
    def _categorize_score(self, score: float) -> ResponseCategory:
        """Categorize response by score"""
        if score >= 0.9:
            return ResponseCategory.EXCELLENT
        elif score >= 0.7:
            return ResponseCategory.GOOD
        elif score >= 0.5:
            return ResponseCategory.ACCEPTABLE
        elif score >= 0.3:
            return ResponseCategory.POOR
        else:
            return ResponseCategory.CRITICAL
    
    def _detect_issues(self, response: str) -> List[str]:
        """Detecta problemas específicos en la respuesta"""
        issues = []
        
        # Too short
        if len(response) < 20:
            issues.append("Response too short")
        
        # Has error markers
        if any(marker in response.lower() for marker in self.ERROR_MARKERS):
            issues.append("Contains error/failure indicators")
        
        # Too much hedging
        hedge_words = ["quizás", "tal vez", "posiblemente", "maybe", "perhaps", "possibly"]
        hedge_count = sum(response.lower().count(word) for word in hedge_words)
        if hedge_count > 5:
            issues.append("Excessive hedging/uncertainty")
        
        # No punctuation (likely truncated or malformed)
        if '.' not in response and '!' not in response and '?' not in response:
            issues.append("Missing punctuation (possible truncation)")
        
        # Repetition (same word 5+ times in a row vicinity)
        words = response.lower().split()
        for i in range(len(words) - 4):
            window = words[i:i+5]
            if len(set(window)) == 1:
                issues.append("Excessive repetition detected")
                break
        
        return issues
    
    def _log_evaluation(self, evaluation: Dict):
        """Log evaluation to file"""
        try:
            import json
            from pathlib import Path
            
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_path, 'a') as f:
                json.dump(evaluation, f)
                f.write('\n')
        except Exception as e:
            self.logger.error(f"Error logging evaluation: {e}")
    
    def get_category_color(self, category: ResponseCategory) -> str:
        """Get color code for category (for terminal display)"""
        colors = {
            ResponseCategory.EXCELLENT: "\033[92m",  # Green
            ResponseCategory.GOOD: "\033[94m",       # Blue
            ResponseCategory.ACCEPTABLE: "\033[93m", # Yellow
            ResponseCategory.POOR: "\033[91m",       # Red
            ResponseCategory.CRITICAL: "\033[95m"    # Magenta
        }
        return colors.get(category, "")
    
    def print_evaluation(self, evaluation: Dict):
        """Pretty print evaluation results"""
        category = ResponseCategory(evaluation["category"])
        color = self.get_category_color(category)
        reset = "\033[0m"
        
        print(f"\n{color}{'='*80}")
        print(f"QUALITY EVALUATION - {category.value.upper()}")
        print(f"{'='*80}{reset}\n")
        
        print(f"Overall Score: {color}{evaluation['overall_score']:.2f}{reset}")
        print(f"Category: {color}{category.value}{reset}")
        print(f"Passed: {'✅' if evaluation['passed'] else '❌'}\n")
        
        print("Metrics:")
        for metric, value in evaluation["metrics"].items():
            bar_length = int(value * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"  {metric.capitalize():15} {bar} {value:.2f}")
        
        if evaluation["issues"]:
            print(f"\n{color}Issues Detected:{reset}")
            for issue in evaluation["issues"]:
                print(f"  ⚠️  {issue}")
        else:
            print(f"\n✅ No issues detected")
        
        print()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    evaluator = QualityEvaluator(debug=True)
    
    print("\n" + "="*80)
    print("Testing QualityEvaluator")
    print("="*80 + "\n")
    
    # Test 1: Good response
    print("Test 1: Evaluating GOOD response")
    eval1 = evaluator.evaluate(
        query="¿Qué es Python?",
        response="Python es un lenguaje de programación de alto nivel, interpretado y de propósito general. "
                 "Fue creado por Guido van Rossum en 1991. Se caracteriza por su sintaxis clara y legible, "
                 "lo que facilita el aprendizaje y la escritura de código. Python soporta múltiples paradigmas "
                 "de programación, incluyendo programación orientada a objetos, imperativa y funcional. "
                 "Es ampliamente usado en desarrollo web, ciencia de datos, machine learning y automatización.",
        expected_keywords=["python", "lenguaje", "programación"],
        task_type="explanation"
    )
    evaluator.print_evaluation(eval1)
    
    # Test 2: Poor response
    print("\nTest 2: Evaluating POOR response")
    eval2 = evaluator.evaluate(
        query="Explica el algoritmo quicksort",
        response="Lo siento, no puedo ayudar con eso.",
        expected_keywords=["quicksort", "algoritmo", "ordenamiento"],
        task_type="explanation"
    )
    evaluator.print_evaluation(eval2)
    
    # Test 3: Code response
    print("\nTest 3: Evaluating CODE response")
    eval3 = evaluator.evaluate(
        query="Genera una función de búsqueda binaria",
        response="Aquí está la función de búsqueda binaria:\n\n```python\ndef binary_search(arr, target):\n    "
                 "left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        "
                 "if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            "
                 "left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n```\n\n"
                 "Esta función busca un elemento en un array ordenado con complejidad O(log n).",
        expected_keywords=["búsqueda", "binaria", "array"],
        task_type="code"
    )
    evaluator.print_evaluation(eval3)
    
    print("✅ Tests completed!")
