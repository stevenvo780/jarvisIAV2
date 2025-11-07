"""
Model Backend Abstraction Layer
Provides unified interface for V1 (ModelManager) and V2 (ModelOrchestrator)
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging


@dataclass
class QueryResult:
    """Result of a model query"""
    response: str
    model_name: str
    difficulty: int
    latency: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ModelBackendInterface(ABC):
    """
    Abstract interface for model backends
    
    Allows seamless switching between V1 (ModelManager) and V2 (ModelOrchestrator)
    without changing client code.
    """
    
    @abstractmethod
    def query(self, text: str, context: Optional[Dict] = None) -> QueryResult:
        """
        Execute a query against the model backend
        
        Args:
            text: User query text
            context: Optional context dictionary
        
        Returns:
            QueryResult with response and metadata
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get backend statistics
        
        Returns:
            Dictionary with backend stats
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if backend is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """
        Get backend version identifier
        
        Returns:
            Version string (e.g., "V1", "V2")
        """
        pass


class V1BackendAdapter(ModelBackendInterface):
    """Adapter for V1 ModelManager"""
    
    def __init__(self, model_manager):
        """
        Initialize V1 adapter
        
        Args:
            model_manager: Instance of ModelManager (V1)
        """
        self.model_manager = model_manager
        self.logger = logging.getLogger("V1Backend")
    
    def query(self, text: str, context: Optional[Dict] = None) -> QueryResult:
        """Execute query using V1 ModelManager"""
        import time
        
        start = time.time()
        try:
            response, model_name = self.model_manager.get_response(text)
            latency = time.time() - start
            
            # Estimate difficulty (V1 doesn't expose this easily)
            difficulty = self.model_manager._analyze_query_difficulty(text)
            
            return QueryResult(
                response=response,
                model_name=model_name,
                difficulty=difficulty,
                latency=latency,
                success=model_name != "error",
                error=None if model_name != "error" else response,
                metadata={
                    'backend': 'V1',
                    'model_count': len(self.model_manager.models)
                }
            )
        
        except Exception as e:
            latency = time.time() - start
            self.logger.error(f"V1 query error: {e}")
            
            return QueryResult(
                response=str(e),
                model_name="error",
                difficulty=0,
                latency=latency,
                success=False,
                error=str(e),
                metadata={'backend': 'V1'}
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get V1 backend stats"""
        return {
            'backend': 'V1',
            'version': 'legacy',
            'models_available': len(self.model_manager.models),
            'models_loaded': len(self.model_manager.models),
        }
    
    def is_healthy(self) -> bool:
        """Check V1 health"""
        return len(self.model_manager.models) > 0
    
    def get_version(self) -> str:
        """Get version"""
        return "V1-Legacy"


class V2BackendAdapter(ModelBackendInterface):
    """Adapter for V2 ModelOrchestrator"""
    
    def __init__(self, orchestrator):
        """
        Initialize V2 adapter
        
        Args:
            orchestrator: Instance of ModelOrchestrator (V2)
        """
        self.orchestrator = orchestrator
        self.logger = logging.getLogger("V2Backend")
    
    def query(self, text: str, context: Optional[Dict] = None) -> QueryResult:
        """Execute query using V2 ModelOrchestrator"""
        import time
        
        start = time.time()
        try:
            # V2 orchestrator query method (needs to be implemented)
            # For now, assume it has a query() method
            if hasattr(self.orchestrator, 'query'):
                result = self.orchestrator.query(text, context or {})
                latency = time.time() - start
                
                return QueryResult(
                    response=result.get('response', ''),
                    model_name=result.get('model', 'unknown'),
                    difficulty=result.get('difficulty', 0),
                    latency=latency,
                    success=True,
                    metadata={
                        'backend': 'V2',
                        'gpu_count': self.orchestrator.gpu_count,
                        'models_loaded': len(self.orchestrator.loaded_models)
                    }
                )
            else:
                # Fallback if query method not implemented
                raise NotImplementedError("V2 Orchestrator query method not implemented")
        
        except Exception as e:
            latency = time.time() - start
            self.logger.error(f"V2 query error: {e}")
            
            return QueryResult(
                response=str(e),
                model_name="error",
                difficulty=0,
                latency=latency,
                success=False,
                error=str(e),
                metadata={'backend': 'V2'}
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get V2 backend stats"""
        return self.orchestrator.get_stats()
    
    def is_healthy(self) -> bool:
        """Check V2 health"""
        # Check if at least one model is loaded or can be loaded
        return self.orchestrator.gpu_count > 0 or len(self.orchestrator.loaded_models) > 0
    
    def get_version(self) -> str:
        """Get version"""
        return "V2-MultiGPU"


class BackendFactory:
    """Factory for creating model backends"""
    
    @staticmethod
    def create_backend(
        backend_type: str,
        **kwargs
    ) -> ModelBackendInterface:
        """
        Create model backend based on type
        
        Args:
            backend_type: "v1" or "v2"
            **kwargs: Arguments for backend initialization
        
        Returns:
            ModelBackendInterface instance
        
        Raises:
            ValueError: If backend_type is invalid
        """
        backend_type = backend_type.lower()
        
        if backend_type == "v1":
            from src.modules.llm.model_manager import ModelManager
            
            model_manager = ModelManager(
                storage_manager=kwargs.get('storage_manager'),
                tts=kwargs.get('tts')
            )
            return V1BackendAdapter(model_manager)
        
        elif backend_type == "v2":
            from src.modules.orchestrator.model_orchestrator import ModelOrchestrator
            
            orchestrator = ModelOrchestrator(
                config_path=kwargs.get('config_path', 'src/config/models_v2.json')
            )
            return V2BackendAdapter(orchestrator)
        
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
    
    @staticmethod
    def auto_select_backend(**kwargs) -> ModelBackendInterface:
        """
        Automatically select best available backend
        
        Tries V2 first, falls back to V1 if unavailable
        
        Args:
            **kwargs: Arguments for backend initialization
        
        Returns:
            ModelBackendInterface instance
        """
        logger = logging.getLogger("BackendFactory")
        
        # Try V2 first (preferred)
        try:
            backend = BackendFactory.create_backend("v2", **kwargs)
            logger.info("✅ Selected V2 backend (Multi-GPU)")
            return backend
        except Exception as e:
            logger.warning(f"V2 backend unavailable: {e}")
        
        # Fallback to V1
        try:
            backend = BackendFactory.create_backend("v1", **kwargs)
            logger.info("✅ Selected V1 backend (Legacy)")
            return backend
        except Exception as e:
            logger.error(f"No backend available: {e}")
            raise RuntimeError("No model backend available")
