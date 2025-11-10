#!/usr/bin/env python3
import os
import sys
import argparse

# Parse args PRIMERO para detectar --debug ANTES de imports
parser = argparse.ArgumentParser(description='Jarvis AI Assistant')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
args, _ = parser.parse_known_args()

# Setear variable de entorno para otros módulos
if args.debug:
    os.environ['JARVIS_DEBUG'] = '1'

# Configurar supresión de logs ANTES de cualquier import
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

# Importar y configurar supresión temprano
from src.utils.log_suppressor import setup_clean_terminal
setup_clean_terminal()

import time
import logging
import threading
from queue import Queue, Empty
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

from src.utils.error_handler import setup_logging
from src.utils.audio_utils import AudioEffects
from src.utils.jarvis_state import JarvisState
from src.utils.smart_prompt_builder import SmartPromptBuilder  # NUEVO
from src.utils.quality_evaluator import QualityEvaluator  # NUEVO Fase 5
from modules.text.terminal_manager import TerminalManager
from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
from src.modules.embeddings.embedding_manager import EmbeddingManager
from src.modules.learning.learning_manager import LearningManager  # NUEVO Fase 3
from src.modules.voice.whisper_handler import WhisperHandler
from src.utils.metrics_tracker import MetricsTracker, QueryTimer
from modules.system_monitor import SystemMonitor
from src.modules.text.text_handler import TextHandler
from src.modules.voice.audio_handler import AudioHandler
from src.modules.voice.tts_manager import TTSManager
from src.modules.storage_manager import StorageManager
from modules.actions import Actions
from modules.system.command_manager import CommandManager
from src.api.healthcheck import start_healthcheck_api  # Quick Win 6
from src.metrics import start_metrics_collector_background  # Quick Win 7

setup_logging()

