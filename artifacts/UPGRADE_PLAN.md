# 🚀 Plan de Actualización - Jarvis IA V2

**Fecha:** 6 de Noviembre 2025  
**Hardware Disponible:**
- GPU1: RTX 5070 Ti (16GB VRAM, Compute 12.0)
- GPU2: RTX 2060 (6GB VRAM, Compute 7.5)
- CPU: AMD Ryzen 9 9950X3D (16C/32T)

---

## 📊 Estado Actual vs Objetivo

### Actual
- ❌ Llama-3.2-3B (subutiliza hardware)
- ❌ Whisper original (lento)
- ❌ Sin embeddings/RAG
- ❌ Sin orquestación multi-GPU
- ❌ APIs caras para todo

### Objetivo
- ✅ Llama-3.3-70B + Qwen2.5-32B (GPU1)
- ✅ Llama-3.2-8B + Whisper-v3-turbo (GPU2)
- ✅ Sistema RAG con embeddings
- ✅ Orquestador inteligente multi-GPU
- ✅ APIs solo para casos complejos (60-80% ahorro)

---

## 🏗️ Arquitectura Multi-GPU Propuesta

```
┌─────────────────────────────────────────────────────────┐
│                   JARVIS ORCHESTRATOR                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Intelligent Router & Load Balancer       │  │
│  │  (Complejidad, VRAM, Latencia, Costo, Cache)    │  │
│  └──────────────────────────────────────────────────┘  │
└────────────┬──────────────┬──────────────┬─────────────┘
             │              │              │
    ┌────────▼────────┐    ▼              ▼
    │   GPU1 (16GB)   │   GPU2 (6GB)      CPU
    │─────────────────│   ──────────      ────────
    │ Llama-70B (AWQ) │   Llama-8B        BGE-M3
    │ Qwen2.5-32B     │   Whisper-v3      ChromaDB
    │ DeepSeek-14B    │   Embeddings      Fallback
    │ [vLLM Server]   │   [HF+Flash-Attn] [llama.cpp]
    └─────────────────┘
             │
    ┌────────▼────────────────────────────┐
    │      API External (Fallback)        │
    │  GPT-4o-mini  │  Claude-3.5-Sonnet  │
    │  Gemini-Flash │  DeepSeek-V3        │
    └─────────────────────────────────────┘
```

### Distribución de Modelos

#### GPU1 (RTX 5070 Ti - 16GB)
| Modelo | Tamaño | Cuantización | VRAM | Uso |
|--------|--------|--------------|------|-----|
| Llama-3.3-70B-Instruct | 70B | AWQ 4-bit | ~14GB | Razonamiento complejo |
| Qwen2.5-32B-Instruct | 32B | AWQ 4-bit | ~10GB | Matemáticas, código |
| DeepSeek-R1-Distill-14B | 14B | GPTQ 4-bit | ~9GB | Razonamiento paso a paso |

**Estrategia:** Cargar 1 modelo grande a la vez con vLLM, swap automático según demanda.

#### GPU2 (RTX 2060 - 6GB)
| Modelo | Tamaño | Cuantización | VRAM | Uso |
|--------|--------|--------------|------|-----|
| Llama-3.2-8B-Instruct | 8B | FP16 | ~5GB | Chat rápido, consultas simples |
| Whisper-large-v3-turbo | 809M | INT8 | ~2GB | ASR en tiempo real |
| BGE-M3 | 568M | FP32 | ~1.5GB | Embeddings para RAG |

**Estrategia:** Multi-modelo concurrente (8GB total con FlashAttention).

#### CPU (Ryzen 9 9950X3D)
- **Embeddings:** BGE-M3 (fallback)
- **ChromaDB/FAISS:** Vector store
- **Preprocessing:** Tokenización, limpieza
- **Fallback:** llama.cpp CPU mode

---

## 📦 Fase 1: Actualización de Dependencias

### 1.1 Nuevo `requirements.txt`

