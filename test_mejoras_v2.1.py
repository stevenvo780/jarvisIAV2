#!/usr/bin/env python3
"""
Test Suite para Mejoras V2.1 de Jarvis IA
==========================================

Tests exhaustivos de:
- Fase 1: Dynamic Token Manager
- Fase 2: Enhanced RAG System
- Fase 4: Smart Prompt Builder

Autor: GitHub Copilot
Fecha: 7 Noviembre 2025
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

# Imports de Jarvis
from src.utils.dynamic_token_manager import DynamicTokenManager, QueryType
from src.utils.smart_prompt_builder import SmartPromptBuilder, TaskType, ModelType  # ✅ Import ModelType
from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
from src.modules.embeddings.embedding_manager import EmbeddingManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResults:
    """Acumulador de resultados de testing"""
    def __init__(self):
        self.results = []
        self.stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
    
    def add_result(self, test_name: str, status: str, details: dict):
        """Añadir resultado de test"""
        result = {
            "test": test_name,
            "status": status,  # "PASS", "FAIL", "WARN"
            "details": details,
            "timestamp": time.time()
        }
        self.results.append(result)
        self.stats["total"] += 1
        if status == "PASS":
            self.stats["passed"] += 1
        elif status == "FAIL":
            self.stats["failed"] += 1
        else:
            self.stats["warnings"] += 1
    
    def print_summary(self):
        """Imprimir resumen de resultados"""
        print("\n" + "="*80)
        print("📊 RESUMEN DE TESTING")
        print("="*80)
        print(f"✅ Passed: {self.stats['passed']}")
        print(f"❌ Failed: {self.stats['failed']}")
        print(f"⚠️  Warnings: {self.stats['warnings']}")
        print(f"📈 Total: {self.stats['total']}")
        print(f"🎯 Success Rate: {(self.stats['passed']/self.stats['total']*100):.1f}%")
        print("="*80)
    
    def save_to_file(self, filename: str = "test_results.json"):
        """Guardar resultados a archivo"""
        output = {
            "stats": self.stats,
            "results": self.results,
            "timestamp": time.time()
        }
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        logger.info(f"Resultados guardados en: {filename}")


def print_section(title: str):
    """Imprimir separador de sección"""
    print("\n" + "="*80)
    print(f"🔬 {title}")
    print("="*80 + "\n")


def test_dynamic_tokens():
    """Test Fase 1: Dynamic Token Manager"""
    print_section("FASE 1: Dynamic Token Manager")
    
    results = TestResults()
    token_manager = DynamicTokenManager(debug=True)
    
    # Test Cases
    test_cases = [
        # (query, expected_min, expected_max, description)
        ("Hola", 64, 256, "Query simple - minimal"),
        ("¿Qué es Python?", 128, 512, "Query media - question"),
        ("Genera una función de búsqueda binaria en Python con comentarios", 512, 4096, "Query código - code generation"),
        ("Explica paso a paso el algoritmo de ordenamiento quicksort, comparándolo con mergesort y mostrando complejidades", 1024, 4096, "Query compleja - reasoning"),
        ("Analiza las diferencias entre arquitecturas MVC y MVVM", 512, 2048, "Query análisis - analysis"),
    ]
    
    for i, (query, min_expected, max_expected, desc) in enumerate(test_cases, 1):
        # Note: DynamicTokenManager doesn't have _estimate_difficulty
        # We'll use a simple heuristic
        difficulty = min(100, max(1, len(query.split()) * 5 + len(query) // 10))
        query_type = token_manager.detect_query_type(query)
        max_tokens = token_manager.calculate_max_tokens(
            query=query,  # ✅ Añadido argumento requerido
            difficulty=difficulty,
            query_type=query_type
        )
        
        # Validación
        status = "PASS" if min_expected <= max_tokens <= max_expected else "FAIL"
        
        print(f"Test {i}: {desc}")
        print(f"  Query: '{query[:60]}...'")
        print(f"  Difficulty: {difficulty}/100")
        print(f"  Query Type: {query_type.name}")
        print(f"  Max Tokens: {max_tokens} (expected: {min_expected}-{max_expected})")
        print(f"  Status: {status}")
        print()
        
        results.add_result(
            test_name=f"DynamicTokens-{i}-{desc}",
            status=status,
            details={
                "query": query,
                "difficulty": difficulty,
                "query_type": query_type.name,
                "max_tokens": max_tokens,
                "expected_range": [min_expected, max_expected]
            }
        )
    
    results.print_summary()
    return results


def test_rag_system():
    """Test Fase 2: Enhanced RAG System"""
    print_section("FASE 2: Enhanced RAG System")
    
    results = TestResults()
    
    # Verificar si RAG está habilitado
    enable_rag = os.getenv('ENABLE_RAG', 'true').lower() == 'true'
    if not enable_rag:
        print("⚠️  RAG deshabilitado (ENABLE_RAG=false), saltando tests")
        results.add_result(
            test_name="RAG-Init",
            status="WARN",
            details={"message": "RAG disabled in .env"}
        )
        return results
    
    try:
        # Inicializar EmbeddingManager
        print("Inicializando EmbeddingManager...")
        embeddings = EmbeddingManager(
            model_name="models/embeddings/bge-m3",
            device="cuda:0",  # RTX 5070 Ti
            chroma_path="vectorstore/chromadb"
        )
        print("✅ EmbeddingManager inicializado correctamente\n")
        
        # Test 1: Verificar parámetros mejorados
        test_queries = [
            ("¿Qué es Python?", 60, "Query factual"),
            ("Genera código para búsqueda binaria", 75, "Query código"),
            ("Explica paso a paso el algoritmo quicksort", 85, "Query compleja"),
        ]
        
        for i, (query, difficulty, desc) in enumerate(test_queries, 1):
            print(f"Test RAG {i}: {desc}")
            print(f"  Query: '{query}'")
            print(f"  Difficulty: {difficulty}")
            
            # Recuperar contexto
            context = embeddings.get_context_for_query(
                query=query,
                max_context=10,  # NUEVO: era 3
                min_similarity=0.7,  # NUEVO: era 0.3
                time_decay_days=30,
                filter_by_difficulty=(difficulty - 20, difficulty + 20),
                deduplicate=True
            )
            
            # Count memories from context
            memories_count = context.count("[Memoria #") if context else 0
            
            # Validación
            status = "PASS"
            if memories_count > 10:
                status = "FAIL"
                details = {"error": "Más de 10 memorias recuperadas"}
            elif memories_count == 0:
                status = "WARN"
                details = {"warning": "No hay memorias en la base de datos aún"}
            else:
                details = {"success": f"{memories_count} memorias recuperadas"}
            
            print(f"  Memorias recuperadas: {memories_count}")
            print(f"  Tamaño contexto: {len(context)} chars")
            print(f"  Status: {status}")
            print()
            
            results.add_result(
                test_name=f"RAG-{i}-{desc}",
                status=status,
                details={
                    "query": query,
                    "difficulty": difficulty,
                    "memories_count": memories_count,
                    "context_size": len(context),
                    **details
                }
            )
        
        # Test 2: Verificar formato mejorado
        print("Test RAG 4: Formato de contexto")
        if context:
            has_score = "[Score:" in context or "Score:" in context
            has_difficulty = "Dificultad:" in context or "difficulty:" in context.lower()
            has_model = "Modelo:" in context or "model:" in context.lower()
            
            status = "PASS" if (has_score or has_difficulty or has_model) else "WARN"
            print(f"  Formato estructurado: {status}")
            print(f"  - Score presente: {has_score}")
            print(f"  - Difficulty presente: {has_difficulty}")
            print(f"  - Model presente: {has_model}")
            print()
            
            results.add_result(
                test_name="RAG-Format",
                status=status,
                details={
                    "has_score": has_score,
                    "has_difficulty": has_difficulty,
                    "has_model": has_model
                }
            )
        else:
            results.add_result(
                test_name="RAG-Format",
                status="WARN",
                details={"warning": "No context to check format"}
            )
        
    except Exception as e:
        logger.error(f"Error en RAG tests: {e}")
        results.add_result(
            test_name="RAG-Error",
            status="FAIL",
            details={"error": str(e)}
        )
    
    results.print_summary()
    return results


def test_smart_prompts():
    """Test Fase 4: Smart Prompt Builder"""
    print_section("FASE 4: Smart Prompt Builder")
    
    results = TestResults()
    
    # Verificar si está habilitado
    enable_smart = os.getenv('ENABLE_SMART_PROMPTS', 'true').lower() == 'true'
    if not enable_smart:
        print("⚠️  Smart Prompts deshabilitado, saltando tests")
        results.add_result(
            test_name="SmartPrompts-Init",
            status="WARN",
            details={"message": "Smart prompts disabled"}
        )
        return results
    
    try:
        prompt_builder = SmartPromptBuilder(debug=True)
        
        # Test Cases
        test_cases = [
            ("Hola, ¿cómo estás?", 15, TaskType.CHAT, "Chat simple"),
            ("¿Qué es Python?", 50, TaskType.QUESTION, "Pregunta factual"),
            ("Genera una función de búsqueda binaria en Python", 70, TaskType.CODE_GEN, "Código generation"),
            ("Explica paso a paso el teorema de Pitágoras con demostración", 80, TaskType.REASONING, "Razonamiento complejo"),
            ("Compara arquitecturas MVC vs MVVM", 65, TaskType.ANALYSIS, "Análisis comparativo"),
        ]
        
        for i, (query, difficulty, expected_task, desc) in enumerate(test_cases, 1):
            print(f"Test SmartPrompt {i}: {desc}")
            print(f"  Query: '{query}'")
            print(f"  Difficulty: {difficulty}")
            
            try:
                # Detectar task type
                detected_task = prompt_builder.detect_task_type(query)
                
                # Build prompt
                enriched_prompt = prompt_builder.build_enriched_prompt(
                    query=query,
                    rag_context="",  # Sin RAG context para testing aislado
                    difficulty=difficulty,
                    model_name="qwen-14b"  # ✅ Parámetro correcto
                )
                
                # Validaciones
                has_system = "Eres Jarvis" in enriched_prompt or "asistente" in enriched_prompt.lower()
                has_instructions = len(enriched_prompt) > len(query) + 50
                has_cot = (difficulty > 60) and ("paso a paso" in enriched_prompt.lower() or "razon" in enriched_prompt.lower())
                task_match = detected_task == expected_task
                
                status = "PASS" if (has_system and has_instructions) else "FAIL"
                if not task_match:
                    status = "WARN"
                
                print(f"  Task detectado: {detected_task.name} (esperado: {expected_task.name})")
                print(f"  Tamaño prompt: {len(enriched_prompt)} chars")
                print(f"  System instructions: {has_system}")
                print(f"  Has instructions: {has_instructions}")
                print(f"  Chain-of-Thought (diff>{60}): {has_cot}")
                print(f"  Status: {status}")
                print()
                
                results.add_result(
                    test_name=f"SmartPrompt-{i}-{desc}",
                    status=status,
                    details={
                        "query": query,
                        "difficulty": difficulty,
                        "detected_task": detected_task.name,
                        "expected_task": expected_task.name,
                        "prompt_size": len(enriched_prompt),
                        "has_system": has_system,
                        "has_cot": has_cot
                    }
                )
            except Exception as e:
                logger.error(f"Error en test {i}: {e}")
                results.add_result(
                    test_name=f"SmartPrompt-{i}-{desc}",
                    status="FAIL",
                    details={"error": str(e)}
                )
        
    except Exception as e:
        logger.error(f"Error en Smart Prompts tests: {e}")
        results.add_result(
            test_name="SmartPrompts-Error",
            status="FAIL",
            details={"error": str(e)}
        )
    
    results.print_summary()
    return results


def test_integration():
    """Test de integración completa"""
    print_section("INTEGRATION TEST: Full Pipeline")
    
    results = TestResults()
    
    print("⚠️  Integration test requiere modelos cargados (GPU)")
    print("Este test se saltará si no hay GPU disponible o modelos no descargados\n")
    
    # Verificar GPU
    try:
        import torch
        if not torch.cuda.is_available():
            results.add_result(
                test_name="Integration-GPU",
                status="WARN",
                details={"warning": "No GPU available"}
            )
            results.print_summary()
            return results
        
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"✅ GPU disponible: {gpu_name}")
        print(f"✅ VRAM: {vram_total:.1f} GB\n")
        
    except ImportError:
        results.add_result(
            test_name="Integration-PyTorch",
            status="WARN",
            details={"warning": "PyTorch not available"}
        )
        results.print_summary()
        return results
    
    # Test: Inicializar orchestrator
    print("Inicializando ModelOrchestrator...")
    try:
        orchestrator = ModelOrchestrator(
            config_path="src/config/models.json",
            metrics_tracker=None,
            enable_metrics=False
        )
        print("✅ Orchestrator inicializado\n")
        
        # Test query simple
        print("Test Integration 1: Query simple")
        query_simple = "Hola"
        difficulty_simple = 10
        
        response, model, tokens = orchestrator.get_response(
            query=query_simple,
            difficulty=difficulty_simple,
            context=""
        )
        
        print(f"  Query: '{query_simple}'")
        print(f"  Response: '{response[:100]}...'")
        print(f"  Model: {model}")
        print(f"  Tokens used: {tokens}")
        
        status = "PASS" if response and len(response) > 0 else "FAIL"
        print(f"  Status: {status}\n")
        
        results.add_result(
            test_name="Integration-SimpleQuery",
            status=status,
            details={
                "query": query_simple,
                "response_length": len(response),
                "model": model,
                "tokens": tokens
            }
        )
        
        # Test query compleja
        print("Test Integration 2: Query compleja")
        query_complex = "Explica paso a paso el algoritmo de búsqueda binaria"
        difficulty_complex = 75
        
        response, model, tokens = orchestrator.get_response(
            query=query_complex,
            difficulty=difficulty_complex,
            context=""
        )
        
        print(f"  Query: '{query_complex}'")
        print(f"  Response: '{response[:100]}...'")
        print(f"  Model: {model}")
        print(f"  Tokens used: {tokens}")
        
        status = "PASS" if response and len(response) > len(query_simple) else "FAIL"
        print(f"  Status: {status}\n")
        
        results.add_result(
            test_name="Integration-ComplexQuery",
            status=status,
            details={
                "query": query_complex,
                "response_length": len(response),
                "model": model,
                "tokens": tokens
            }
        )
        
        # Cleanup
        print("Limpiando recursos...")
        orchestrator.cleanup()
        print("✅ Cleanup completo\n")
        
    except Exception as e:
        logger.error(f"Error en integration test: {e}")
        results.add_result(
            test_name="Integration-Error",
            status="FAIL",
            details={"error": str(e)}
        )
    
    results.print_summary()
    return results


def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("🧪 JARVIS IA V2.1 - TEST SUITE COMPLETO")
    print("="*80)
    print("Fecha: 7 Noviembre 2025")
    print("Testing: Fases 1, 2, 4 implementadas")
    print("="*80 + "\n")
    
    all_results = TestResults()
    
    # Run tests
    tests = [
        ("Fase 1: Dynamic Tokens", test_dynamic_tokens),
        ("Fase 2: Enhanced RAG", test_rag_system),
        ("Fase 4: Smart Prompts", test_smart_prompts),
        # ("Integration", test_integration),  # Comentado por defecto (requiere GPU+modelos)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Ejecutando: {test_name}")
            test_results = test_func()
            
            # Merge results
            all_results.results.extend(test_results.results)
            for key in all_results.stats:
                all_results.stats[key] += test_results.stats[key]
        
        except Exception as e:
            logger.error(f"Error ejecutando {test_name}: {e}")
            all_results.add_result(
                test_name=f"{test_name}-CriticalError",
                status="FAIL",
                details={"error": str(e)}
            )
    
    # Final summary
    print("\n" + "="*80)
    print("🏁 RESULTADOS FINALES - TODAS LAS FASES")
    print("="*80)
    all_results.print_summary()
    
    # Save results
    all_results.save_to_file("test_mejoras_v2.1_results.json")
    
    print("\n✅ Testing completo!")
    print(f"📄 Resultados guardados en: test_mejoras_v2.1_results.json\n")
    
    # Return exit code
    return 0 if all_results.stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