class Jarvis:
    def __init__(self):
        # Thread-safe state management
        self.state = JarvisState(
            running=True,
            voice_active=False,
            listening_active=False,
            error_count=0,
            max_errors=5
        )
        self.input_queue = Queue()
        self.executor = ThreadPoolExecutor(max_workers=2)
        load_dotenv()
        try:
            self.terminal = TerminalManager()
            self.terminal.print_header("Starting Jarvis AI Assistant (Multi-GPU + RAG)")
            
            self.system_monitor = SystemMonitor()
            self.terminal.print_success("System monitor initialized")
            
            # TTS conditional initialization
            enable_tts = os.getenv('ENABLE_TTS', 'true').lower() == 'true'
            if enable_tts:
                self._initialize_tts()
                self.terminal.print_success("TTS initialized")
            else:
                self.tts = None
                self.terminal.print_status("TTS disabled (ENABLE_TTS=false)")
            
            self.storage = StorageManager()
            self.terminal.print_success("Storage initialized")
            
            # Audio effects conditional initialization
            enable_audio_effects = os.getenv('ENABLE_AUDIO_EFFECTS', 'true').lower() == 'true'
            if enable_audio_effects:
                self.audio_effects = AudioEffects()
                self.terminal.print_success("Audio effects initialized")
            else:
                self.audio_effects = None
                self.terminal.print_status("Audio effects disabled (ENABLE_AUDIO_EFFECTS=false)")
            
            # Inicializar métricas y monitoreo
            self.metrics = MetricsTracker(
                log_path="logs/metrics.jsonl",
                enable_gpu_monitoring=True
            )
            self.terminal.print_success("Metrics tracker initialized")
            
            # Inicializar embeddings/RAG
            enable_rag = os.getenv('ENABLE_RAG', 'true').lower() == 'true'
            if enable_rag:
                try:
                    self.embeddings = EmbeddingManager(
                        model_name="models/embeddings/bge-m3",
                        device="cpu",  # CPU mode to avoid CUDA OOM
                        chroma_path="vectorstore/chromadb"
                    )
                    self.terminal.print_success("Embedding system (RAG) initialized")
                except Exception as e:
                    self.terminal.print_warning(f"Embeddings disabled: {e}")
                    self.embeddings = None
            else:
                self.terminal.print_status("RAG/Embeddings disabled (ENABLE_RAG=false)")
                self.embeddings = None
            
            # Inicializar SmartPromptBuilder para prompt engineering avanzado
            enable_smart_prompts = os.getenv('ENABLE_SMART_PROMPTS', 'true').lower() == 'true'
            if enable_smart_prompts:
                self.prompt_builder = SmartPromptBuilder(debug=False)
                self.terminal.print_success("SmartPromptBuilder initialized")
            else:
                self.prompt_builder = None
                self.terminal.print_status("SmartPromptBuilder disabled")
            
            # Inicializar Learning Manager (Fase 3)
            enable_learning = os.getenv('ENABLE_LEARNING', 'true').lower() == 'true'
            if enable_learning:
                self.learning_manager = LearningManager(
                    log_dir="logs/learning",
                    enable_auto_tuning=True,
                    debug=False
                )
                self.terminal.print_success("LearningManager initialized")
            else:
                self.learning_manager = None
                self.terminal.print_status("LearningManager disabled")
            
            # Inicializar Quality Evaluator (Fase 5)
            enable_quality = os.getenv('ENABLE_QUALITY_EVAL', 'true').lower() == 'true'
            if enable_quality:
                self.quality_evaluator = QualityEvaluator(
                    log_file="logs/quality_evaluations.jsonl",
                    enable_detailed_logging=True,
                    debug=False
                )
                self.terminal.print_success("QualityEvaluator initialized")
            else:
                self.quality_evaluator = None
                self.terminal.print_status("QualityEvaluator disabled")
            
            self.text_handler = None
            self.command_manager = None
            self.model_manager = None
            self.orchestrator = None
            self.actions = None
            
            self._initialize_llm()
            self.terminal.print_success("LLM system initialized")
            
            self._async_audio_init()
            self.terminal.print_success("Voice system initialized")
            
            self._initialize_actions()
            self.terminal.print_success("Actions initialized")
            
            self.text_handler = TextHandler(
                terminal_manager=self.terminal,
                input_queue=self.input_queue,
                actions=self.actions,
                embeddings=self.embeddings
            )
            self.terminal.print_success("Text handler initialized")
        
            self.terminal.print_header("Initializing Jarvis")
            
            # Mostrar estadísticas
            if hasattr(self, 'orchestrator'):
                stats = self.orchestrator.get_stats()
                self.terminal.print_success(f"GPUs: {stats['gpu_count']} | Models loaded: {stats['models_loaded']}")
            
            self.terminal.print_status("Jarvis Text Interface - Escribe 'help' para ver los comandos")
            self.terminal.update_prompt_state('NEUTRAL')
            if self.audio_effects:
                self.audio_effects.play('startup')
            
            # Quick Win 6: Iniciar Health API en background
            enable_health_api = os.getenv('ENABLE_HEALTH_API', 'true').lower() == 'true'
            if enable_health_api:
                health_port = int(os.getenv('HEALTH_API_PORT', '8080'))
                self.health_api = start_healthcheck_api(
                    jarvis_instance=self,
                    port=health_port,
                    background=True
                )
                self.terminal.print_success(f"Health API running on port {health_port}")
                
                # Quick Win 7: Iniciar Metrics Collector en background
                enable_metrics = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
                if enable_metrics:
                    metrics_interval = int(os.getenv('METRICS_INTERVAL', '15'))
                    start_metrics_collector_background(
                        jarvis_instance=self,
                        interval_seconds=metrics_interval
                    )
                    self.terminal.print_success(f"Metrics collector running (interval={metrics_interval}s)")
            else:
                self.health_api = None
                self.terminal.print_status("Health API disabled (ENABLE_HEALTH_API=false)")
        except Exception as e:
            if hasattr(self, 'audio_effects') and self.audio_effects:
                self.audio_effects.play('error')
            self.terminal.print_error(f"Initialization error: {e}")
            sys.exit(1)


    def _initialize_actions(self):
        try:
            self.actions = Actions(
                tts=self.tts,
                state=self.state,
                audio_effects=self.audio_effects,
                audio_handler=self.audio 
            )
        except Exception as e:
            raise e

    def _initialize_tts(self):
        try:
            self.tts = TTSManager()
            self.state.set_voice_active(True)
        except Exception as e:
            self.terminal.print_warning(f"TTS initialization error: {e}")
            self.state.set_voice_active(False)
            raise e

    def _initialize_llm(self):
        try:
            # Usar ModelOrchestrator para Multi-GPU
            self.orchestrator = ModelOrchestrator(
                config_path="src/config/models.json"
            )
            self.model_manager = None
            self.terminal.print_success("ModelOrchestrator initialized (Multi-GPU)")
            
            # CommandManager usa el orchestrator
            self.command_manager = CommandManager(
                model_manager=self.orchestrator,
            )
        except Exception as e:
            raise e

    def _async_audio_init(self):
        enable_whisper = os.getenv('ENABLE_WHISPER', 'true').lower() == 'true'
        
        if not enable_whisper:
            self.terminal.print_status("⌨️ Text mode - ENABLE_WHISPER=false")
            self.whisper = None
            self.audio = None
            self.state.set_listening_active(False)
            return
            
        try:
            logging.info("Iniciando inicialización de audio...")
            
            # Intentar usar WhisperHandler optimizado
            try:
                self.whisper = WhisperHandler(
                    model_path="models/whisper/large-v3-turbo-ct2",
                    device="cuda",
                    device_index=1,
                    compute_type="int8"
                )
                self.terminal.print_success("WhisperHandler initialized")
            except Exception as e:
                self.terminal.print_warning(f"Whisper fallback to CPU: {e}")
                try:
                    self.whisper = WhisperHandler(device="cpu")
                except Exception as e2:
                    self.terminal.print_error(f"Whisper CPU fallback also failed: {e2}")
                    self.whisper = None
            
            # AudioHandler (wrapper para reconocimiento de voz)
            if self.whisper:
                self.audio = AudioHandler(
                    terminal_manager=self.terminal,
                    tts=self.tts,
                    state=self.state,
                    input_queue=self.input_queue,
                    whisper_handler=self.whisper
                )
                self.state.set_listening_active(True)
            else:
                self.audio = None
                self.state.set_listening_active(False)
                self.terminal.print_warning("⌨️ Text mode only - Whisper not available")
        except Exception as e:
            self.terminal.print_warning(f"⌨️ Text mode only: {e}")
            self.state.set_listening_active(False)
            self.terminal.print_error(f"Error inicializando audio: {e}")
            if self.audio_effects:
                self.audio_effects.play('error')
            logging.error(f"Audio init error: {e}")
            self.audio = None

    def _handle_critical_error(self, message):
        logging.critical(message)
        self.terminal.print_error(message)
        if self.audio_effects:
            self.audio_effects.play('error')
        if self.state.increment_errors():
            self.terminal.print_error("Max error limit reached")
            self._shutdown_system()

    def _system_monitor(self):
        while self.state.is_running():
            try:
                status = self.system_monitor.check_system_health()
                if all(status.values()):
                    self.state.reset_errors()
                else:
                    self.state.increment_errors()
                    f = [k.replace('_ok','') for k,v in status.items() if not v]
                    logging.warning(f"Compromised: {f}")
                    time.sleep(5)
            except Exception as e:
                logging.error(f"Monitor error: {str(e)}")
                if self.state.get_error_count() >= self.state.max_errors:
                    sys.exit(1)
            time.sleep(1)

    def _process_inputs(self):
        try:
            t, content = self.input_queue.get_nowait()
            
            if content.strip():
                if self.tts:
                    self.tts.stop_speaking()

                if self.actions:
                    message, is_command = self.actions.handle_command(content)
                    if is_command == True:
                        if message:
                            self.terminal.print_response(message, "system")
                            self.storage.add_interaction({
                                "query": content,
                                "response": message,
                                "model": "system",
                                "type": "system-command"
                            })
                        self.terminal.update_prompt_state('NEUTRAL')
                        self.input_queue.task_done()
                        return
                
                self.terminal.update_prompt_state('PROCESSING')
                if self.command_manager:
                    response, response_type = self.command_manager.process_input(content)
                    if response and response_type in ["command", "error"]:
                        self.terminal.print_response(response, "system" if response_type == "command" else "error")
                        self.storage.add_interaction({
                            "query": content,
                            "response": response,
                            "model": "system" if response_type == "command" else "error",
                            "type": f"system-{response_type}"
                        })
                        self.input_queue.task_done()
                        
                        self.terminal.update_prompt_state('SPEAKING')
                        if self.tts:
                            self.tts.speak(response)
                        self.terminal.update_prompt_state('NEUTRAL')
                        return
                
                self.terminal.update_prompt_state('THINKING')
                try:
                    # Usar orchestrator con métricas y contexto RAG
                    if self.orchestrator:
                        # Calcular dificultad (simple heurística)
                        difficulty = self._estimate_difficulty(content)
                        
                        # Obtener contexto RAG si está disponible
                        rag_context = ""
                        if self.embeddings:
                            rag_context = self.embeddings.get_context_for_query(
                                query=content,
                                max_context=10,  # ✅ Incrementado de 3 a 10
                                min_similarity=0.7,  # ✅ Más estricto (era 0.3 implícito)
                                filter_by_difficulty=(max(1, difficulty-20), min(100, difficulty+20)),
                                deduplicate=True
                            )
                        
                        # Enriquecer query con SmartPromptBuilder si está disponible
                        if self.prompt_builder:
                            enriched_query = self.prompt_builder.build_enriched_prompt(
                                query=content,
                                rag_context=rag_context,
                                difficulty=difficulty,
                                model_name="qwen-14b",
                                enable_few_shot=True,
                                enable_cot=True
                            )
                        else:
                            # Fallback: formato simple
                            enriched_query = content
                            if rag_context:
                                enriched_query = f"Contexto relevante:\n{rag_context}\n\nPregunta: {content}"
                        
                        # Consultar con métricas
                        if self.metrics:
                            with QueryTimer(self.metrics, content, "auto", difficulty):
                                response, model_name = self.orchestrator.get_response(
                                    query=enriched_query,
                                    difficulty=difficulty
                                )
                        else:
                            response, model_name = self.orchestrator.get_response(
                                query=enriched_query,
                                difficulty=difficulty
                            )
                        
                        # Guardar en RAG para memoria de largo plazo
                        if self.embeddings:
                            self.embeddings.add_interaction(
                                query=content,
                                response=response,
                                model=model_name,
                                difficulty=difficulty
                            )
                        
                        # ✅ NUEVO: Evaluar calidad de respuesta (Fase 5)
                        quality_score = None
                        if self.quality_evaluator:
                            task_type = self.prompt_builder.detect_task_type(content).value if self.prompt_builder else "general"
                            quality_eval = self.quality_evaluator.evaluate(
                                query=content,
                                response=response,
                                task_type=task_type
                            )
                            quality_score = quality_eval["overall_score"]
                            
                            # Log warning si calidad baja
                            if not quality_eval["passed"]:
                                self.terminal.print_warning(
                                    f"⚠️  Low quality response detected (score: {quality_score:.2f})"
                                )
                        
                        # ✅ NUEVO: Log en Learning Manager (Fase 3)
                        if self.learning_manager and self.metrics:
                            # Get tokens used and response time from last query
                            tokens_used = getattr(self.orchestrator, 'last_tokens_used', 0)
                            response_time = getattr(self.metrics, 'last_response_time', 0)
                            
                            self.learning_manager.log_interaction(
                                query=content,
                                response=response,
                                model=model_name,
                                difficulty=difficulty,
                                task_type=task_type if self.prompt_builder else "general",
                                tokens_used=tokens_used,
                                response_time=response_time,
                                quality_score=quality_score,
                                metadata={
                                    "rag_enabled": rag_context != "",
                                    "smart_prompts": self.prompt_builder is not None
                                }
                            )
                    else:
                        # V1: Legacy model_manager
                        # aqui no se guarda interaccion por que ya esta dentro del get_response
                        response, model_name = self.model_manager.get_response(content)
                    
                    self.terminal.print_response(response, model_name)
                    if (t == 'voice' or self.state.voice_active) and self.tts:
                        self.tts.speak(response)
                except Exception as e:
                    self.terminal.print_error(f"Error del modelo: {e}")
                    self.storage.add_interaction({
                        "query": content,
                        "response": str(e),
                        "model": "error",
                        "type": "system-error"
                    })
                
            self.terminal.update_prompt_state('NEUTRAL')
            self.input_queue.task_done()
            
        except Empty:
            pass
        except Exception as e:
            self._handle_critical_error(f"Error processing input: {str(e)}")

    def _process_inputs_loop(self):
        while self.state.is_running():
            self._process_inputs()
            time.sleep(0.1)
        self._shutdown_system()

    def _estimate_difficulty(self, query: str) -> int:
        """
        Estima la dificultad de una query (0-100).
        Heurística simple basada en longitud, palabras clave, y complejidad.
        """
        query_lower = query.lower()
        difficulty = 30  # Base
        
        # Longitud
        if len(query) > 200:
            difficulty += 20
        elif len(query) > 100:
            difficulty += 10
        
        # Palabras clave complejas
        complex_keywords = [
            'explica', 'analiza', 'compara', 'teoría', 'científico', 'matemática',
            'complejo', 'detallado', 'profundo', 'técnico', 'algoritmo', 'física',
            'química', 'biología', 'filosofía', 'razona', 'demuestra', 'deriva'
        ]
        for keyword in complex_keywords:
            if keyword in query_lower:
                difficulty += 10
                break
        
        # Palabras clave simples
        simple_keywords = ['hola', 'qué tal', 'gracias', 'adiós', 'sí', 'no']
        for keyword in simple_keywords:
            if keyword in query_lower:
                difficulty = max(10, difficulty - 20)
                break
        
        return min(100, max(10, difficulty))
    
    def _kill_zombie_vllm_processes(self):
        """
        Force kill any remaining VLLM processes that weren't cleaned up properly
        This is a safety measure to prevent GPU memory leaks
        """
        import subprocess
        
        try:
            # Find VLLM processes
            result = subprocess.run(
                ["pgrep", "-f", "VLLM::EngineCore"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                logging.info(f"Found {len(pids)} zombie VLLM process(es): {pids}")
                
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-9", pid], timeout=2)
                        logging.info(f"Killed zombie VLLM process: {pid}")
                    except Exception as e:
                        logging.error(f"Failed to kill PID {pid}: {e}")
                        
                self.terminal.print_success("Zombie VLLM processes cleaned")
            else:
                logging.info("No zombie VLLM processes found")
                
        except subprocess.TimeoutExpired:
            logging.warning("Timeout while searching for VLLM processes")
        except FileNotFoundError:
            logging.warning("pgrep not available - skipping zombie cleanup")
        except Exception as e:
            logging.error(f"Error in zombie cleanup: {e}")

    def _shutdown_system(self, signum=None, frame=None):
        self.terminal.print_status("Shutting down...")
        try:
            self.state.set_running(False)
            self.terminal.print_warning("Shutdown signal received...")
            
            # Mostrar estadísticas finales
            if self.metrics:
                self.terminal.print_header("Session Statistics")
                self.metrics.print_stats()
            
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join(timeout=2)
            if hasattr(self, 'processor_thread'):
                self.processor_thread.join(timeout=2)
            if hasattr(self, 'text_handler'):
                self.text_handler.stop()
            if self.tts:
                self.tts.cleanup()
            
            # Cleanup orchestrator
            if hasattr(self, 'orchestrator') and self.orchestrator:
                self.terminal.print_status("Unloading models and cleaning GPU...")
                try:
                    # Explicitly cleanup all models and GPU resources
                    self.orchestrator.cleanup()
                except Exception as e:
                    logging.error(f"Orchestrator cleanup error: {e}")
                finally:
                    del self.orchestrator
                    
                # Force kill any zombie VLLM processes
                try:
                    self._kill_zombie_vllm_processes()
                except Exception as e:
                    logging.error(f"Error killing zombie VLLM processes: {e}")
            
            if hasattr(self, 'model_manager') and self.model_manager:
                del self.model_manager
            
            # V2: Cleanup embeddings
            if hasattr(self, 'embeddings') and self.embeddings:
                stats = self.embeddings.get_statistics()
                self.terminal.print_success(f"RAG: {stats['total_memories']} memories saved")
                del self.embeddings
            
            if hasattr(self, 'audio') and self.audio:
                self.audio.cleanup()
            
            self.terminal.print_goodbye()
            
        except Exception as e:
            logging.error(f"Shutdown error: {str(e)}")
        finally:
            os._exit(0)

    def run(self):
        self.monitor_thread = threading.Thread(target=self._system_monitor, daemon=True)
        self.processor_thread = threading.Thread(target=self._process_inputs_loop, daemon=True)
        self.monitor_thread.start()
        self.processor_thread.start()
        
        self.text_handler.run_interactive()
    
    def process_command(self, query: str) -> str:
        """
        Process a single command/query and return the response
        Used for non-interactive mode
        
        Args:
            query: User query/command
            
        Returns:
            Response string
        """
        try:
            print(f"\n🔵 Query: {query}")
            
            # Check if it's a system command
            if self.actions:
                message, is_command = self.actions.handle_command(query)
                if is_command == True:
                    if message:
                        print(f"\n🟢 System: {message}")
                        return message
                    return ""
            
            # Check command manager
            if self.command_manager:
                response, response_type = self.command_manager.process_input(query)
                if response and response_type in ["command", "error"]:
                    print(f"\n🟢 System: {response}")
                    return response
            
            # Process with LLM orchestrator
            if self.orchestrator:
                # Calcular dificultad
                difficulty = self._estimate_difficulty(query)
                
                # Obtener contexto RAG si está disponible
                rag_context = ""
                if self.embeddings:
                    rag_context = self.embeddings.get_context_for_query(
                        query=query,
                        max_context=10,  # ✅ Incrementado de 3 a 10
                        min_similarity=0.7,  # ✅ Más estricto
                        filter_by_difficulty=(max(1, difficulty-20), min(100, difficulty+20)),
                        deduplicate=True
                    )
                
                # Enriquecer query con SmartPromptBuilder si está disponible
                if self.prompt_builder:
                    enriched_query = self.prompt_builder.build_enriched_prompt(
                        query=query,
                        rag_context=rag_context,
                        difficulty=difficulty,
                        model_name="qwen-14b",
                        enable_few_shot=True,
                        enable_cot=True
                    )
                else:
                    # Fallback: formato simple
                    enriched_query = query
                    if rag_context:
                        enriched_query = f"Contexto relevante:\n{rag_context}\n\nPregunta: {query}"
                
                print("\n⏳ Processing...")
                
                # Consultar
                response, model_name = self.orchestrator.get_response(
                    query=enriched_query,
                    difficulty=difficulty
                )
                
                # Guardar en RAG
                if self.embeddings:
                    self.embeddings.add_interaction(
                        query=query,
                        response=response,
                        model=model_name,
                        difficulty=difficulty
                    )
                
                print(f"\n🟢 {model_name}: {response}")
                return response
            else:
                error_msg = "No hay modelos disponibles. Configura claves API o descarga modelos locales."
                print(f"\n🔴 {error_msg}")
                return error_msg
            
        except Exception as e:
            error_msg = f"Error processing command: {e}"
            logging.error(error_msg)
            print(f"\n🔴 {error_msg}")
            return error_msg

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Jarvis AI Assistant - Multi-GPU LLM System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python main.py
  
  # Command mode (single query)
  python main.py --query "¿Cuál es la capital de Francia?"
  
  # Command mode with specific model
  python main.py --query "Explica la teoría de la relatividad" --model llama-70b
  
  # Show available models
  python main.py --list-models
  
  # Debug mode (verbose logging)
  python main.py --debug
        """
    )
    
    parser.add_argument(
        '-q', '--query',
        type=str,
        help='Execute a single query and exit (non-interactive mode)'
    )
    
    parser.add_argument(
        '-m', '--model',
        type=str,
        help='Specify model to use (e.g., llama-70b, qwen-32b, gpt-4o-mini)'
    )
    
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List available models and exit'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show system statistics and exit'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug/verbose logging'
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # Configurar nivel de logging según --debug
    if not args.debug:
        # Suprimir pygame prompt ANTES de cualquier import
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
        
        # Suprimir logs verbosos de bibliotecas externas
        logging.getLogger("vllm").setLevel(logging.CRITICAL)
        logging.getLogger("torch").setLevel(logging.CRITICAL)
        logging.getLogger("transformers").setLevel(logging.CRITICAL)
        logging.getLogger("sentence_transformers").setLevel(logging.CRITICAL)
        logging.getLogger("chromadb").setLevel(logging.CRITICAL)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("pygame").setLevel(logging.CRITICAL)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("root").setLevel(logging.WARNING)
        
        # Suprimir nuestros propios INFO logs en modo normal
        logging.getLogger("MetricsTracker").setLevel(logging.WARNING)
        logging.getLogger("EmbeddingManager").setLevel(logging.WARNING)
        logging.getLogger("ModelOrchestrator").setLevel(logging.WARNING)
        logging.getLogger("LearningManager").setLevel(logging.WARNING)
        logging.getLogger("QualityEvaluator").setLevel(logging.WARNING)
        logging.getLogger("SmartPromptBuilder").setLevel(logging.WARNING)
        logging.getLogger("DynamicTokenManager").setLevel(logging.WARNING)
        
        # Suprimir warnings de deprecation
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", message=".*pkg_resources.*")
        warnings.filterwarnings("ignore", message=".*CUDA_DEVICE_ORDER.*")
    
    jarvis = Jarvis()

    
    try:
        # List models mode
        if args.list_models:
            print("\n" + "="*70)
            print("AVAILABLE MODELS")
            print("="*70)
            
            if hasattr(jarvis, 'orchestrator'):
                stats = jarvis.orchestrator.get_stats()
                print(f"\n📊 GPU Count: {stats['gpu_count']}")
                print(f"📦 Models Loaded: {len(stats['loaded_models'])}")
                
                for gpu_info in stats['gpus']:
                    print(f"\n🎮 {gpu_info['name']} (GPU {gpu_info['id']})")
                    print(f"   VRAM: {gpu_info['vram_used_mb']}MB / {gpu_info['vram_total_mb']}MB ({gpu_info['vram_percent']}%)")
                
                print("\n📋 Configured Models:")
                # List all models from config
                import json
                with open('src/config/models.json', 'r') as f:
                    config = json.load(f)
                    for model_id, model_info in config.get('models', {}).items():
                        status = "✅ LOADED" if model_id in stats['loaded_models'] else "⬜ NOT LOADED"
                        print(f"  {status} {model_id}: {model_info['name']} (GPU {model_info['gpu_id']}, {model_info['vram_required']}MB)")
            
            sys.exit(0)
        
        # Stats mode
        if args.stats:
            print("\n" + "="*70)
            print("SYSTEM STATISTICS")
            print("="*70)
            
            if hasattr(jarvis, 'orchestrator'):
                stats = jarvis.orchestrator.get_stats()
                print(f"\n🎮 GPUs: {stats['gpu_count']}")
                for gpu_info in stats['gpus']:
                    print(f"  GPU {gpu_info['id']}: {gpu_info['name']}")
                    print(f"    VRAM: {gpu_info['vram_used_mb']}MB / {gpu_info['vram_total_mb']}MB")
            
            if hasattr(jarvis, 'embeddings') and jarvis.embeddings:
                emb_stats = jarvis.embeddings.get_statistics()
                print(f"\n💾 Memories: {emb_stats.get('total_memories', 0)}")
            
            sys.exit(0)
        
        # Command mode
        if args.query:
            # TODO: Support model selection with args.model
            response = jarvis.process_command(args.query)
            sys.exit(0)
        
        # Interactive mode (default)
        jarvis.run()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        jarvis._shutdown_system()
        logging.error(f"Fatal error: {e}")