```python
# Core Deep Learning
torch>=2.6.0
torchvision>=0.19.0
torchaudio>=2.5.0

# Transformers & Optimization
transformers>=4.48.1
accelerate>=0.36.0
bitsandbytes>=0.45.0
flash-attn>=2.7.0
peft>=0.14.0

# Inference Backends
vllm>=0.6.5
llama-cpp-python[server]>=0.3.5
ctranslate2>=4.5.0
optimum>=1.23.0

# Embeddings & Vector Stores
sentence-transformers>=3.3.0
chromadb>=0.5.20
faiss-cpu>=1.9.0

# Speech
faster-whisper>=1.1.0
pyaudio>=0.2.14
sounddevice>=0.5.1
pygame>=2.6.1
gtts>=2.5.4

# APIs
openai>=1.60.2
anthropic>=0.43.0
google-generativeai>=0.8.4

# Utils
python-dotenv>=1.0.1
psutil>=6.1.1
colorama>=0.4.6
prompt-toolkit>=3.0.50
pynvml>=11.5.3

# System
google-api-python-client>=2.159.0
google-auth-oauthlib>=1.2.1
wolframalpha>=5.0.0
pytz>=2024.2
sympy>=1.13.1
```

### 1.2 Script de Instalación

```bash
#!/bin/bash
# install_upgrade.sh

set -e

echo "🚀 Jarvis IA V2 - Upgrade Installation"
echo "========================================"

# Verificar CUDA
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ NVIDIA drivers not found!"
    exit 1
fi

echo "✅ GPUs detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Crear entorno virtual
echo "📦 Creating virtual environment..."
python3.10 -m venv venv_v2
source venv_v2/bin/activate

# Actualizar pip
pip install --upgrade pip setuptools wheel

# Instalar PyTorch con CUDA 12.4
echo "🔥 Installing PyTorch with CUDA 12.4..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Instalar flash-attention (requiere compilación)
echo "⚡ Installing Flash Attention..."
pip install flash-attn --no-build-isolation

# Instalar vLLM
echo "🚄 Installing vLLM..."
pip install vllm

# Instalar llama-cpp-python con CUDA
echo "🦙 Installing llama-cpp-python with CUDA..."
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python[server]

# Instalar el resto
echo "📚 Installing remaining packages..."
pip install -r requirements_v2.txt

echo "✅ Installation complete!"
echo "Run: source venv_v2/bin/activate"
```

---

## 🧠 Fase 2: Nuevo Sistema de Modelos Locales

### 2.1 Estructura de Directorios

```
jarvisIAV2/
├── models/
│   ├── llm/
│   │   ├── llama-3.3-70b-awq/          # GPU1 - Principal
│   │   ├── qwen2.5-32b-awq/             # GPU1 - Técnico
│   │   ├── deepseek-r1-14b-gptq/        # GPU1 - Razonamiento
│   │   └── llama-3.2-8b-instruct/       # GPU2 - Rápido
│   ├── whisper/
│   │   └── large-v3-turbo-ct2/          # GPU2 - ASR
│   └── embeddings/
│       ├── bge-m3/                      # CPU/GPU2 - RAG
│       └── e5-mistral-7b/               # GPU2 - Opcional
├── vectorstore/
│   └── chromadb/                        # Memoria de largo plazo
└── cache/
    └── model_cache/                     # Cache compartido
```

### 2.2 Script de Descarga de Modelos

```python
# scripts/download_models.py

from huggingface_hub import snapshot_download
import os

MODELS = [
    # LLMs para GPU1
    ("casperhansen/llama-3.3-70b-instruct-awq", "models/llm/llama-3.3-70b-awq"),
    ("Qwen/Qwen2.5-32B-Instruct-AWQ", "models/llm/qwen2.5-32b-awq"),
    ("solidrust/DeepSeek-R1-Distill-Qwen-14B-GPTQ", "models/llm/deepseek-r1-14b-gptq"),
    
    # LLM para GPU2
    ("meta-llama/Llama-3.2-8B-Instruct", "models/llm/llama-3.2-8b-instruct"),
    
    # Embeddings
    ("BAAI/bge-m3", "models/embeddings/bge-m3"),
]

def download_model(repo_id, local_dir):
    print(f"⬇️  Downloading {repo_id}...")
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False
    )
    print(f"✅ Downloaded to {local_dir}")

if __name__ == "__main__":
    for repo_id, local_dir in MODELS:
        if not os.path.exists(local_dir):
            download_model(repo_id, local_dir)
        else:
            print(f"⏭️  {local_dir} already exists, skipping...")
    
    print("\n🎉 All models downloaded!")
```

