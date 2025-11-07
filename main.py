#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
from queue import Queue, Empty
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

from src.utils.error_handler import setup_logging
from src.utils.audio_utils import AudioEffects
from src.utils.jarvis_state import JarvisState
from modules.text.terminal_manager import TerminalManager

# V2: Nuevo orchestrador multi-GPU
try:
    from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
    USE_V2_ORCHESTRATOR = True
except ImportError:
    from src.modules.llm.model_manager import ModelManager
    USE_V2_ORCHESTRATOR = False
    logging.warning("V2 ModelOrchestrator no disponible, usando ModelManager legacy")

# V2: Sistema de embeddings/RAG
try:
    from src.modules.embeddings.embedding_manager import EmbeddingManager
    USE_V2_EMBEDDINGS = True
except ImportError:
    USE_V2_EMBEDDINGS = False
    logging.warning("V2 EmbeddingManager no disponible")

# V2: Whisper optimizado
try:
    from src.modules.voice.whisper_handler import WhisperHandler
    USE_V2_WHISPER = True
except ImportError:
    USE_V2_WHISPER = False
    logging.warning("V2 WhisperHandler no disponible, usando AudioHandler legacy")

# V2: Métricas y monitoreo
try:
    from src.utils.metrics_tracker import MetricsTracker, QueryTimer
    USE_V2_METRICS = True
except ImportError:
    USE_V2_METRICS = False
    logging.warning("V2 MetricsTracker no disponible")

from modules.system_monitor import SystemMonitor
from src.modules.text.text_handler import TextHandler
from src.modules.voice.audio_handler import AudioHandler
from src.modules.voice.tts_manager import TTSManager
from src.modules.storage_manager import StorageManager
from modules.actions import Actions
from modules.system.command_manager import CommandManager

setup_logging()

