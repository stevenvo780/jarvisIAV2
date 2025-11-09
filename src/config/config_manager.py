"""
Gestor de Configuración Centralizado para Jarvis IA V2
Singleton pattern con validación, type hints y carga desde múltiples fuentes
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading


logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Tipos de backend soportados"""
    VLLM = "vllm"
    TRANSFORMERS = "transformers"
    LLAMA_CPP = "llama_cpp"
    API = "api"


class LogFormat(Enum):
    """Formatos de logging"""
    TEXT = "text"
    JSON = "json"


@dataclass
class GPUConfig:
    """Configuración de GPU - Optimizada para mejor throughput"""
    primary_gpu_id: int = 0
    secondary_gpu_id: int = 1
    vram_buffer_mb: int = 500
    gpu_memory_utilization: float = 0.92  # Optimizado: 0.90 → 0.92 (+7% VRAM disponible)
    max_num_seqs: int = 64  # Optimizado: soporte para 64 secuencias concurrentes (vs 16 default)
    max_num_batched_tokens: int = 8192  # Tokens por batch para continuous batching
    enable_prefix_caching: bool = True  # Cache de KV para prefixes comunes
    enable_chunked_prefill: bool = True  # Chunked prefill para mejor latencia
    swap_space_gb: int = 8  # Espacio de swap en CPU RAM para modelos grandes
    enable_monitoring: bool = True
    monitor_interval: int = 5
    
    def __post_init__(self):
        if not 0 <= self.gpu_memory_utilization <= 1.0:
            raise ValueError("gpu_memory_utilization debe estar entre 0.0 y 1.0")


@dataclass
class InferenceConfig:
    """Configuración de inferencia"""
    default_backend: BackendType = BackendType.VLLM
    max_tokens: int = 4096
    default_temperature: float = 0.7
    preferred_quantization: str = "awq"
    inference_timeout: int = 60
    
    def __post_init__(self):
        if not 0.0 <= self.default_temperature <= 2.0:
            raise ValueError("temperature debe estar entre 0.0 y 2.0")
        if self.max_tokens < 1:
            raise ValueError("max_tokens debe ser positivo")


@dataclass
class RAGConfig:
    """Configuración del sistema RAG"""
    chroma_db_path: str = "./vectorstore/chromadb"
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cuda:1"
    max_results: int = 5
    similarity_threshold: float = 0.7
    enable_rag: bool = True
    
    def __post_init__(self):
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold debe estar entre 0.0 y 1.0")


@dataclass
class WhisperConfig:
    """Configuración de Whisper"""
    model: str = "large-v3-turbo"
    backend: str = "faster-whisper"
    device: str = "cuda:1"
    compute_type: str = "int8"
    language: str = "es"
    
    @property
    def model_path(self) -> str:
        """Path al modelo Whisper"""
        return f"models/whisper/{self.model}"


@dataclass
class TTSConfig:
    """Configuración de Text-to-Speech"""
    engine: str = "gtts"
    language: str = "es"
    speed: float = 1.0
    volume: float = 0.8
    
    def __post_init__(self):
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError("speed debe estar entre 0.5 y 2.0")
        if not 0.0 <= self.volume <= 1.0:
            raise ValueError("volume debe estar entre 0.0 y 1.0")


@dataclass
class AudioConfig:
    """Configuración de audio"""
    device_index: Optional[int] = None
    sample_rate: int = 16000
    channels: int = 1
    energy_threshold: int = 250
    dynamic_energy_adjustment: bool = True


@dataclass
class LoggingConfig:
    """Configuración de logging"""
    log_level: str = "INFO"
    log_dir: str = "./logs"
    log_format: LogFormat = LogFormat.TEXT
    structured_logging: bool = False
    max_size_mb: int = 10
    backup_count: int = 5
    
    @property
    def level(self) -> int:
        """Convertir string a nivel de logging"""
        return getattr(logging, self.log_level.upper(), logging.INFO)


@dataclass
class MetricsConfig:
    """Configuración de métricas"""
    enable_metrics: bool = True
    metrics_log_path: str = "./logs/metrics.jsonl"
    enable_profiling: bool = False


@dataclass
class SecurityConfig:
    """Configuración de seguridad"""
    blocked_terms: List[str] = field(default_factory=list)
    strict_input_validation: bool = True
    max_query_length: int = 5000
    
    def __post_init__(self):
        if self.max_query_length < 1:
            raise ValueError("max_query_length debe ser positivo")


@dataclass
class SystemConfig:
    """Configuración del sistema"""
    max_workers: int = 2
    cpu_threshold: int = 80
    memory_threshold: int = 85
    disk_threshold: int = 90
    debug_mode: bool = False
    save_all_interactions: bool = True
    
    def __post_init__(self):
        if self.max_workers < 1:
            raise ValueError("max_workers debe ser al menos 1")