### 2.3 Whisper con CTranslate2

```bash
# Convertir Whisper a CTranslate2
ct2-transformers-converter \
    --model openai/whisper-large-v3-turbo \
    --output_dir models/whisper/large-v3-turbo-ct2 \
    --quantization int8
```

---

## ⚙️ Fase 3: Orquestador Multi-GPU

### 3.1 `src/modules/llm/model_orchestrator.py`

```python
import torch
import os
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import psutil
import pynvml

class ModelBackend(Enum):
    VLLM = "vllm"
    TRANSFORMERS = "transformers"
    LLAMA_CPP = "llama_cpp"
    API = "api"

@dataclass
class ModelConfig:
    name: str
    path: str
    backend: ModelBackend
    gpu_id: Optional[int]
    vram_required: int  # MB
    difficulty_range: Tuple[int, int]
    quantization: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7

class ModelOrchestrator:
    """
    Orquestador inteligente multi-GPU para Jarvis IA V2
    
    Maneja:
    - Selección de modelo según complejidad
    - Carga/descarga dinámica de modelos
    - Monitoreo de VRAM
    - Fallback a APIs
    - Cache de respuestas
    """
    
    def __init__(self, config_path: str = "src/config/models_v2.json"):
        self.config = self._load_config(config_path)
        self.loaded_models: Dict[str, Any] = {}
        self.gpu_stats = {}
        
        # Inicializar NVML para monitoreo
        pynvml.nvmlInit()
        self.gpu_count = pynvml.nvmlDeviceGetCount()
        
        # Cargar modelos por defecto
        self._init_default_models()
    
    def _get_gpu_memory(self, gpu_id: int) -> Tuple[int, int]:
        """Retorna (usado, total) en MB"""
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return info.used // 1024**2, info.total // 1024**2
    
    def _can_load_model(self, model_config: ModelConfig) -> bool:
        """Verifica si hay espacio en GPU para cargar el modelo"""
        if model_config.gpu_id is None:
            return True  # CPU siempre disponible
        
        used, total = self._get_gpu_memory(model_config.gpu_id)
        available = total - used
        
        # Buffer de 500MB
        return available >= (model_config.vram_required + 500)
    
    def _load_vllm_model(self, config: ModelConfig):
        """Carga modelo con vLLM (GPU1 - modelos grandes)"""
        from vllm import LLM, SamplingParams
        
        os.environ['CUDA_VISIBLE_DEVICES'] = str(config.gpu_id)
        
        llm = LLM(
            model=config.path,
            quantization=config.quantization,
            gpu_memory_utilization=0.90,
            max_model_len=4096,
            tensor_parallel_size=1
        )
        
        return {
            'model': llm,
            'backend': ModelBackend.VLLM,
            'config': config
        }
    
    def _load_transformers_model(self, config: ModelConfig):
        """Carga modelo con Transformers + FlashAttention (GPU2)"""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        device = f"cuda:{config.gpu_id}" if config.gpu_id is not None else "cpu"
        
        tokenizer = AutoTokenizer.from_pretrained(config.path)
        model = AutoModelForCausalLM.from_pretrained(
            config.path,
            torch_dtype=torch.float16,
            device_map=device,
            attn_implementation="flash_attention_2"
        )
        
        return {
            'model': model,
            'tokenizer': tokenizer,
            'backend': ModelBackend.TRANSFORMERS,
            'config': config
        }
    
    def get_response(
        self, 
        query: str, 
        difficulty: int,
        force_model: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Obtiene respuesta del modelo apropiado
        
        Returns:
            (respuesta, nombre_modelo)
        """
        # Seleccionar modelo
        if force_model:
            model_name = force_model
        else:
            model_name = self._select_model_by_difficulty(difficulty)
        
        # Cargar si no está en memoria
        if model_name not in self.loaded_models:
            self._load_model(model_name)
        
        # Generar respuesta
        model_data = self.loaded_models[model_name]
        
        if model_data['backend'] == ModelBackend.VLLM:
            response = self._generate_vllm(model_data, query)
        elif model_data['backend'] == ModelBackend.TRANSFORMERS:
            response = self._generate_transformers(model_data, query)
        else:
            response = self._generate_api(model_data, query)
        
        return response, model_name
    
    def _generate_vllm(self, model_data, query: str) -> str:
        """Genera con vLLM"""
        from vllm import SamplingParams
        
        sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.9,
            max_tokens=2048
        )
        
        outputs = model_data['model'].generate([query], sampling_params)
        return outputs[0].outputs[0].text.strip()
    
    def _generate_transformers(self, model_data, query: str) -> str:
        """Genera con Transformers"""
        inputs = model_data['tokenizer'](query, return_tensors="pt").to(
            model_data['model'].device
        )
        
        with torch.inference_mode():
            outputs = model_data['model'].generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.7,
                do_sample=True
            )
        
        response = model_data['tokenizer'].decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )
        return response.strip()
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas de uso"""
        stats = {
            'loaded_models': list(self.loaded_models.keys()),
            'gpus': []
        }
        
        for i in range(self.gpu_count):
            used, total = self._get_gpu_memory(i)
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            
            stats['gpus'].append({
                'id': i,
                'name': name,
                'vram_used': used,
                'vram_total': total,
                'vram_percent': (used / total) * 100
            })
        
        return stats
```

