"""
Learning Manager - Sistema de aprendizaje continuo para JarvisIA V2

Análisis automático de calidad, detección de patrones y ajuste de parámetros.

Features:
- Análisis de calidad de respuestas (user feedback implícito)
- Detección de patrones de éxito/fallo
- Ajuste automático de parámetros por dominio
- Estadísticas de performance por modelo/task/difficulty
- Recomendaciones de optimización

Author: JarvisIA Team
Version: 1.0
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics


class LearningManager:
    """
    Sistema de aprendizaje continuo que analiza respuestas y ajusta parámetros
    
    Almacena interacciones con metadata y aprende de patrones de éxito/fallo.
    """
    
    def __init__(
        self,
        log_dir: str = "logs/learning",
        stats_file: str = "logs/learning/stats.json",
        enable_auto_tuning: bool = True,
        debug: bool = False
    ):
        """
        Initialize Learning Manager
        
        Args:
            log_dir: Directory para logs de aprendizaje
            stats_file: File para estadísticas acumuladas
            enable_auto_tuning: Enable automatic parameter tuning
            debug: Enable debug logging
        """
        self.logger = logging.getLogger("LearningManager")
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.enable_auto_tuning = enable_auto_tuning
        self.debug = debug
        
        # Load existing stats
        self.stats = self._load_stats()
        
        # Performance metrics by domain
        self.domain_metrics = defaultdict(lambda: {
            "total": 0,
            "successful": 0,
            "tokens_used": [],
            "response_times": [],
            "avg_difficulty": [],
            "models_used": defaultdict(int)
        })
        
        self.logger.info("✅ LearningManager initialized")
    
    def _load_stats(self) -> Dict:
        """Load stats from file or create new"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    stats = json.load(f)
                self.logger.info(f"Loaded stats from {self.stats_file}")
                return stats
            except Exception as e:
                self.logger.warning(f"Error loading stats: {e}, creating new")
        
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_interactions": 0,
            "by_model": {},
            "by_task": {},
            "by_difficulty_range": {},
            "quality_scores": [],
            "parameter_tuning_history": []
        }
    
    def _save_stats(self):
        """Save stats to file"""
        try:
            self.stats["last_updated"] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            self.logger.debug(f"Stats saved to {self.stats_file}")
        except Exception as e:
            self.logger.error(f"Error saving stats: {e}")
    
    def log_interaction(
        self,
        query: str,
        response: str,
        model: str,
        difficulty: int,
        task_type: str,
        tokens_used: int,
        response_time: float,
        quality_score: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log interaction con metadata completa
        
        Args:
            query: User query
            response: Model response
            model: Model name
            difficulty: Difficulty score (1-100)
            task_type: Task type
            tokens_used: Tokens consumed
            response_time: Response time in seconds
            quality_score: Optional quality score (0-1)
            metadata: Additional metadata
        
        Returns:
            Interaction ID
        """
        interaction_id = f"int_{int(datetime.now().timestamp())}_{self.stats['total_interactions']}"
        
        interaction = {
            "id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "query": query[:200],  # Truncate for privacy
            "response_length": len(response),
            "model": model,
            "difficulty": difficulty,
            "task_type": task_type,
            "tokens_used": tokens_used,
            "response_time": response_time,
            "quality_score": quality_score,
            "metadata": metadata or {}
        }
        
        # Update stats
        self.stats["total_interactions"] += 1
        
        # By model
        if model not in self.stats["by_model"]:
            self.stats["by_model"][model] = {
                "count": 0,
                "total_tokens": 0,
                "avg_response_time": 0,
                "quality_scores": []
            }
        self.stats["by_model"][model]["count"] += 1
        self.stats["by_model"][model]["total_tokens"] += tokens_used
        
        # By task
        if task_type not in self.stats["by_task"]:
            self.stats["by_task"][task_type] = {"count": 0, "avg_difficulty": 0}
        self.stats["by_task"][task_type]["count"] += 1
        
        # By difficulty range
        diff_range = self._get_difficulty_range(difficulty)
        if diff_range not in self.stats["by_difficulty_range"]:
            self.stats["by_difficulty_range"][diff_range] = {"count": 0, "avg_tokens": 0}
        self.stats["by_difficulty_range"][diff_range]["count"] += 1
        
        # Quality score
        if quality_score is not None:
            self.stats["quality_scores"].append(quality_score)
            self.stats["by_model"][model]["quality_scores"].append(quality_score)
        
        # Log to file
        log_file = self.log_dir / f"interactions_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        try:
            with open(log_file, 'a') as f:
                json.dump(interaction, f)
                f.write('\n')
        except Exception as e:
            self.logger.error(f"Error logging interaction: {e}")
        
        self._save_stats()
        
        self.logger.debug(
            f"Logged interaction {interaction_id}: {model}, {task_type}, "
            f"diff={difficulty}, tokens={tokens_used}, time={response_time:.2f}s"
        )
        
        return interaction_id
    
    def _get_difficulty_range(self, difficulty: int) -> str:
        """Get difficulty range label"""
        if difficulty <= 20:
            return "trivial (1-20)"
        elif difficulty <= 40:
            return "easy (21-40)"
        elif difficulty <= 60:
            return "medium (41-60)"
        elif difficulty <= 80:
            return "hard (61-80)"
        else:
            return "expert (81-100)"
    
    def analyze_quality(
        self,
        query: str,
        response: str,
        expected_min_length: int = 50,
        expected_keywords: Optional[List[str]] = None
    ) -> float:
        """
        Analiza calidad de respuesta automáticamente
        
        Heurísticas simples:
        - Longitud apropiada
        - Presencia de keywords esperados
        - No errores obvios
        - Estructura coherente
        
        Args:
            query: User query
            response: Model response
            expected_min_length: Minimum expected response length
            expected_keywords: Keywords que deberían aparecer
        
        Returns:
            Quality score 0-1
        """
        score = 0.0
        checks = 0
        
        # Check 1: Longitud apropiada
        if len(response) >= expected_min_length:
            score += 0.3
        checks += 1
        
        # Check 2: No errores obvios
        error_markers = [
            "error", "failed", "unable", "cannot", "sorry",
            "disculpa", "no puedo", "imposible"
        ]
        has_errors = any(marker in response.lower() for marker in error_markers)
        if not has_errors:
            score += 0.2
        checks += 1
        
        # Check 3: Keywords esperados (si se proporcionan)
        if expected_keywords:
            found_keywords = sum(1 for kw in expected_keywords if kw.lower() in response.lower())
            keyword_ratio = found_keywords / len(expected_keywords)
            score += keyword_ratio * 0.3
            checks += 1
        
        # Check 4: Estructura coherente (tiene párrafos/frases)
        sentences = response.count('.') + response.count('!') + response.count('?')
        if sentences >= 2:
            score += 0.2
        checks += 1
        
        # Normalize
        final_score = min(1.0, score)
        
        self.logger.debug(
            f"Quality analysis: length={len(response)}, "
            f"errors={has_errors}, sentences={sentences}, score={final_score:.2f}"
        )
        
        return final_score
    
    def detect_patterns(
        self,
        time_window_days: int = 7,
        min_samples: int = 10
    ) -> Dict:
        """
        Detecta patrones de éxito/fallo en interacciones recientes
        
        Args:
            time_window_days: Days to analyze
            min_samples: Minimum samples required
        
        Returns:
            Dict con patrones detectados
        """
        patterns = {
            "successful_combinations": [],  # (model, task, difficulty_range)
            "problematic_combinations": [],
            "optimal_token_ranges": {},  # task -> (min, max)
            "model_preferences": {},  # task -> best_model
            "recommendations": []
        }
        
        # Load recent interactions
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        recent_interactions = []
        
        for log_file in self.log_dir.glob("interactions_*.jsonl"):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        interaction = json.loads(line.strip())
                        int_date = datetime.fromisoformat(interaction["timestamp"])
                        if int_date >= cutoff_date:
                            recent_interactions.append(interaction)
            except Exception as e:
                self.logger.warning(f"Error reading {log_file}: {e}")
        
        if len(recent_interactions) < min_samples:
            self.logger.warning(
                f"Not enough samples ({len(recent_interactions)} < {min_samples}) for pattern detection"
            )
            patterns["recommendations"].append(
                f"Need at least {min_samples - len(recent_interactions)} more interactions for pattern analysis"
            )
            return patterns
        
        # Analyze by (model, task, difficulty_range)
        combinations = defaultdict(lambda: {
            "count": 0,
            "quality_scores": [],
            "tokens": [],
            "response_times": []
        })
        
        for inter in recent_interactions:
            key = (
                inter["model"],
                inter["task_type"],
                self._get_difficulty_range(inter["difficulty"])
            )
            
            combinations[key]["count"] += 1
            combinations[key]["tokens"].append(inter["tokens_used"])
            combinations[key]["response_times"].append(inter["response_time"])
            
            if inter.get("quality_score") is not None:
                combinations[key]["quality_scores"].append(inter["quality_score"])
        
        # Identify successful vs problematic
        for key, data in combinations.items():
            if data["count"] < 3:  # Skip low-sample combinations
                continue
            
            avg_quality = statistics.mean(data["quality_scores"]) if data["quality_scores"] else 0.5
            avg_tokens = statistics.mean(data["tokens"])
            avg_time = statistics.mean(data["response_times"])
            
            combination_info = {
                "model": key[0],
                "task": key[1],
                "difficulty_range": key[2],
                "count": data["count"],
                "avg_quality": round(avg_quality, 2),
                "avg_tokens": int(avg_tokens),
                "avg_time": round(avg_time, 2)
            }
            
            if avg_quality >= 0.7:
                patterns["successful_combinations"].append(combination_info)
            elif avg_quality < 0.4:
                patterns["problematic_combinations"].append(combination_info)
        
        # Optimal token ranges per task
        by_task = defaultdict(list)
        for inter in recent_interactions:
            if inter.get("quality_score", 0) >= 0.7:  # Only successful interactions
                by_task[inter["task_type"]].append(inter["tokens_used"])
        
        for task, tokens_list in by_task.items():
            if len(tokens_list) >= 5:
                patterns["optimal_token_ranges"][task] = (
                    int(min(tokens_list)),
                    int(max(tokens_list))
                )
        
        # Model preferences per task (highest avg quality)
        by_task_model = defaultdict(lambda: defaultdict(list))
        for inter in recent_interactions:
            if inter.get("quality_score") is not None:
                by_task_model[inter["task_type"]][inter["model"]].append(inter["quality_score"])
        
        for task, models_data in by_task_model.items():
            best_model = None
            best_avg = 0
            for model, scores in models_data.items():
                avg_score = statistics.mean(scores)
                if avg_score > best_avg:
                    best_avg = avg_score
                    best_model = model
            
            if best_model:
                patterns["model_preferences"][task] = {
                    "model": best_model,
                    "avg_quality": round(best_avg, 2)
                }
        
        # Generate recommendations
        if patterns["successful_combinations"]:
            patterns["recommendations"].append(
                f"✅ Found {len(patterns['successful_combinations'])} successful model+task combinations"
            )
        
        if patterns["problematic_combinations"]:
            patterns["recommendations"].append(
                f"⚠️  Found {len(patterns['problematic_combinations'])} problematic combinations - consider parameter adjustment"
            )
        
        if patterns["optimal_token_ranges"]:
            patterns["recommendations"].append(
                f"📊 Identified optimal token ranges for {len(patterns['optimal_token_ranges'])} tasks"
            )
        
        self.logger.info(f"Pattern detection complete: {len(recent_interactions)} interactions analyzed")
        return patterns
    
    def suggest_parameters(
        self,
        task_type: str,
        difficulty: int,
        model: str
    ) -> Dict:
        """
        Sugiere parámetros óptimos basados en aprendizaje
        
        Args:
            task_type: Task type
            difficulty: Difficulty score
            model: Model name
        
        Returns:
            Dict con parámetros sugeridos
        """
        suggestions = {
            "max_tokens": None,
            "temperature": 0.7,
            "confidence": 0.5,
            "source": "default"
        }
        
        # Check stats for this combination
        if model in self.stats.get("by_model", {}):
            model_stats = self.stats["by_model"][model]
            if model_stats["count"] >= 10:
                avg_tokens = model_stats["total_tokens"] / model_stats["count"]
                suggestions["max_tokens"] = int(avg_tokens * 1.2)  # +20% buffer
                suggestions["source"] = "learned"
                suggestions["confidence"] = min(1.0, model_stats["count"] / 50)
        
        return suggestions
    
    def get_stats_summary(self) -> Dict:
        """Get summary of learning statistics"""
        summary = {
            "total_interactions": self.stats["total_interactions"],
            "models_used": len(self.stats.get("by_model", {})),
            "tasks_analyzed": len(self.stats.get("by_task", {})),
            "avg_quality": round(statistics.mean(self.stats["quality_scores"]), 2) if self.stats["quality_scores"] else 0,
            "top_models": [],
            "top_tasks": []
        }
        
        # Top models by count
        if self.stats.get("by_model"):
            top_models = sorted(
                self.stats["by_model"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:3]
            summary["top_models"] = [
                {"model": m, "count": d["count"], "total_tokens": d["total_tokens"]}
                for m, d in top_models
            ]
        
        # Top tasks by count
        if self.stats.get("by_task"):
            top_tasks = sorted(
                self.stats["by_task"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:3]
            summary["top_tasks"] = [
                {"task": t, "count": d["count"]}
                for t, d in top_tasks
            ]
        
        return summary


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    manager = LearningManager(debug=True)
    
    # Simulate interactions
    print("\n" + "="*80)
    print("Testing LearningManager")
    print("="*80 + "\n")
    
    # Test 1: Log interaction
    print("Test 1: Log interaction")
    inter_id = manager.log_interaction(
        query="¿Qué es Python?",
        response="Python es un lenguaje de programación de alto nivel, interpretado y de propósito general. Es conocido por su sintaxis clara y legible...",
        model="qwen-14b",
        difficulty=50,
        task_type="question",
        tokens_used=256,
        response_time=1.5,
        quality_score=0.85
    )
    print(f"  Interaction logged: {inter_id}\n")
    
    # Test 2: Analyze quality
    print("Test 2: Analyze quality")
    quality = manager.analyze_quality(
        query="Explica Python",
        response="Python es un lenguaje moderno. Es fácil de aprender. Tiene muchas librerías.",
        expected_keywords=["python", "lenguaje", "programación"]
    )
    print(f"  Quality score: {quality:.2f}\n")
    
    # Test 3: Get stats
    print("Test 3: Get stats summary")
    summary = manager.get_stats_summary()
    print(f"  Total interactions: {summary['total_interactions']}")
    print(f"  Models used: {summary['models_used']}")
    print(f"  Avg quality: {summary['avg_quality']}\n")
    
    print("✅ Tests completed!")
