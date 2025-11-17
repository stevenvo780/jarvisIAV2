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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
import json

# Rate limiting (opcional - solo si slowapi está instalado)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False
    # Logger se inicializa más adelante, así que no podemos usarlo aquí

# Authentication helpers
from fastapi import Depends, Header

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

        # API Keys (opcional - si está configurado)
        self.api_keys = set()
        api_keys_env = os.getenv("JARVIS_API_KEYS", "")
        if api_keys_env:
            self.api_keys = set(api_keys_env.split(","))
            logger.info(f"✅ API key authentication enabled ({len(self.api_keys)} keys)")
        else:
            logger.info("ℹ️  API key authentication disabled (set JARVIS_API_KEYS to enable)")

        # Rate limiting (si está disponible)
        if RATE_LIMIT_AVAILABLE:
            self.limiter = Limiter(key_func=get_remote_address)
            self.app.state.limiter = self.limiter
            self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            logger.info("✅ Rate limiting enabled (10 req/min)")
        else:
            self.limiter = None
            logger.warning("⚠️  Rate limiting disabled")

        self._setup_middleware()
        self._setup_routes()
        self._mount_static()
    
    def _setup_middleware(self):
        """Configurar middleware CORS y compresión"""
        # Compresión gzip para respuestas > 500 bytes
        self.app.add_middleware(GZipMiddleware, minimum_size=500)

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
    
    async def _verify_api_key(self, x_api_key: Optional[str] = Header(None)):
        """Verificar API key si la autenticación está habilitada"""
        # Si no hay keys configuradas, permitir acceso
        if not self.api_keys:
            return True

        # Si hay keys configuradas, verificar
        if not x_api_key or x_api_key not in self.api_keys:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key. Add X-Api-Key header."
            )
        return True

    def _setup_routes(self):
        """Configurar rutas de la API"""

        @self.app.get("/health")
        async def health_check():
            """Health check público sin información sensible"""
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "service": "jarvis-web"
            }

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
        async def get_status(authenticated: bool = Depends(self._verify_api_key)) -> SystemStatus:
            """Obtener estado del sistema (requiere API key si está configurado)"""
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
        
        # Aplicar rate limiting si está disponible
        chat_route = self.app.post("/api/chat")
        if RATE_LIMIT_AVAILABLE and self.limiter:
            chat_route = self.limiter.limit("10/minute")(chat_route)

        @chat_route
        async def chat(
            request: Request,
            message: ChatMessage,
            authenticated: bool = Depends(self._verify_api_key)
        ) -> ChatResponse:
            """Enviar mensaje a Jarvis (máx 10 req/min si rate limiting está habilitado)"""
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
        
        @self.app.get("/api/voice/config")
        async def get_voice_config():
            """Obtener configuración de voz (cliente-side Web Speech API)"""
            return {
                "tts_enabled": True,
                "stt_enabled": True,
                "wake_word": "jarvis",
                "language": "es-ES",
                "voice_rate": 1.0,
                "voice_pitch": 1.0
            }
        
        @self.app.post("/api/voice/settings")
        async def update_voice_settings(settings: Dict[str, Any]):
            """Actualizar configuración de voz (almacenada en cliente)"""
            # La configuración se maneja en el cliente (localStorage)
            # Aquí solo validamos y retornamos confirmación
            return {"status": "ok", "settings": settings}

        @self.app.post("/api/chat/stream")
        async def chat_stream(request: Request, message: ChatMessage):
            """Streaming de respuesta con Server-Sent Events (mejor UX)"""
            if not self.jarvis:
                raise HTTPException(status_code=503, detail="Jarvis not initialized")

            async def generate():
                try:
                    # Enviar evento de inicio
                    yield f"data: {json.dumps({'type': 'start', 'timestamp': datetime.now().isoformat()})}\n\n"

                    # Procesar mensaje
                    response_text = await self._process_message(message.message)

                    # Simular streaming enviando la respuesta en chunks
                    words = response_text.split()
                    for i, word in enumerate(words):
                        chunk_data = {
                            'type': 'token',
                            'content': word + (' ' if i < len(words) - 1 else ''),
                            'index': i
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        await asyncio.sleep(0.01)  # Pequeño delay para simular streaming

                    # Enviar evento de finalización
                    yield f"data: {json.dumps({'type': 'done', 'timestamp': datetime.now().isoformat()})}\n\n"

                except Exception as e:
                    logger.error(f"Error in streaming: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")
        
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
                
                # Verificar si hay modelos locales disponibles
                has_local_models = len(llm_system.loaded_models) > 0
                
                # Estimar dificultad
                # Si NO hay modelos locales, usar dificultad alta para forzar API
                if not has_local_models:
                    logger.info("⚠️ No hay modelos locales disponibles, usando API")
                    difficulty = 95  # Forzar uso de API
                else:
                    # Dificultad basada en longitud del mensaje
                    difficulty = min(50 + len(message) // 10, 90)
                
                logger.debug(f"Procesando mensaje (difficulty={difficulty}, local_models={has_local_models})")
                
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