### 3.2 Configuración de Modelos `models_v2.json`

```json
{
  "models": {
    "llama-70b": {
      "name": "Llama-3.3-70B-Instruct",
      "path": "models/llm/llama-3.3-70b-awq",
      "backend": "vllm",
      "gpu_id": 0,
      "vram_required": 14000,
      "difficulty_range": [70, 100],
      "quantization": "awq",
      "priority": 1
    },
    "qwen-32b": {
      "name": "Qwen2.5-32B-Instruct",
      "path": "models/llm/qwen2.5-32b-awq",
      "backend": "vllm",
      "gpu_id": 0,
      "vram_required": 10000,
      "difficulty_range": [60, 85],
      "quantization": "awq",
      "priority": 2,
      "specialties": ["math", "code", "technical"]
    },
    "deepseek-14b": {
      "name": "DeepSeek-R1-Distill-14B",
      "path": "models/llm/deepseek-r1-14b-gptq",
      "backend": "vllm",
      "gpu_id": 0,
      "vram_required": 9000,
      "difficulty_range": [65, 95],
      "quantization": "gptq",
      "priority": 3,
      "specialties": ["reasoning", "math", "analysis"]
    },
    "llama-8b": {
      "name": "Llama-3.2-8B-Instruct",
      "path": "models/llm/llama-3.2-8b-instruct",
      "backend": "transformers",
      "gpu_id": 1,
      "vram_required": 5000,
      "difficulty_range": [1, 60],
      "priority": 4
    }
  },
  "api_models": {
    "gpt-4o-mini": {
      "difficulty_range": [75, 100],
      "cost_per_1k": 0.00015,
      "fallback": true
    },
    "claude-3.5-sonnet": {
      "difficulty_range": [80, 100],
      "cost_per_1k": 0.003,
      "specialties": ["reasoning", "writing"]
    },
    "gemini-flash-thinking": {
      "difficulty_range": [50, 90],
      "cost_per_1k": 0.0001,
      "fast": true
    },
    "deepseek-chat": {
      "difficulty_range": [60, 100],
      "cost_per_1k": 0.00014,
      "specialties": ["math", "code"]
    }
  },
  "routing": {
    "prefer_local": true,
    "max_local_latency": 5.0,
    "fallback_on_oom": true,
    "cache_responses": true
  }
}
```

