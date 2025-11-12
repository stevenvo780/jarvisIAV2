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
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Modelo para mensajes de chat"""
    message: str = Field(..., min_length=1, max_length=5000)
    timestamp: Optional[str] = None

    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


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
        self.chat_history = deque(maxlen=100)  # Límite de 100 mensajes en memoria
        self.active_connections: List[WebSocket] = []
        self.start_time = datetime.now()  # Para tracking de uptime

        self._setup_middleware()
        self._setup_routes()
        self._mount_static()
    
    def _setup_middleware(self):
        """Configurar middleware CORS"""
        # Permitir solo localhost y dominios específicos
        allowed_origins = [
            "http://localhost:8090",
            "http://127.0.0.1:8090",
            "http://localhost:*",
            "http://127.0.0.1:*"
        ]

        # Agregar dominio custom desde variable de entorno si existe
        custom_origin = os.getenv("JARVIS_ALLOWED_ORIGIN")
        if custom_origin:
            allowed_origins.append(custom_origin)

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type"],
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
                
                uptime_seconds = (datetime.now() - self.start_time).total_seconds()
                return SystemStatus(
                    status="ready",
                    models_loaded=models_loaded,
                    gpu_count=gpu_count,
                    uptime=uptime_seconds
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
        async def get_history(offset: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
            """Obtener historial de chat con paginación"""
            history_list = list(self.chat_history)
            return history_list[offset:offset+limit]
        
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
            # Usar ModelOrchestrator para obtener respuesta
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

                # System prompt para respuestas concisas y directas
                system_prompt = """Eres Jarvis, un asistente de IA útil y conciso.
Instrucciones importantes:
- Responde de forma breve y directa
- Si la pregunta es simple, da una respuesta corta (1-3 oraciones)
- Solo proporciona detalles adicionales si el usuario los solicita explícitamente
- No inventes información ni hables de temas no relacionados
- Mantén tus respuestas en el tema de la pregunta"""

                # Construir prompt completo
                if context:
                    full_prompt = f"{system_prompt}\n\n{context}\n\nUsuario: {message}\nAsistente:"
                else:
                    full_prompt = f"{system_prompt}\n\nUsuario: {message}\nAsistente:"
                
                # Estimar dificultad (simple: longitud del mensaje)
                difficulty = min(50 + len(message) // 10, 90)
                
                # Obtener respuesta del modelo usando get_response
                response, model_used = await asyncio.to_thread(
                    llm_system.get_response,
                    full_prompt,
                    difficulty=difficulty
                )
                
                if response and not response.startswith("Error:"):
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
                elif response:
                    return response  # Devolver mensaje de error del orchestrator
                
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
