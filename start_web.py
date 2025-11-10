#!/usr/bin/env python3
"""
Jarvis Web Launcher
Inicia Jarvis con interfaz web en http://localhost:8090
"""

import os
import sys
import asyncio
import threading
import argparse
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

# Parse args para --debug
parser = argparse.ArgumentParser(description='Jarvis AI Assistant - Web Interface')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
parser.add_argument('--port', type=int, default=8090, help='Puerto para interfaz web (default: 8090)')
parser.add_argument('--host', default='0.0.0.0', help='Host para interfaz web (default: 0.0.0.0)')
args = parser.parse_args()

if args.debug:
    os.environ['JARVIS_DEBUG'] = '1'

# Configurar supresión de logs
from src.utils.log_suppressor import setup_clean_terminal
setup_clean_terminal()

import logging
from dotenv import load_dotenv

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO if not args.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports de Jarvis
from src.utils.error_handler import setup_logging
from modules.text.terminal_manager import TerminalManager
from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
from src.modules.embeddings.embedding_manager import EmbeddingManager
from src.modules.learning.learning_manager import LearningManager
from src.utils.smart_prompt_builder import SmartPromptBuilder
from src.utils.quality_evaluator import QualityEvaluator
from src.utils.metrics_tracker import MetricsTracker
from modules.system_monitor import SystemMonitor
from src.modules.text.text_handler import TextHandler
from src.modules.storage_manager import StorageManager
from modules.actions import Actions

# Import web interface
from src.web.api import create_web_app

setup_logging()
load_dotenv()


class JarvisWeb:
    """Jarvis con interfaz web"""
    
    def __init__(self):
        self.terminal = TerminalManager()
        self.terminal.print_header("Jarvis AI Assistant - Web Interface")
        
        logger.info("🌐 Inicializando Jarvis para interfaz web...")
        
        # Inicializar componentes core
        self.system_monitor = SystemMonitor()
        logger.info("✓ System monitor initialized")
        
        self.storage = StorageManager()
        logger.info("✓ Storage initialized")
        
        self.metrics = MetricsTracker()
        logger.info("✓ Metrics tracker initialized")
        
        # RAG System
        self.embedding_manager = EmbeddingManager()
        logger.info("✓ Embedding system (RAG) initialized")
        
        # LLM Components
        self.prompt_builder = SmartPromptBuilder()
        logger.info("✓ SmartPromptBuilder initialized")
        
        self.learning_manager = LearningManager()
        logger.info("✓ LearningManager initialized")
        
        self.quality_evaluator = QualityEvaluator()
        logger.info("✓ QualityEvaluator initialized")
        
        # Model Orchestrator (Multi-GPU)
        self.llm_system = ModelOrchestrator()
        logger.info("✓ ModelOrchestrator initialized (Multi-GPU)")
        
        # Actions
        self.actions = Actions()
        logger.info("✓ Actions initialized")
        
        # Text Handler
        self.text_handler = TextHandler(
            llm_system=self.llm_system,
            embedding_manager=self.embedding_manager,
            actions=self.actions,
            storage=self.storage,
            learning_manager=self.learning_manager,
            prompt_builder=self.prompt_builder,
            quality_evaluator=self.quality_evaluator
        )
        logger.info("✓ Text handler initialized")
        
        logger.info("✅ Jarvis core initialized successfully")
    
    def get_status(self):
        """Obtener estado del sistema"""
        return {
            'models_loaded': len(self.llm_system.loaded_models),
            'gpu_count': self.llm_system.gpu_count,
            'storage_ready': self.storage is not None,
            'rag_ready': self.embedding_manager is not None
        }


def run_web_server(jarvis_instance, host='0.0.0.0', port=8090):
    """Ejecutar servidor web"""
    import uvicorn
    
    # Crear app web y conectar con Jarvis
    app, web_interface = create_web_app(jarvis_instance)
    
    logger.info(f"🌐 Iniciando servidor web en http://{host}:{port}")
    logger.info(f"📱 Abre tu navegador en: http://localhost:{port}")
    
    # Configurar uvicorn para logging mínimo
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(client_addr)s - %(request_line)s - %(status_code)s"
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning" if not args.debug else "info",
        access_log=args.debug
    )


def main():
    """Main entry point"""
    try:
        # Verificar y crear models_v2.json si no existe
        models_v2_path = PROJECT_ROOT / 'src' / 'config' / 'models_v2.json'
        models_path = PROJECT_ROOT / 'src' / 'config' / 'models.json'
        
        if not models_v2_path.exists() and models_path.exists():
            logger.info("📋 Creando models_v2.json desde models.json...")
            import shutil
            shutil.copy(models_path, models_v2_path)
            logger.info("✅ models_v2.json creado")
        
        # Banner
        print("\n" + "="*60)
        print("🤖 JARVIS AI ASSISTANT - WEB INTERFACE")
        print("="*60)
        print(f"📱 Interfaz web: http://localhost:{args.port}")
        print(f"⚙️  Puerto: {args.port}")
        print(f"🔧 Debug: {'Activado' if args.debug else 'Desactivado'}")
        print("="*60 + "\n")
        
        # Inicializar Jarvis
        logger.info("Inicializando Jarvis...")
        jarvis = JarvisWeb()
        
        status = jarvis.get_status()
        logger.info(f"✅ Jarvis listo: {status['models_loaded']} modelos, {status['gpu_count']} GPUs")
        
        # Iniciar servidor web
        logger.info("\n🚀 Iniciando interfaz web...")
        logger.info(f"🌐 Abre tu navegador en: http://localhost:{args.port}\n")
        
        run_web_server(jarvis, host=args.host, port=args.port)
    
    except KeyboardInterrupt:
        logger.info("\n👋 Cerrando Jarvis...")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