@dataclass
class APIKeysConfig:
    """Configuración de API Keys"""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    deepinfra_api_key: Optional[str] = None
    wolframalpha_app_id: Optional[str] = None
    
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)
    
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)
    
    def has_google(self) -> bool:
        return bool(self.google_api_key)
    
    def has_deepinfra(self) -> bool:
        return bool(self.deepinfra_api_key)


class ConfigManager:
    """
    Gestor de configuración centralizado (Singleton)
    
    Carga configuración desde:
    1. Variables de entorno (.env)
    2. Archivos JSON
    3. Valores por defecto
    
    Usage:
        config = ConfigManager.get_instance()
        max_tokens = config.inference.max_tokens
        primary_gpu = config.gpu.primary_gpu_id
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Evitar reinicialización
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.logger = logging.getLogger("ConfigManager")
        
        # Cargar configuraciones
        self.gpu = self._load_gpu_config()
        self.inference = self._load_inference_config()
        self.rag = self._load_rag_config()
        self.whisper = self._load_whisper_config()
        self.tts = self._load_tts_config()
        self.audio = self._load_audio_config()
        self.logging_config = self._load_logging_config()
        self.metrics = self._load_metrics_config()
        self.security = self._load_security_config()
        self.system = self._load_system_config()
        self.api_keys = self._load_api_keys()
        
        self.logger.info("ConfigManager initialized successfully")
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """Obtener instancia singleton"""
        return cls()
    
    def _get_env(self, key: str, default: Any = None, cast: type = str) -> Any:
        """Helper para obtener variable de entorno con casting"""
        value = os.getenv(key, default)
        if value is None:
            return default
        
        try:
            if cast == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif cast == list:
                return [item.strip() for item in value.split(',') if item.strip()]
            else:
                return cast(value)
        except (ValueError, TypeError):
            self.logger.warning(f"Error parsing env var {key}={value}, using default {default}")
            return default
    
    def _load_gpu_config(self) -> GPUConfig:
        """Cargar configuración GPU"""
        return GPUConfig(
            primary_gpu_id=self._get_env('PRIMARY_GPU_ID', 0, int),
            secondary_gpu_id=self._get_env('SECONDARY_GPU_ID', 1, int),
            vram_buffer_mb=self._get_env('VRAM_BUFFER_MB', 500, int),
            gpu_memory_utilization=self._get_env('GPU_MEMORY_UTILIZATION', 0.90, float),
            enable_monitoring=self._get_env('ENABLE_GPU_MONITORING', True, bool),
            monitor_interval=self._get_env('GPU_MONITOR_INTERVAL', 5, int)
        )
    
    def _load_inference_config(self) -> InferenceConfig:
        """Cargar configuración de inferencia"""
        backend_str = self._get_env('DEFAULT_BACKEND', 'vllm', str)
        backend = BackendType(backend_str) if backend_str in [b.value for b in BackendType] else BackendType.VLLM
        
        return InferenceConfig(
            default_backend=backend,
            max_tokens=self._get_env('MAX_TOKENS', 4096, int),
            default_temperature=self._get_env('DEFAULT_TEMPERATURE', 0.7, float),
            preferred_quantization=self._get_env('PREFERRED_QUANTIZATION', 'awq', str),
            inference_timeout=self._get_env('INFERENCE_TIMEOUT', 60, int)
        )
    
    def _load_rag_config(self) -> RAGConfig:
        """Cargar configuración RAG"""
        return RAGConfig(
            chroma_db_path=self._get_env('CHROMA_DB_PATH', './vectorstore/chromadb', str),
            embedding_model=self._get_env('EMBEDDING_MODEL', 'BAAI/bge-m3', str),
            embedding_device=self._get_env('EMBEDDING_DEVICE', 'cuda:1', str),
            max_results=self._get_env('RAG_MAX_RESULTS', 5, int),
            similarity_threshold=self._get_env('RAG_SIMILARITY_THRESHOLD', 0.7, float),
            enable_rag=self._get_env('ENABLE_RAG', True, bool)
        )
    
    def _load_whisper_config(self) -> WhisperConfig:
        """Cargar configuración Whisper"""
        return WhisperConfig(
            model=self._get_env('WHISPER_MODEL', 'large-v3-turbo', str),
            backend=self._get_env('WHISPER_BACKEND', 'faster-whisper', str),
            device=self._get_env('WHISPER_DEVICE', 'cuda:1', str),
            compute_type=self._get_env('WHISPER_COMPUTE_TYPE', 'int8', str),
            language=self._get_env('WHISPER_LANGUAGE', 'es', str)
        )
    
    def _load_tts_config(self) -> TTSConfig:
        """Cargar configuración TTS"""
        return TTSConfig(
            engine=self._get_env('TTS_ENGINE', 'gtts', str),
            language=self._get_env('TTS_LANGUAGE', 'es', str),
            speed=self._get_env('TTS_SPEED', 1.0, float),
            volume=self._get_env('TTS_VOLUME', 0.8, float)
        )
    
    def _load_audio_config(self) -> AudioConfig:
        """Cargar configuración de audio"""
        device_idx = self._get_env('AUDIO_DEVICE_INDEX', None, str)
        device_idx = int(device_idx) if device_idx and device_idx.isdigit() else None
        
        return AudioConfig(
            device_index=device_idx,
            sample_rate=self._get_env('AUDIO_SAMPLE_RATE', 16000, int),
            channels=self._get_env('AUDIO_CHANNELS', 1, int),
            energy_threshold=self._get_env('ENERGY_THRESHOLD', 250, int),
            dynamic_energy_adjustment=self._get_env('DYNAMIC_ENERGY_ADJUSTMENT', True, bool)
        )
    
    def _load_logging_config(self) -> LoggingConfig:
        """Cargar configuración de logging"""
        fmt_str = self._get_env('LOG_FORMAT', 'text', str)
        log_format = LogFormat(fmt_str) if fmt_str in [f.value for f in LogFormat] else LogFormat.TEXT
        
        return LoggingConfig(
            log_level=self._get_env('LOG_LEVEL', 'INFO', str),
            log_dir=self._get_env('LOG_DIR', './logs', str),
            log_format=log_format,
            structured_logging=self._get_env('STRUCTURED_LOGGING', False, bool),
            max_size_mb=self._get_env('LOG_MAX_SIZE_MB', 10, int),
            backup_count=self._get_env('LOG_BACKUP_COUNT', 5, int)
        )
    
    def _load_metrics_config(self) -> MetricsConfig:
        """Cargar configuración de métricas"""
        return MetricsConfig(
            enable_metrics=self._get_env('ENABLE_METRICS', True, bool),
            metrics_log_path=self._get_env('METRICS_LOG_PATH', './logs/metrics.jsonl', str),
            enable_profiling=self._get_env('ENABLE_PROFILING', False, bool)
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """Cargar configuración de seguridad"""
        return SecurityConfig(
            blocked_terms=self._get_env('BLOCKED_TERMS', [], list),
            strict_input_validation=self._get_env('STRICT_INPUT_VALIDATION', True, bool),
            max_query_length=self._get_env('MAX_QUERY_LENGTH', 5000, int)
        )
    
    def _load_system_config(self) -> SystemConfig:
        """Cargar configuración del sistema"""
        return SystemConfig(
            max_workers=self._get_env('MAX_WORKERS', 2, int),
            cpu_threshold=self._get_env('CPU_THRESHOLD', 80, int),
            memory_threshold=self._get_env('MEMORY_THRESHOLD', 85, int),
            disk_threshold=self._get_env('DISK_THRESHOLD', 90, int),
            debug_mode=self._get_env('DEBUG_MODE', False, bool),
            save_all_interactions=self._get_env('SAVE_ALL_INTERACTIONS', True, bool)
        )
    
    def _load_api_keys(self) -> APIKeysConfig:
        """Cargar API keys"""
        return APIKeysConfig(
            openai_api_key=self._get_env('OPENAI_API_KEY', None, str),
            anthropic_api_key=self._get_env('ANTHROPIC_API_KEY', None, str),
            google_api_key=self._get_env('GOOGLE_API_KEY', None, str),
            deepinfra_api_key=self._get_env('DEEPINFRA_API_KEY', None, str),
            wolframalpha_app_id=self._get_env('WOLFRAMALPHA_APP_ID', None, str)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Exportar configuración a diccionario"""
        return {
            'gpu': asdict(self.gpu),
            'inference': {**asdict(self.inference), 'default_backend': self.inference.default_backend.value},
            'rag': asdict(self.rag),
            'whisper': asdict(self.whisper),
            'tts': asdict(self.tts),
            'audio': asdict(self.audio),
            'logging': {**asdict(self.logging_config), 'log_format': self.logging_config.log_format.value},
            'metrics': asdict(self.metrics),
            'security': asdict(self.security),
            'system': asdict(self.system),
            'api_keys': {'has_openai': self.api_keys.has_openai(), 'has_anthropic': self.api_keys.has_anthropic()}
        }
    
    def save_to_file(self, path: str):
        """Guardar configuración a archivo JSON"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        self.logger.info(f"Configuration saved to {path}")
    
    def reload(self):
        """Recargar configuración"""
        self._initialized = False
        self.__init__()


# Instancia global para conveniencia
config = ConfigManager.get_instance()
