"""
Jarvis Web Interface - FastAPI Backend
Proporciona una interfaz web limpia y moderna para interactuar con Jarvis
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Modelo para mensajes de chat"""
    message: str
    timestamp: Optional[str] = None


class ChatResponse(BaseModel):
    """Modelo para respuestas de chat"""
    response: str
    timestamp: str
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None


class SystemStatus(BaseModel):
    """Modelo para estado del sistema"""
    status: str
    models_loaded: int
    gpu_count: int
    memory_usage: Optional[Dict[str, Any]] = None
    uptime: Optional[float] = None


class WebInterface:
    """Interfaz web para Jarvis"""
    
    def __init__(self, jarvis_instance=None):
        self.app = FastAPI(
            title="Jarvis AI Assistant",
            description="Interfaz web para interactuar con Jarvis",
            version="1.0.0"
        )
        self.jarvis = jarvis_instance
        self.chat_history: List[Dict[str, Any]] = []
        self.active_connections: List[WebSocket] = []
        
        self._setup_middleware()
        self._setup_routes()
        self._mount_static()
    
    def _setup_middleware(self):
        """Configurar middleware CORS"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _mount_static(self):
        """Montar archivos estáticos"""
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    def _setup_routes(self):
        """Configurar rutas de la API"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Página principal"""
            html_file = Path(__file__).parent / "templates" / "index.html"
            if html_file.exists():
                return html_file.read_text()
            return """
            <html>
                <head><title>Jarvis AI</title></head>
                <body>
                    <h1>Jarvis AI Assistant</h1>
                    <p>Interfaz web cargando...</p>
                    <p>Si ves esto, verifica que templates/index.html existe</p>
                </body>
            </html>
            """
        
        @self.app.get("/api/status")
        async def get_status() -> SystemStatus:
            """Obtener estado del sistema"""
            if not self.jarvis:
                return SystemStatus(
                    status="initializing",
                    models_loaded=0,
                    gpu_count=0
                )
            
            try:
                orchestrator = getattr(self.jarvis, 'llm_system', None)
                if orchestrator:
                    models_loaded = len(orchestrator.loaded_models)
                    gpu_count = orchestrator.gpu_count
                else:
                    models_loaded = 0
                    gpu_count = 0
                
                return SystemStatus(
                    status="ready",
                    models_loaded=models_loaded,
                    gpu_count=gpu_count,
                    uptime=getattr(self.jarvis, 'uptime', 0.0)
                )
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return SystemStatus(
                    status="error",
                    models_loaded=0,
                    gpu_count=0
                )
        
        @self.app.post("/api/chat")
        async def chat(message: ChatMessage) -> ChatResponse:
            """Enviar mensaje a Jarvis"""
            if not self.jarvis:
                raise HTTPException(status_code=503, detail="Jarvis not initialized")
            
            try:
                start_time = datetime.now()
                
                # Procesar mensaje con Jarvis
                response_text = await self._process_message(message.message)
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                # Guardar en historial
                chat_entry = {
                    "user": message.message,
                    "assistant": response_text,
                    "timestamp": end_time.isoformat(),
                    "response_time": response_time
                }
                self.chat_history.append(chat_entry)
                
                return ChatResponse(
                    response=response_text,
                    timestamp=end_time.isoformat(),
                    response_time=response_time
                )
            
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/history")
        async def get_history() -> List[Dict[str, Any]]:
            """Obtener historial de chat"""
            return self.chat_history[-50:]  # Últimos 50 mensajes
        
        @self.app.delete("/api/history")
        async def clear_history():
            """Limpiar historial de chat"""
            self.chat_history.clear()
            return {"status": "ok", "message": "History cleared"}
        
        @self.app.websocket("/ws/chat")
        async def websocket_chat(websocket: WebSocket):
            """WebSocket para streaming de respuestas"""
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    
                    # Procesar mensaje
                    response = await self._process_message(data)
                    
                    # Enviar respuesta
                    await websocket.send_json({
                        "type": "message",
                        "content": response,
                        "timestamp": datetime.now().isoformat()
                    })
            
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
    
    async def _process_message(self, message: str) -> str:
        """
        Procesar mensaje con Jarvis
        Maneja la comunicación con el sistema principal de Jarvis
        """
        if not self.jarvis:
            return "Error: Jarvis no está inicializado"
        
        try:
            # Usar ModelOrchestrator directamente para obtener respuesta
            llm_system = getattr(self.jarvis, 'llm_system', None)
            if llm_system:
                # Buscar contexto RAG si está disponible
                context = ""
                embedding_manager = getattr(self.jarvis, 'embedding_manager', None)
                if embedding_manager:
                    try:
                        results = await asyncio.to_thread(
                            embedding_manager.search_memories,
                            message,
                            k=3
                        )
                        if results:
                            context = "\n".join([f"- {r['content']}" for r in results[:3]])
                            context = f"\nContexto relevante:\n{context}\n"
                    except Exception as e:
                        logger.debug(f"No se pudo obtener contexto RAG: {e}")
                
                # Construir prompt con contexto
                full_prompt = f"{context}\nUsuario: {message}\nAsistente:"
                
                # Obtener respuesta del modelo
                response = await asyncio.to_thread(
                    llm_system.query,
                    full_prompt,
                    query_type="chat"
                )
                
                if response:
                    # Guardar en memoria RAG
                    if embedding_manager:
                        try:
                            await asyncio.to_thread(
                                embedding_manager.add_memory,
                                f"Usuario preguntó: {message}. Respondí: {response}"
                            )
                        except Exception as e:
                            logger.debug(f"No se pudo guardar en RAG: {e}")
                    
                    return response
                
                return "Lo siento, no pude generar una respuesta."
            
            return "Error: Sistema de procesamiento no disponible"
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error al procesar mensaje: {str(e)}"
    
    def set_jarvis_instance(self, jarvis_instance):
        """Configurar instancia de Jarvis después de la inicialización"""
        self.jarvis = jarvis_instance
        logger.info("✅ Jarvis instance connected to web interface")


def create_web_app(jarvis_instance=None) -> FastAPI:
    """
    Factory function para crear la aplicación web
    
    Args:
        jarvis_instance: Instancia de Jarvis para conectar
    
    Returns:
        FastAPI app configurada
    """
    web_interface = WebInterface(jarvis_instance)
    return web_interface.app, web_interface


if __name__ == "__main__":
    # Para desarrollo: ejecutar servidor directamente
    import uvicorn
    
    app, _ = create_web_app()
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