class Jarvis:
    def __init__(self):
        # Thread-safe state management
        self.state = JarvisState(
            running=True,
            voice_active=False,
            listening_active=False,
            error_count=0,
            max_errors=5,
            v2_mode=USE_V2_ORCHESTRATOR
        )
        self.input_queue = Queue()
        self.executor = ThreadPoolExecutor(max_workers=2)
        load_dotenv()
        try:
            self.terminal = TerminalManager()
            version_str = "V2 (Multi-GPU + RAG)" if USE_V2_ORCHESTRATOR else "V1 (Legacy)"
            self.terminal.print_header(f"Starting Jarvis System {version_str}")
            
            self.system_monitor = SystemMonitor()
            self.terminal.print_success("System monitor initialized")
            
            self._initialize_tts()
            self.terminal.print_success("TTS initialized")
            
            self.storage = StorageManager()
            self.terminal.print_success("Storage initialized")
            
            self.audio_effects = AudioEffects()
            self.terminal.print_success("Audio effects initialized")
            
            # V2: Inicializar métricas
            if USE_V2_METRICS:
                self.metrics = MetricsTracker(
                    log_path="logs/metrics.jsonl",
                    enable_gpu_monitoring=True
                )
                self.terminal.print_success("V2 Metrics tracker initialized")
            else:
                self.metrics = None
            
            # V2: Inicializar embeddings/RAG
            if USE_V2_EMBEDDINGS:
                try:
                    self.embeddings = EmbeddingManager(
                        model_name="models/embeddings/bge-m3",
                        device="cuda:1",  # GPU2 para embeddings
                        chroma_path="vectorstore/chromadb"
                    )
                    self.terminal.print_success("V2 Embedding system (RAG) initialized")
                except Exception as e:
                    self.terminal.print_warning(f"V2 Embeddings fallback to CPU: {e}")
                    self.embeddings = EmbeddingManager(device="cpu")
            else:
                self.embeddings = None
            
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
                embeddings=self.embeddings if USE_V2_EMBEDDINGS else None  # Pasar RAG
            )
            self.terminal.print_success("Text handler initialized")
        
            self.terminal.print_header("Initializing Jarvis")
            
            # Mostrar estadísticas V2 si están disponibles
            if USE_V2_ORCHESTRATOR and hasattr(self, 'orchestrator'):
                stats = self.orchestrator.get_stats()
                self.terminal.print_success(f"GPUs: {stats['gpu_count']} | Models loaded: {stats['models_loaded']}")
            
            self.terminal.print_status("Jarvis Text Interface - Escribe 'help' para ver los comandos")
            self.terminal.update_prompt_state('NEUTRAL')
            self.audio_effects.play('startup')
        except Exception as e:
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
            if USE_V2_ORCHESTRATOR:
                # V2: Usar ModelOrchestrator
                self.orchestrator = ModelOrchestrator(
                    config_path="src/config/models_v2.json"
                )
                self.model_manager = None  # Legacy no usado
                self.terminal.print_success("V2 ModelOrchestrator initialized (Multi-GPU)")
                
                # CommandManager puede usar orchestrator o model_manager
                self.command_manager = CommandManager(
                    model_manager=self.orchestrator,  # Compatible con misma interfaz
                )
            else:
                # V1: Legacy ModelManager
                self.model_manager = ModelManager(storage_manager=self.storage, tts=self.tts)
                self.orchestrator = None
                self.terminal.print_success("V1 ModelManager initialized (Legacy)")
                
                self.command_manager = CommandManager(
                    model_manager=self.model_manager,
                )
        except Exception as e:
            raise e

    def _async_audio_init(self):
        try:
            logging.info("Iniciando inicialización de audio...")
            
            # V2: Intentar usar WhisperHandler optimizado
            if USE_V2_WHISPER:
                try:
                    self.whisper = WhisperHandler(
                        model_path="models/whisper/large-v3-turbo-ct2",
                        device="cuda",
                        device_index=1,  # GPU2
                        compute_type="int8"
                    )
                    self.terminal.print_success("V2 WhisperHandler initialized (4x faster)")
                except Exception as e:
                    self.terminal.print_warning(f"V2 Whisper fallback to CPU: {e}")
                    self.whisper = WhisperHandler(device="cpu")
            else:
                self.whisper = None
            
            # AudioHandler legacy (wrapper)
            self.audio = AudioHandler(
                terminal_manager=self.terminal,
                tts=self.tts,
                state=self.state,
                input_queue=self.input_queue,
                whisper_handler=self.whisper if USE_V2_WHISPER else None  # V2 passthrough
            )
            self.state.set_listening_active(True)
            pass
        except Exception as e:
            self.terminal.print_warning(f"⌨️ Text mode only: {e}")
            self.state.set_listening_active(False)
            self.terminal.print_error(f"Error inicializando audio: {e}")
            self.audio_effects.play('error')
            logging.error(f"Audio init error: {e}")

    def _handle_critical_error(self, message):
        logging.critical(message)
        self.terminal.print_error(message)
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
                if hasattr(self, 'tts'):
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
                        self.tts.speak(response)
                        self.terminal.update_prompt_state('NEUTRAL')
                        return
                
                self.terminal.update_prompt_state('THINKING')
                try:
                    # V2: Usar orchestrator con métricas y contexto RAG
                    if USE_V2_ORCHESTRATOR and self.orchestrator:
                        # Calcular dificultad (simple heurística)
                        difficulty = self._estimate_difficulty(content)
                        
                        # Obtener contexto RAG si está disponible
                        rag_context = ""
                        if self.embeddings:
                            rag_context = self.embeddings.get_context_for_query(content, max_context=3)
                        
                        # Enriquecer query con contexto
                        enriched_query = content
                        if rag_context:
                            enriched_query = f"Contexto relevante:\n{rag_context}\n\nPregunta: {content}"
                        
                        # Consultar con métricas
                        if USE_V2_METRICS and self.metrics:
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
                    else:
                        # V1: Legacy model_manager
                        # aqui no se guarda interaccion por que ya esta dentro del get_response
                        response, model_name = self.model_manager.get_response(content)
                    
                    self.terminal.print_response(response, model_name)
                    if (t == 'voice' or self.state.voice_active) and hasattr(self, 'tts'):
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

    def _shutdown_system(self, signum=None, frame=None):
        self.terminal.print_status("Shutting down...")
        try:
            self.state.set_running(False)
            self.terminal.print_warning("Shutdown signal received...")
            
            # V2: Mostrar estadísticas finales
            if USE_V2_METRICS and self.metrics:
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
            if hasattr(self, 'tts'):
                self.tts.cleanup()
            
            # V2: Cleanup orchestrator
            if hasattr(self, 'orchestrator') and self.orchestrator:
                self.terminal.print_status("Unloading V2 models...")
                # No hay método cleanup directo, pero Python limpiará en exit
                del self.orchestrator
            
            if hasattr(self, 'model_manager') and self.model_manager:
                del self.model_manager
            
            # V2: Cleanup embeddings
            if hasattr(self, 'embeddings') and self.embeddings:
                stats = self.embeddings.get_statistics()
                self.terminal.print_success(f"RAG: {stats['total_memories']} memories saved")
                del self.embeddings
            
            if hasattr(self, 'audio'):
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

if __name__ == "__main__":
    jarvis = Jarvis()
    try:
        jarvis.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        jarvis._shutdown_system()
        logging.error(f"Fatal error: {e}")
