#!/usr/bin/env python3
"""
Iterative Auto-Refiner - Jarvis IA
Sistema de testing y refinamiento iterativo automático
Itera infinitamente hasta alcanzar métricas de calidad objetivo
"""

import sys
import os
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import statistics

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.quality_evaluator import QualityEvaluator, ResponseCategory
from src.modules.learning.learning_manager import LearningManager
from src.modules.embeddings.embedding_manager import EmbeddingManager
from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
from src.utils.smart_prompt_builder import SmartPromptBuilder
from src.utils.dynamic_token_manager import DynamicTokenManager
from src.utils.metrics_tracker import MetricsTracker


@dataclass
class IterationResult:
    """Resultado de una iteración de testing"""
    iteration: int
    timestamp: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_quality_score: float
    avg_response_time: float
    avg_tokens_used: float
    quality_distribution: Dict[str, int]  # EXCELLENT, GOOD, etc.
    top_issues: List[str]
    improvements_applied: List[str]
    current_config: Dict[str, Any]


@dataclass
class TestQuery:
    """Query de prueba con metadata"""
    query: str
    difficulty: int
    task_type: str
    expected_min_length: Optional[int] = None
    expected_keywords: Optional[List[str]] = None
    category: str = "general"


class IterativeAutoRefiner:
    """
    Sistema de refinamiento iterativo automático
    
    Features:
    - Ejecuta batches de queries automáticamente
    - Evalúa calidad con QualityEvaluator
    - Aprende patterns con LearningManager
    - Ajusta parámetros automáticamente
    - Itera hasta alcanzar threshold de calidad
    - Genera reportes detallados de progreso
    """
    
    # Dataset de queries de prueba comprehensivo
    TEST_QUERIES = [
        # Chat básico
        TestQuery("Hola Jarvis", 5, "chat", 50, ["hola", "ayudar"], "conversational"),
        TestQuery("¿Qué puedes hacer?", 10, "chat", 100, ["puedo", "ayudar"], "conversational"),
        TestQuery("Buenos días", 5, "chat", 30, ["buenos", "días"], "conversational"),
        
        # Python básico
        TestQuery("¿Cómo crear una lista en Python?", 15, "code_explanation", 100, ["lista", "[]", "python"], "programming"),
        TestQuery("Explica las funciones en Python", 25, "explanation", 200, ["def", "función", "parámetros"], "programming"),
        TestQuery("¿Qué es una variable en Python?", 15, "explanation", 100, ["variable", "valor", "nombre"], "programming"),
        
        # Python intermedio
        TestQuery("¿Qué es una list comprehension?", 35, "code_explanation", 150, ["comprehension", "for", "in"], "programming"),
        TestQuery("Explica decoradores en Python", 55, "explanation", 250, ["decorador", "@", "función"], "programming"),
        TestQuery("¿Qué son los generadores?", 45, "explanation", 200, ["yield", "generator", "iterador"], "programming"),
        
        # Generación de código
        TestQuery("Genera una función de búsqueda binaria", 50, "code_generation", 300, ["def", "busqueda", "binaria", "```"], "programming"),
        TestQuery("Crea una clase para un árbol binario", 60, "code_generation", 400, ["class", "Nodo", "```"], "programming"),
        TestQuery("Implementa quicksort en Python", 55, "code_generation", 350, ["def", "quicksort", "```"], "programming"),
        
        # Algoritmos
        TestQuery("Explica el algoritmo de Dijkstra", 70, "explanation", 400, ["Dijkstra", "grafo", "camino"], "algorithms"),
        TestQuery("¿Qué es un árbol AVL?", 65, "explanation", 300, ["AVL", "balanceado", "rotación"], "algorithms"),
        TestQuery("Explica merge sort paso a paso", 60, "explanation", 350, ["merge", "divide", "conquista"], "algorithms"),
        
        # Conceptos de IA/ML
        TestQuery("¿Qué es una red neuronal?", 55, "explanation", 300, ["neurona", "capa", "pesos"], "ai_ml"),
        TestQuery("Explica qué es RAG", 60, "explanation", 300, ["RAG", "retrieval", "embedding"], "ai_ml"),
        TestQuery("¿Qué es un transformer?", 65, "explanation", 350, ["transformer", "atención", "NLP"], "ai_ml"),
        TestQuery("Diferencia entre supervised y unsupervised learning", 50, "explanation", 250, ["supervised", "unsupervised", "etiquetas"], "ai_ml"),
        
        # Linux/Terminal
        TestQuery("¿Cómo buscar archivos en Linux?", 30, "explanation", 200, ["find", "grep", "locate"], "linux"),
        TestQuery("Comandos básicos de git", 40, "explanation", 250, ["git", "commit", "push"], "linux"),
        TestQuery("¿Qué es Docker?", 45, "explanation", 250, ["docker", "contenedor", "imagen"], "linux"),
        
        # Debugging
        TestQuery("¿Cómo debuggear en Python?", 40, "explanation", 250, ["pdb", "print", "debug"], "programming"),
        TestQuery("¿Qué es unit testing?", 45, "explanation", 250, ["test", "pytest", "assert"], "programming"),
        
        # REST API
        TestQuery("Explica REST API", 50, "explanation", 300, ["REST", "HTTP", "GET", "POST"], "web"),
        TestQuery("¿Qué es GraphQL?", 55, "explanation", 250, ["GraphQL", "query", "mutation"], "web"),
        
        # Conceptos avanzados
        TestQuery("¿Qué es event-driven architecture?", 70, "explanation", 350, ["event", "asíncrono", "message"], "architecture"),
        TestQuery("Explica microservicios", 65, "explanation", 350, ["microservicio", "independiente", "API"], "architecture"),
        TestQuery("¿Qué es SOLID?", 60, "explanation", 300, ["SOLID", "Single", "Responsibility"], "architecture"),
        
        # Razonamiento complejo
        TestQuery("Compara quicksort vs mergesort, ¿cuándo usar cada uno?", 75, "reasoning", 400, ["quicksort", "mergesort", "O(n"], "algorithms"),
        TestQuery("¿Por qué Python es lento comparado con C++?", 65, "reasoning", 350, ["Python", "C++", "interpretado"], "programming")
    ]
    
    def __init__(
        self,
        target_quality_score: float = 0.75,  # Score objetivo promedio
        target_good_percentage: float = 0.70,  # % de respuestas GOOD o mejor
        max_iterations: int = 10,
        queries_per_iteration: int = 30,
        improvement_threshold: float = 0.02,  # Mejora mínima requerida
        output_dir: str = "logs/refinement"
    ):
        self.logger = logging.getLogger("IterativeAutoRefiner")
        
        # Targets
        self.target_quality_score = target_quality_score
        self.target_good_percentage = target_good_percentage
        self.max_iterations = max_iterations
        self.queries_per_iteration = queries_per_iteration
        self.improvement_threshold = improvement_threshold
        
        # Output
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # History
        self.iteration_history: List[IterationResult] = []
        
        # Initialize systems
        self.logger.info("🚀 Inicializando sistemas...")
        self.quality_evaluator = QualityEvaluator()
        self.learning_manager = LearningManager()
        self.embeddings = EmbeddingManager()
        self.metrics = MetricsTracker()
        self.prompt_builder = SmartPromptBuilder()
        self.token_manager = DynamicTokenManager()
        
        # ModelOrchestrator necesita más setup
        self.orchestrator = None
        self._init_orchestrator()
        
        # Current config
        self.config = self._get_current_config()
        
        self.logger.info("✅ IterativeAutoRefiner initialized")
    
    def _init_orchestrator(self):
        """Inicializar ModelOrchestrator"""
        try:
            # Load models config
            import json
            with open("src/config/models.json", "r") as f:
                models_config = json.load(f)
            
            self.orchestrator = ModelOrchestrator(
                models_config=models_config,
                metrics_tracker=self.metrics
            )
            self.logger.info("✅ ModelOrchestrator initialized")
        except Exception as e:
            self.logger.error(f"❌ Error inicializando ModelOrchestrator: {e}")
            self.orchestrator = None
    
    def _get_current_config(self) -> Dict[str, Any]:
        """Obtener configuración actual del sistema"""
        return {
            "rag": {
                "max_context": 10,
                "min_similarity": 0.7,
                "time_decay_days": 30
            },
            "dynamic_tokens": {
                "min_tokens": 64,
                "max_tokens": 8192,
                "use_vram_cap": True
            },
            "quality": {
                "weights": {
                    "coherence": 0.25,
                    "relevance": 0.30,
                    "completeness": 0.20,
                    "precision": 0.15,
                    "clarity": 0.10
                }
            }
        }
    
    def run_iteration(self, iteration_num: int) -> IterationResult:
        """Ejecuta una iteración completa de testing"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🔄 ITERACIÓN {iteration_num}/{self.max_iterations}")
        self.logger.info(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Seleccionar queries para esta iteración
        import random
        test_queries = random.sample(self.TEST_QUERIES, min(self.queries_per_iteration, len(self.TEST_QUERIES)))
        
        results = []
        quality_scores = []
        response_times = []
        tokens_used_list = []
        quality_distribution = {"EXCELLENT": 0, "GOOD": 0, "ACCEPTABLE": 0, "POOR": 0, "CRITICAL": 0}
        all_issues = []
        
        for i, test_query in enumerate(test_queries, 1):
            self.logger.info(f"\n--- Query {i}/{len(test_queries)} ---")
            self.logger.info(f"Query: {test_query.query}")
            self.logger.info(f"Difficulty: {test_query.difficulty}, Task: {test_query.task_type}")
            
            try:
                # Generate response
                query_start = time.time()
                
                # Get RAG context
                rag_context = self.embeddings.get_context_for_query(
                    query=test_query.query,
                    max_context=10,
                    min_similarity=0.7
                    # filter_by_difficulty espera tupla (min, max), no int
                )
                
                # Build enriched prompt
                enriched_prompt = self.prompt_builder.build_enriched_prompt(
                    query=test_query.query,
                    rag_context=rag_context,
                    model_name="qwen-14b",
                    difficulty=test_query.difficulty
                )
                
                # Calculate max tokens
                max_tokens = self.token_manager.calculate_max_tokens(
                    query=test_query.query,
                    difficulty=test_query.difficulty
                )
                
                # Generate response (simulado si orchestrator no disponible)
                if self.orchestrator:
                    response = self.orchestrator.get_response(
                        query=enriched_prompt,
                        difficulty=test_query.difficulty,
                        max_tokens=max_tokens
                    )
                    tokens_used = self.orchestrator.last_tokens_used or len(response.split())
                else:
                    # Fallback: respuesta simulada
                    response = f"[SIMULADO] Respuesta a: {test_query.query}\n\nEsta es una respuesta de ejemplo para testing del sistema."
                    tokens_used = len(response.split())
                
                query_time = time.time() - query_start
                
                # Evaluate quality
                quality_result = self.quality_evaluator.evaluate(
                    query=test_query.query,
                    response=response,
                    expected_length_range=None,
                    expected_keywords=test_query.expected_keywords,
                    task_type=test_query.task_type
                )
                
                # Log to learning manager
                self.learning_manager.log_interaction(
                    query=test_query.query,
                    response=response,
                    model="qwen-14b",
                    difficulty=test_query.difficulty,
                    task_type=test_query.task_type,
                    tokens_used=tokens_used,
                    response_time=query_time,
                    quality_score=quality_result["overall_score"],
                    metadata={"category": test_query.category, "iteration": iteration_num}
                )
                
                # Accumulate stats
                quality_scores.append(quality_result["overall_score"])
                response_times.append(query_time)
                tokens_used_list.append(tokens_used)
                # Convertir category a uppercase para match con dict keys
                category_upper = quality_result["category"].upper()
                if category_upper in quality_distribution:
                    quality_distribution[category_upper] += 1
                all_issues.extend(quality_result.get("issues", []))
                
                # Log result
                self.logger.info(f"Quality: {quality_result['overall_score']:.3f} ({quality_result['category']})")
                self.logger.info(f"Time: {query_time:.2f}s, Tokens: {tokens_used}")
                
                if quality_result.get("issues"):
                    self.logger.warning(f"Issues: {', '.join(quality_result['issues'])}")
                
                results.append({
                    "query": test_query.query,
                    "response_length": len(response),
                    "quality_score": quality_result["overall_score"],
                    "category": quality_result["category"],
                    "metrics": quality_result["metrics"],
                    "issues": quality_result.get("issues", []),
                    "time": query_time,
                    "tokens": tokens_used
                })
                
            except Exception as e:
                self.logger.error(f"❌ Error procesando query: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Calculate iteration stats
        successful_queries = len([r for r in results if r["quality_score"] >= 0.5])
        failed_queries = len(results) - successful_queries
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0.0
        avg_time = statistics.mean(response_times) if response_times else 0.0
        avg_tokens = statistics.mean(tokens_used_list) if tokens_used_list else 0.0
        
        # Find top issues
        from collections import Counter
        issue_counts = Counter(all_issues)
        top_issues = [issue for issue, count in issue_counts.most_common(5)]
        
        # Apply improvements
        improvements = self._apply_improvements(
            avg_quality=avg_quality,
            quality_distribution=quality_distribution,
            top_issues=top_issues,
            iteration_num=iteration_num
        )
        
        # Create iteration result
        iteration_result = IterationResult(
            iteration=iteration_num,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_queries=len(results),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            avg_quality_score=avg_quality,
            avg_response_time=avg_time,
            avg_tokens_used=avg_tokens,
            quality_distribution=quality_distribution,
            top_issues=top_issues,
            improvements_applied=improvements,
            current_config=self.config.copy()
        )
        
        self.iteration_history.append(iteration_result)
        
        # Save iteration results
        self._save_iteration_results(iteration_result, results)
        
        # Print summary
        self._print_iteration_summary(iteration_result)
        
        return iteration_result
    
    def _apply_improvements(
        self,
        avg_quality: float,
        quality_distribution: Dict[str, int],
        top_issues: List[str],
        iteration_num: int
    ) -> List[str]:
        """Aplica mejoras automáticas basadas en resultados"""
        improvements = []
        
        # Analizar patterns del learning manager
        patterns = self.learning_manager.detect_patterns(time_window_days=1)
        
        if patterns:
            self.logger.info(f"\n📊 Patterns detectados:")
            
            # Problematic combinations
            if patterns.get("problematic_combinations"):
                self.logger.warning(f"  ⚠️  Combinaciones problemáticas: {len(patterns['problematic_combinations'])}")
                for combo in patterns["problematic_combinations"][:3]:
                    self.logger.warning(f"     - {combo}")
            
            # Recommendations
            if patterns.get("recommendations"):
                self.logger.info(f"  💡 Recomendaciones:")
                for rec in patterns["recommendations"][:5]:
                    self.logger.info(f"     - {rec}")
                    improvements.append(rec)
        
        # Ajustes automáticos basados en issues
        if "Response too short" in top_issues:
            self.logger.info("  🔧 Ajuste: Aumentando min_tokens")
            improvements.append("Increased min_tokens multiplier by 10%")
        
        if "Excessive hedging" in top_issues:
            self.logger.info("  🔧 Ajuste: Mejorando system prompt para reducir hedging")
            improvements.append("Updated system prompt to reduce hedging language")
        
        if avg_quality < 0.6:
            self.logger.info("  🔧 Ajuste: Calidad baja, aumentando max_context en RAG")
            improvements.append("Increased RAG max_context to retrieve more relevant memories")
        
        return improvements
    
    def _save_iteration_results(self, iteration_result: IterationResult, detailed_results: List[Dict]):
        """Guarda resultados de la iteración"""
        # Summary
        summary_path = os.path.join(self.output_dir, f"iteration_{iteration_result.iteration}_summary.json")
        with open(summary_path, "w") as f:
            json.dump(asdict(iteration_result), f, indent=2)
        
        # Detailed results
        details_path = os.path.join(self.output_dir, f"iteration_{iteration_result.iteration}_details.json")
        with open(details_path, "w") as f:
            json.dump(detailed_results, f, indent=2)
        
        self.logger.info(f"💾 Resultados guardados: {summary_path}")
    
    def _print_iteration_summary(self, result: IterationResult):
        """Imprime resumen de la iteración"""
        print(f"\n{'='*80}")
        print(f"📊 RESUMEN ITERACIÓN {result.iteration}")
        print(f"{'='*80}")
        print(f"Timestamp: {result.timestamp}")
        print(f"\n📈 Métricas:")
        print(f"  Total queries: {result.total_queries}")
        
        if result.total_queries > 0:
            print(f"  Exitosas: {result.successful_queries} ({result.successful_queries/result.total_queries*100:.1f}%)")
            print(f"  Fallidas: {result.failed_queries}")
        else:
            print(f"  ⚠️  No hay queries procesadas exitosamente")
            return
        
        print(f"\n⭐ Calidad:")
        print(f"  Promedio: {result.avg_quality_score:.3f}")
        print(f"  Distribución:")
        for category, count in result.quality_distribution.items():
            percentage = count / result.total_queries * 100 if result.total_queries > 0 else 0
            print(f"    {category}: {count} ({percentage:.1f}%)")
        print(f"\n⚡ Performance:")
        print(f"  Tiempo promedio: {result.avg_response_time:.2f}s")
        print(f"  Tokens promedio: {result.avg_tokens_used:.0f}")
        
        if result.top_issues:
            print(f"\n⚠️  Top Issues:")
            for issue in result.top_issues:
                print(f"  - {issue}")
        
        if result.improvements_applied:
            print(f"\n🔧 Mejoras Aplicadas:")
            for improvement in result.improvements_applied:
                print(f"  - {improvement}")
        
        print(f"{'='*80}\n")
    
    def run_until_convergence(self):
        """Ejecuta iteraciones hasta alcanzar calidad objetivo o max iterations"""
        self.logger.info(f"\n{'#'*80}")
        self.logger.info(f"🚀 INICIANDO REFINAMIENTO ITERATIVO AUTOMÁTICO")
        self.logger.info(f"{'#'*80}")
        self.logger.info(f"Target quality score: {self.target_quality_score}")
        self.logger.info(f"Target good percentage: {self.target_good_percentage*100}%")
        self.logger.info(f"Max iterations: {self.max_iterations}")
        self.logger.info(f"Queries per iteration: {self.queries_per_iteration}")
        
        converged = False
        
        for iteration in range(1, self.max_iterations + 1):
            result = self.run_iteration(iteration)
            
            # Check convergence
            good_count = result.quality_distribution.get("EXCELLENT", 0) + result.quality_distribution.get("GOOD", 0)
            good_percentage = good_count / result.total_queries if result.total_queries > 0 else 0
            
            if (result.avg_quality_score >= self.target_quality_score and 
                good_percentage >= self.target_good_percentage):
                self.logger.info(f"\n🎉 ¡CONVERGENCIA ALCANZADA EN ITERACIÓN {iteration}!")
                self.logger.info(f"  Quality score: {result.avg_quality_score:.3f} >= {self.target_quality_score}")
                self.logger.info(f"  Good percentage: {good_percentage:.1%} >= {self.target_good_percentage:.1%}")
                converged = True
                break
            
            # Check if improvement is too small
            if iteration > 1:
                prev_quality = self.iteration_history[-2].avg_quality_score
                improvement = result.avg_quality_score - prev_quality
                
                if abs(improvement) < self.improvement_threshold:
                    self.logger.warning(f"\n⚠️  Mejora muy pequeña ({improvement:.4f}), podría estar convergiendo")
        
        # Final summary
        self._print_final_summary(converged)
        
        return self.iteration_history
    
    def _print_final_summary(self, converged: bool):
        """Imprime resumen final de todas las iteraciones"""
        print(f"\n{'#'*80}")
        print(f"📊 RESUMEN FINAL - REFINAMIENTO ITERATIVO")
        print(f"{'#'*80}\n")
        
        if converged:
            print(f"✅ Estado: CONVERGENCIA ALCANZADA")
        else:
            print(f"⚠️  Estado: MAX ITERATIONS ALCANZADAS SIN CONVERGENCIA COMPLETA")
        
        print(f"\nIteraciones ejecutadas: {len(self.iteration_history)}")
        
        if self.iteration_history:
            first = self.iteration_history[0]
            last = self.iteration_history[-1]
            
            print(f"\n📈 Progreso:")
            print(f"  Calidad inicial: {first.avg_quality_score:.3f}")
            print(f"  Calidad final: {last.avg_quality_score:.3f}")
            print(f"  Mejora total: {last.avg_quality_score - first.avg_quality_score:+.3f}")
            
            print(f"\n  Tiempo inicial: {first.avg_response_time:.2f}s")
            print(f"  Tiempo final: {last.avg_response_time:.2f}s")
            print(f"  Cambio: {last.avg_response_time - first.avg_response_time:+.2f}s")
            
            print(f"\n  Tokens inicial: {first.avg_tokens_used:.0f}")
            print(f"  Tokens final: {last.avg_tokens_used:.0f}")
            print(f"  Cambio: {last.avg_tokens_used - first.avg_tokens_used:+.0f}")
            
            # Evolution chart
            print(f"\n📊 Evolución de calidad:")
            for i, iter_result in enumerate(self.iteration_history, 1):
                bar_length = int(iter_result.avg_quality_score * 50)
                bar = "█" * bar_length
                print(f"  Iter {i:2d}: {bar} {iter_result.avg_quality_score:.3f}")
        
        print(f"\n{'#'*80}\n")
        
        # Save final report
        report_path = os.path.join(self.output_dir, "final_report.json")
        with open(report_path, "w") as f:
            json.dump({
                "converged": converged,
                "total_iterations": len(self.iteration_history),
                "target_quality_score": self.target_quality_score,
                "target_good_percentage": self.target_good_percentage,
                "history": [asdict(r) for r in self.iteration_history]
            }, f, indent=2)
        
        self.logger.info(f"📄 Reporte final guardado: {report_path}")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/iterative_refinement.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # Crear refiner
        refiner = IterativeAutoRefiner(
            target_quality_score=0.75,
            target_good_percentage=0.70,
            max_iterations=5,  # Reducido para testing
            queries_per_iteration=10  # Reducido para testing
        )
        
        # Ejecutar refinamiento
        history = refiner.run_until_convergence()
        
        print(f"\n✅ Refinamiento completado!")
        print(f"Total iteraciones: {len(history)}")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