---

## 🎙️ Fase 4: Sistema de Voz Moderno

### 4.1 Faster-Whisper Integration

```python
# src/modules/voice/whisper_handler.py

from faster_whisper import WhisperModel
import numpy as np
import torch

class WhisperHandler:
    """
    Whisper optimizado con CTranslate2 en GPU2
    
    Mejoras:
    - 4x más rápido que openai-whisper
    - Menor uso de VRAM
    - Soporte para streaming
    """
    
    def __init__(
        self,
        model_path: str = "models/whisper/large-v3-turbo-ct2",
        device: str = "cuda",
        device_index: int = 1,  # GPU2
        compute_type: str = "int8"
    ):
        self.model = WhisperModel(
            model_path,
            device=device,
            device_index=device_index,
            compute_type=compute_type,
            num_workers=4
        )
        
        print(f"✅ Whisper loaded on GPU {device_index}")
    
    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "es",
        task: str = "transcribe"
    ) -> str:
        """Transcribe audio a texto"""
        
        segments, info = self.model.transcribe(
            audio,
            language=language,
            task=task,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500
            )
        )
        
        # Concatenar todos los segmentos
        transcription = " ".join([seg.text for seg in segments])
        
        return transcription.strip()
    
    def transcribe_streaming(self, audio_stream):
        """Transcripción en tiempo real (futuro)"""
        # TODO: Implementar con VAD + chunks
        pass
```

---

## 🧩 Fase 5: Sistema RAG con Embeddings

### 5.1 Embedding Manager

```python
# src/modules/embeddings/embedding_manager.py

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import torch
from typing import List, Dict

class EmbeddingManager:
    """
    Sistema de embeddings y RAG para Jarvis
    
    - BGE-M3 para embeddings multilingües
    - ChromaDB para almacenamiento vectorial
    - Búsqueda semántica de memoria de largo plazo
    """
    
    def __init__(
        self,
        model_name: str = "models/embeddings/bge-m3",
        device: str = "cuda:1",  # GPU2
        chroma_path: str = "vectorstore/chromadb"
    ):
        # Cargar modelo de embeddings
        self.model = SentenceTransformer(
            model_name,
            device=device
        )
        
        # Inicializar ChromaDB
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=chroma_path
        ))
        
        # Crear colección de memoria
        self.memory_collection = self.chroma_client.get_or_create_collection(
            name="jarvis_memory",
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"✅ Embeddings ready on {device}")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings para textos"""
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        return embeddings.tolist()
    
    def add_to_memory(
        self,
        texts: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ):
        """Añade interacciones a la memoria de largo plazo"""
        embeddings = self.embed(texts)
        
        self.memory_collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
    
    def search_memory(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """Busca en la memoria de largo plazo"""
        query_embedding = self.embed([query])[0]
        
        results = self.memory_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        return [
            {
                "text": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )
        ]
    
    def get_context_for_query(
        self,
        query: str,
        max_context: int = 3
    ) -> str:
        """Obtiene contexto relevante de la memoria para una consulta"""
        
        memories = self.search_memory(query, n_results=max_context)
        
        if not memories:
            return ""
        
        context_parts = []
        for i, mem in enumerate(memories, 1):
            context_parts.append(f"Memoria {i}: {mem['text']}")
        
        return "\n".join(context_parts)
```

---

## 📈 Fase 6: Benchmarking y Monitoreo

### 6.1 Sistema de Métricas

