#!/usr/bin/env python3
"""
Test Suite para Jarvis IA V2
Valida todos los componentes del sistema V2:
- ModelOrchestrator (multi-GPU)
- EmbeddingManager (RAG)
- WhisperHandler (faster-whisper)
- MetricsTracker
- Integración completa
"""

import os
import sys
import logging
import time
from pathlib import Path

# Agregar rutas al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from colorama import Fore, Style, init

init(autoreset=True)

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text.center(60)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

def print_success(text):
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

def print_error(text):
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

def print_warning(text):
    print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")

def print_info(text):
    print(f"{Fore.BLUE}ℹ️  {text}{Style.RESET_ALL}")


class V2TestSuite:
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Componentes V2
        self.orchestrator = None
        self.embeddings = None
        self.whisper = None
        self.metrics = None
    
    def test_gpu_availability(self):
        """Test 1: Verificar disponibilidad de GPUs"""
        print_header("Test 1: GPU Availability")
        
        try:
            import torch
            
            if not torch.cuda.is_available():
                print_error("CUDA no disponible")
                self.results['failed'] += 1
                return False
            
            gpu_count = torch.cuda.device_count()
            print_success(f"CUDA disponible con {gpu_count} GPU(s)")
            
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                vram_gb = props.total_memory / (1024**3)
                print_info(f"GPU {i}: {props.name} | {vram_gb:.1f} GB VRAM")
            
            self.results['passed'] += 1
            return True
            
        except ImportError:
            print_error("PyTorch no instalado")
            self.results['failed'] += 1
            return False
        except Exception as e:
            print_error(f"Error: {e}")
            self.results['failed'] += 1
            return False
    
    def test_orchestrator_init(self):
        """Test 2: Inicializar ModelOrchestrator"""
        print_header("Test 2: ModelOrchestrator Initialization")
        
        try:
            from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
            
            config_path = PROJECT_ROOT / "src/config/models_v2.json"
            if not config_path.exists():
                print_warning(f"Configuración no encontrada: {config_path}")
                print_info("Creando configuración por defecto...")
            
            self.orchestrator = ModelOrchestrator(config_path=str(config_path))
            print_success("ModelOrchestrator inicializado correctamente")
            
            # Obtener estadísticas
            stats = self.orchestrator.get_stats()
            print_info(f"GPUs detectadas: {stats['gpu_count']}")
            print_info(f"Modelos cargados: {stats['models_loaded']}")
            print_info(f"Modelos disponibles: {len(stats['available_models'])}")
            
            for model_id in stats['available_models'][:3]:  # Mostrar primeros 3
                print_info(f"  - {model_id}")
            
            self.results['passed'] += 1
            return True
            
        except ImportError as e:
            print_error(f"ModelOrchestrator no disponible: {e}")
            self.results['skipped'] += 1
            return False
        except Exception as e:
            print_error(f"Error al inicializar: {e}")
            self.results['failed'] += 1
            return False
    
    def test_orchestrator_query(self):
        """Test 3: Consulta simple con ModelOrchestrator"""
        print_header("Test 3: ModelOrchestrator Query")
        
        if not self.orchestrator:
            print_warning("Saltando: Orchestrator no inicializado")
            self.results['skipped'] += 1
            return False
        
        try:
            test_queries = [
                ("Hola, ¿cómo estás?", 20),  # Fácil
                ("¿Cuál es la capital de Francia?", 40),  # Media
                ("Explica la teoría de la relatividad", 80)  # Difícil
            ]
            
            for query, difficulty in test_queries:
                print_info(f"Query (difficulty={difficulty}): {query}")
                
                start_time = time.time()
                response, model_used = self.orchestrator.get_response(
                    query=query,
                    difficulty=difficulty
                )
                latency = time.time() - start_time
                
                print_success(f"Modelo usado: {model_used}")
                print_success(f"Latencia: {latency:.2f}s")
                print_info(f"Respuesta: {response[:100]}...")
                print()
            
            self.results['passed'] += 1
            return True
            
        except Exception as e:
            print_error(f"Error en query: {e}")
            self.results['failed'] += 1
            return False
    
    def test_embeddings_init(self):
        """Test 4: Inicializar EmbeddingManager (RAG)"""
        print_header("Test 4: EmbeddingManager Initialization")
        
        try:
            from src.modules.embeddings.embedding_manager import EmbeddingManager
            
            # Intentar con GPU primero
            try:
                self.embeddings = EmbeddingManager(
                    model_name="models/embeddings/bge-m3",
                    device="cuda:1",
                    chroma_path="vectorstore/chromadb_test"
                )
                print_success("EmbeddingManager inicializado en GPU1")
            except Exception as e:
                print_warning(f"GPU fallback a CPU: {e}")
                self.embeddings = EmbeddingManager(
                    device="cpu",
                    chroma_path="vectorstore/chromadb_test"
                )
                print_success("EmbeddingManager inicializado en CPU")
            
            stats = self.embeddings.get_statistics()
            print_info(f"Total memorias: {stats['total_memories']}")
            print_info(f"Backend: {stats.get('device', 'unknown')}")
            
            self.results['passed'] += 1
            return True
            
        except ImportError as e:
            print_error(f"EmbeddingManager no disponible: {e}")
            self.results['skipped'] += 1
            return False
        except Exception as e:
            print_error(f"Error al inicializar: {e}")
            self.results['failed'] += 1
            return False
    
    def test_embeddings_search(self):
        """Test 5: Sistema RAG - Añadir y buscar memorias"""
        print_header("Test 5: RAG System - Add & Search")
        
        if not self.embeddings:
            print_warning("Saltando: Embeddings no inicializados")
            self.results['skipped'] += 1
            return False
        
        try:
            # Agregar memorias de prueba
            test_memories = [
                {
                    "query": "¿Cuál es mi color favorito?",
                    "response": "Tu color favorito es el azul marino",
                    "model": "test",
                    "difficulty": 20
                },
                {
                    "query": "¿Qué lenguaje de programación prefiero?",
                    "response": "Prefieres Python para IA y JavaScript para web",
                    "model": "test",
                    "difficulty": 30
                },
                {
                    "query": "¿Cuál es mi película favorita?",
                    "response": "Tu película favorita es Inception",
                    "model": "test",
                    "difficulty": 25
                }
            ]
            
            print_info("Agregando memorias de prueba...")
            for mem in test_memories:
                self.embeddings.add_interaction(**mem)
            print_success(f"{len(test_memories)} memorias agregadas")
            
            # Buscar
            search_queries = [
                "color preferido",
                "programación",
                "cine"
            ]
            
            for search_query in search_queries:
                print_info(f"Buscando: '{search_query}'")
                results = self.embeddings.search_memory(search_query, n_results=1)
                
                if results['documents'] and results['documents'][0]:
                    doc = results['documents'][0][0]
                    distance = results['distances'][0][0] if results['distances'] else 'N/A'
                    print_success(f"Encontrado (distance={distance:.3f}): {doc[:80]}...")
                else:
                    print_warning("No se encontraron resultados")
                print()
            
            # Estadísticas finales
            stats = self.embeddings.get_statistics()
            print_success(f"Total memorias en sistema: {stats['total_memories']}")
            
            self.results['passed'] += 1
            return True
            
        except Exception as e:
            print_error(f"Error en RAG: {e}")
            self.results['failed'] += 1
            return False
    
    def test_whisper_init(self):
        """Test 6: Inicializar WhisperHandler"""
        print_header("Test 6: WhisperHandler Initialization")
        
        try:
            from src.modules.voice.whisper_handler import WhisperHandler
            
            model_path = PROJECT_ROOT / "models/whisper/large-v3-turbo-ct2"
            
            if not model_path.exists():
                print_warning(f"Modelo Whisper no encontrado: {model_path}")
                print_info("Puedes descargarlo con: python scripts/download_models.py --category whisper")
                self.results['skipped'] += 1
                return False
            
            try:
                self.whisper = WhisperHandler(
                    model_path=str(model_path),
                    device="cuda",
                    device_index=1,
                    compute_type="int8"
                )
                print_success("WhisperHandler inicializado en GPU1")
            except Exception as e:
                print_warning(f"GPU fallback a CPU: {e}")
                self.whisper = WhisperHandler(device="cpu")
                print_success("WhisperHandler inicializado en CPU")
            
            info = self.whisper.get_info()
            print_info(f"Device: {info['device']}")
            print_info(f"Backend: {info['backend']}")
            print_info(f"Compute type: {info['compute_type']}")
            
            # Listar idiomas soportados
            languages = self.whisper.get_supported_languages()
            print_info(f"Idiomas soportados: {len(languages)}")
            print_info(f"Español incluido: {'es' in languages}")
            
            self.results['passed'] += 1
            return True
            
        except ImportError as e:
            print_error(f"WhisperHandler no disponible: {e}")
            self.results['skipped'] += 1
            return False
        except Exception as e:
            print_error(f"Error al inicializar: {e}")
            self.results['failed'] += 1
            return False
    
    def test_metrics_tracker(self):
        """Test 7: MetricsTracker"""
        print_header("Test 7: MetricsTracker")
        
        try:
            from src.utils.metrics_tracker import MetricsTracker, QueryTimer
            
            self.metrics = MetricsTracker(
                log_path="logs/test_metrics.jsonl",
                enable_gpu_monitoring=True
            )
            print_success("MetricsTracker inicializado")
            
            # Simular queries
            test_queries = [
                ("Test query 1", "llama-8b", 30, 0.5),
                ("Test query 2", "qwen-32b", 60, 1.2),
                ("Test query 3", "gpt-4o-mini", 80, 0.8),
            ]
            
            for query, model, difficulty, latency in test_queries:
                time.sleep(latency)  # Simular latencia
                
                self.metrics.track_query(
                    query=query,
                    model=model,
                    difficulty=difficulty,
                    latency=latency,
                    tokens={"prompt": 50, "completion": 100},
                    cost=0.001 if "gpt" in model else 0.0,
                    success=True
                )
            
            print_success(f"{len(test_queries)} queries registradas")
            
            # Mostrar estadísticas
            print_info("Estadísticas de sesión:")
            self.metrics.print_stats()
            
            self.results['passed'] += 1
            return True
            
        except ImportError as e:
            print_error(f"MetricsTracker no disponible: {e}")
            self.results['skipped'] += 1
            return False
        except Exception as e:
            print_error(f"Error en metrics: {e}")
            self.results['failed'] += 1
            return False
    
    def test_integration(self):
        """Test 8: Integración completa V2"""
        print_header("Test 8: Integration Test")
        
        if not all([self.orchestrator, self.embeddings, self.metrics]):
            print_warning("Saltando: No todos los componentes disponibles")
            self.results['skipped'] += 1
            return False
        
        try:
            test_query = "¿Qué sabes sobre mis preferencias de programación?"
            difficulty = 50
            
            print_info(f"Query integrada: {test_query}")
            
            # 1. Buscar contexto en RAG
            rag_context = self.embeddings.get_context_for_query(test_query, max_context=2)
            print_success(f"Contexto RAG obtenido: {len(rag_context)} caracteres")
            
            # 2. Enriquecer query
            enriched_query = test_query
            if rag_context:
                enriched_query = f"Contexto:\n{rag_context}\n\nPregunta: {test_query}"
            
            # 3. Consultar con métricas
            with QueryTimer(self.metrics, test_query, "auto", difficulty):
                response, model_used = self.orchestrator.get_response(
                    query=enriched_query,
                    difficulty=difficulty
                )
            
            print_success(f"Modelo usado: {model_used}")
            print_info(f"Respuesta: {response[:150]}...")
            
            # 4. Guardar interacción en RAG
            self.embeddings.add_interaction(
                query=test_query,
                response=response,
                model=model_used,
                difficulty=difficulty
            )
            print_success("Interacción guardada en RAG")
            
            # 5. Verificar métricas
            stats = self.metrics.get_session_stats()
            print_info(f"Total queries: {stats['total_queries']}")
            print_info(f"Latencia promedio: {stats['average_latency']:.2f}s")
            
            self.results['passed'] += 1
            return True
            
        except Exception as e:
            print_error(f"Error en integración: {e}")
            self.results['failed'] += 1
            return False
    
    def print_summary(self):
        """Mostrar resumen de tests"""
        print_header("Test Summary")
        
        total = sum(self.results.values())
        passed_pct = (self.results['passed'] / total * 100) if total > 0 else 0
        
        print(f"{Fore.GREEN}Passed:  {self.results['passed']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed:  {self.results['failed']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Skipped: {self.results['skipped']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Total:   {total}{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Success Rate: {passed_pct:.1f}%{Style.RESET_ALL}\n")
        
        if self.results['failed'] == 0:
            print_success("🎉 Todos los tests pasaron correctamente!")
        elif self.results['passed'] > self.results['failed']:
            print_warning("⚠️  Algunos tests fallaron, revisa los errores")
        else:
            print_error("❌ La mayoría de tests fallaron, revisa la instalación")
    
    def cleanup(self):
        """Limpiar recursos"""
        print_info("Limpiando recursos...")
        
        if self.orchestrator:
            del self.orchestrator
        
        if self.embeddings:
            del self.embeddings
        
        if self.whisper:
            del self.whisper
        
        if self.metrics:
            del self.metrics
        
        print_success("Cleanup completado")


def main():
    """Ejecutar suite de tests"""
    print_header("Jarvis IA V2 - Test Suite")
    print_info(f"Directorio de proyecto: {PROJECT_ROOT}")
    print_info(f"Python: {sys.version.split()[0]}")
    print()
    
    suite = V2TestSuite()
    
    try:
        # Tests de infraestructura
        suite.test_gpu_availability()
        
        # Tests de componentes
        suite.test_orchestrator_init()
        if suite.orchestrator:
            suite.test_orchestrator_query()
        
        suite.test_embeddings_init()
        if suite.embeddings:
            suite.test_embeddings_search()
        
        suite.test_whisper_init()
        suite.test_metrics_tracker()
        
        # Test de integración
        suite.test_integration()
        
    except KeyboardInterrupt:
        print_warning("\nTests interrumpidos por el usuario")
    except Exception as e:
        print_error(f"Error fatal: {e}")
    finally:
        suite.cleanup()
        suite.print_summary()


if __name__ == "__main__":
    main()