```python
# src/utils/metrics_tracker.py

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import pynvml

@dataclass
class QueryMetrics:
    query: str
    model_used: str
    difficulty: int
    latency: float  # seconds
    tokens_generated: int
    vram_used: Dict[int, int]  # {gpu_id: mb}
    cost: float  # USD
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        return {
            'query': self.query[:100],  # Truncar
            'model': self.model_used,
            'difficulty': self.difficulty,
            'latency': round(self.latency, 3),
            'tokens': self.tokens_generated,
            'vram': self.vram_used,
            'cost': self.cost,
            'timestamp': self.timestamp.isoformat()
        }

class MetricsTracker:
    """
    Seguimiento de métricas de rendimiento
    
    - Latencia por modelo
    - Uso de VRAM
    - Costos de API
    - Tokens generados
    """
    
    def __init__(self, log_path: str = "logs/metrics.jsonl"):
        self.log_path = log_path
        self.session_metrics: List[QueryMetrics] = []
        
        pynvml.nvmlInit()
        self.gpu_count = pynvml.nvmlDeviceGetCount()
    
    def track_query(
        self,
        query: str,
        model: str,
        difficulty: int,
        latency: float,
        tokens: int,
        cost: float = 0.0
    ):
        """Registra métricas de una consulta"""
        
        # Capturar VRAM actual
        vram = {}
        for i in range(self.gpu_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram[i] = info.used // 1024**2
        
        metrics = QueryMetrics(
            query=query,
            model_used=model,
            difficulty=difficulty,
            latency=latency,
            tokens_generated=tokens,
            vram_used=vram,
            cost=cost
        )
        
        self.session_metrics.append(metrics)
        self._log_metric(metrics)
    
    def _log_metric(self, metric: QueryMetrics):
        """Escribe métrica a archivo"""
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(metric.to_dict()) + '\n')
    
    def get_session_stats(self) -> Dict:
        """Obtiene estadísticas de la sesión actual"""
        if not self.session_metrics:
            return {}
        
        total_queries = len(self.session_metrics)
        avg_latency = sum(m.latency for m in self.session_metrics) / total_queries
        total_tokens = sum(m.tokens_generated for m in self.session_metrics)
        total_cost = sum(m.cost for m in self.session_metrics)
        
        # Uso por modelo
        model_usage = {}
        for m in self.session_metrics:
            model_usage[m.model_used] = model_usage.get(m.model_used, 0) + 1
        
        return {
            'total_queries': total_queries,
            'avg_latency': round(avg_latency, 3),
            'total_tokens': total_tokens,
            'total_cost': round(total_cost, 4),
            'model_usage': model_usage
        }
    
    def print_stats(self):
        """Imprime estadísticas formateadas"""
        stats = self.get_session_stats()
        
        print("\n" + "="*50)
        print("📊 SESSION STATS")
        print("="*50)
        print(f"Total Queries: {stats['total_queries']}")
        print(f"Avg Latency: {stats['avg_latency']}s")
        print(f"Total Tokens: {stats['total_tokens']}")
        print(f"Total Cost: ${stats['total_cost']}")
        print("\nModel Usage:")
        for model, count in stats['model_usage'].items():
            print(f"  - {model}: {count}")
        print("="*50 + "\n")
```

---

## 🚀 Fase 7: Implementación Paso a Paso

### Semana 1: Fundamentos
- [ ] Backup completo del proyecto actual
- [ ] Crear entorno virtual nuevo
- [ ] Instalar nuevas dependencias
- [ ] Verificar compilación de Flash Attention
- [ ] Testear PyTorch + CUDA en ambas GPUs

### Semana 2: Modelos Locales
- [ ] Descargar Llama-3.3-70B-AWQ
- [ ] Descargar Qwen2.5-32B-AWQ
- [ ] Descargar Llama-3.2-8B
- [ ] Convertir Whisper a CTranslate2
- [ ] Descargar BGE-M3
- [ ] Testear carga de modelos individuales

### Semana 3: Orquestador
- [ ] Implementar `ModelOrchestrator`
- [ ] Integrar vLLM para GPU1
- [ ] Integrar Transformers para GPU2
- [ ] Testear cambio dinámico de modelos
- [ ] Implementar monitoreo de VRAM

### Semana 4: Voz y Embeddings
- [ ] Migrar a `faster-whisper`
- [ ] Implementar `EmbeddingManager`
- [ ] Configurar ChromaDB
- [ ] Integrar sistema RAG
- [ ] Testear búsqueda semántica

### Semana 5: Integración
- [ ] Actualizar `ModelManager` para usar `ModelOrchestrator`
- [ ] Implementar router inteligente
- [ ] Añadir `MetricsTracker`
- [ ] Migrar APIs a versiones nuevas
- [ ] Testing end-to-end

### Semana 6: Optimización
- [ ] Benchmarking de todos los modelos
- [ ] Ajuste de hiperparámetros
- [ ] Optimización de routing
- [ ] Documentación completa
- [ ] Scripts de deploy

---

## 📊 Resultados Esperados

### Rendimiento

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Latencia (simple) | 2-3s | 0.5-1s | **3x más rápido** |
| Latencia (complejo) | 5-8s | 2-4s | **2x más rápido** |
| Calidad (simple) | 6/10 | 8/10 | **+33%** |
| Calidad (complejo) | 7/10 | 9/10 | **+29%** |
| Uso de VRAM GPU1 | 3GB | 14GB | **+367%** |
| Uso de VRAM GPU2 | 0GB | 5GB | **Activado** |
| Costo API/mes | $50 | $10-15 | **-70-80%** |
| Whisper latency | 3-5s | 0.8-1.2s | **4x más rápido** |

### Capacidades Nuevas
- ✅ RAG con memoria de largo plazo
- ✅ Embeddings semánticos
- ✅ Razonamiento paso a paso (DeepSeek-R1)
- ✅ Mejor comprensión de código/matemáticas (Qwen2.5)
- ✅ Respuestas más elaboradas (70B vs 3B)
- ✅ Multi-GPU orchestration
- ✅ Monitoreo en tiempo real

---

## 🛠️ Troubleshooting

### Error: OOM en GPU1
```bash
# Reducir gpu_memory_utilization en vLLM
# Cambiar a modelo 32B en lugar de 70B
# Usar cuantización más agresiva (3-bit)
```

### Error: Flash Attention no compila
```bash
# Instalar dependencias
sudo apt install ninja-build
pip install packaging

# Reinstalar
pip uninstall flash-attn
MAX_JOBS=4 pip install flash-attn --no-build-isolation
```

### Error: vLLM no encuentra CUDA
```bash
# Verificar CUDA
nvcc --version

# Reinstalar vLLM con CUDA
pip uninstall vllm
pip install vllm --no-cache-dir
```

### Latencia alta en modelos locales
```bash
# Verificar que usa GPU
nvidia-smi

# Ajustar batch size y workers
# Habilitar CUDA graphs en vLLM
```

---

## 📚 Recursos

### Documentación
- [vLLM Docs](https://docs.vllm.ai/)
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)
- [Sentence Transformers](https://www.sbert.net/)
- [ChromaDB](https://docs.trychroma.com/)

### Modelos Recomendados
- [Llama-3.3-70B-AWQ](https://huggingface.co/casperhansen/llama-3.3-70b-instruct-awq)
- [Qwen2.5-32B](https://huggingface.co/Qwen/Qwen2.5-32B-Instruct-AWQ)
- [DeepSeek-R1-14B](https://huggingface.co/solidrust/DeepSeek-R1-Distill-Qwen-14B-GPTQ)
- [BGE-M3](https://huggingface.co/BAAI/bge-m3)

### Comunidad
- [vLLM Discord](https://discord.gg/vllm)
- [HuggingFace Forums](https://discuss.huggingface.co/)
- [r/LocalLLaMA](https://reddit.com/r/LocalLLaMA)

---

## ✅ Checklist Final

- [ ] Código actualizado y testeado
- [ ] Todos los modelos descargados
- [ ] Benchmarks completados
- [ ] Documentación actualizada
- [ ] Scripts de instalación validados
- [ ] Sistema de monitoreo activo
- [ ] Backup del sistema antiguo
- [ ] Plan de rollback definido

---

**🎯 Próximo Paso:** Ejecutar `install_upgrade.sh` y comenzar Semana 1.
