# Sistema de Logs Limpios para Jarvis

## 🎯 Objetivo
Mantener la terminal limpia durante la ejecución de Jarvis, suprimiendo logs verbosos de librerías externas mientras se preserva la interfaz de usuario.

## 📋 Problemas Identificados

### Antes de la Mejora
Cuando se ejecutaba Jarvis, aparecían logs técnicos que contaminaban la interfaz:

```
[Gloo] Rank 0 is connected to 0 peer ranks. Expected number of connected peer ranks is : 0
Loading safetensors checkpoint shards:   0% Completed | 0/3 [00:00<?, ?it/s]
Loading safetensors checkpoint shards:  33% Completed | 1/3 [00:00<00:00,  5.14it/s]
Loading safetensors checkpoint shards:  67% Completed | 2/3 [00:00<00:00,  3.25it/s]
Loading safetensors checkpoint shards: 100% Completed | 3/3 [00:00<00:00,  2.89it/s]
Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): 100%|█████| 11/11 [00:02<00:00,  5.15it/s]
Capturing CUDA graphs (decode, FULL): 100%|████████████████| 7/7 [00:01<00:00,  5.09it/s]
Adding requests: 100%|████████████████████████████████| 1/1 [00:00<00:00, 529.85it/s]
```

**Fuentes de logs verbosos:**
- vLLM (safetensors, CUDA graphs, engine core)
- torch.distributed (Gloo)
- tqdm (barras de progreso)
- transformers, sentence_transformers
- httpx, asyncio

## 🛠️ Solución Implementada

### 1. Nuevo Módulo: `src/utils/log_suppressor.py`

Implementa un sistema robusto de supresión de logs con:

#### **Context Manager para Captura de Output**
```python
class SuppressedOutput:
    """Context manager para suprimir stdout/stderr selectivamente"""
    - Captura stdout/stderr durante operaciones ruidosas
    - Permite redirección a logs si se necesita debug
    - Siempre muestra errores críticos
```

#### **Configuración de Entorno Silencioso**
```python
def configure_quiet_mode():
    """Configura variables de entorno y loggers para silenciar librerías"""
    - TF_CPP_MIN_LOG_LEVEL=3
    - TRANSFORMERS_VERBOSITY=error
    - VLLM_LOGGING_LEVEL=ERROR
    - GLOO_LOG_LEVEL=ERROR
    - Configura 15+ loggers problemáticos
```

#### **Supresión de tqdm**
```python
def suppress_tqdm():
    """Monkey-patch para deshabilitar barras de progreso"""
    - Intercepta tqdm.tqdm y tqdm.trange
    - Establece disable=True por defecto
```

#### **Context Manager para Carga de Modelos**
```python
@contextmanager
def model_loading_context(debug_mode: bool = False):
    """Context manager específico para cargar modelos sin contaminar terminal"""
    - Si debug_mode=True, muestra todo
    - Si debug_mode=False, suprime output completo
    - Automático basado en JARVIS_DEBUG
```

### 2. Integración en `main.py`

```python
# ANTES de cualquier import pesado
from src.utils.log_suppressor import setup_clean_terminal
setup_clean_terminal()
```

**Beneficios:**
- Configuración temprana antes de imports
- Respeta flag `--debug` del usuario
- Centralizado y mantenible

### 3. Integración en `model_orchestrator.py`

```python
from src.utils.log_suppressor import model_loading_context

def _load_inner():
    debug_mode = os.environ.get('JARVIS_DEBUG') == '1'
    with model_loading_context(debug_mode=debug_mode):
        llm = LLM(model=config.path, ...)
```

**Mejoras:**
- Reemplaza el intento anterior con StringIO (no robusto)
- Context manager adecuado con __enter__/__exit__
- Restauración garantizada de stdout/stderr
- Respeta modo debug

## 📊 Resultado Esperado

### Después de la Mejora

```
2025-11-09 23:03:06 - root - INFO - ✅ Async logging initialized (QueueHandler)

=== Starting Jarvis AI Assistant (Multi-GPU + RAG) ===

✓ System monitor initialized
[STATUS] TTS disabled (ENABLE_TTS=false)
✓ Storage initialized
[STATUS] Audio effects disabled (ENABLE_AUDIO_EFFECTS=false)
✓ Metrics tracker initialized
✓ Embedding system (RAG) initialized
✓ SmartPromptBuilder initialized
✓ LearningManager initialized
✓ QualityEvaluator initialized
✓ ModelOrchestrator initialized (Multi-GPU)
✓ LLM system initialized
[STATUS] ⌨️ Text mode - ENABLE_WHISPER=false
✓ Voice system initialized
✓ Actions initialized
✓ Text handler initialized

=== Initializing Jarvis ===

✓ GPUs: 1 | Models loaded: 0
[STATUS] Jarvis Text Interface - Escribe 'help' para ver los comandos
✓ Health API running on port 8080
✓ Metrics collector running (interval=15s)
🟢 > 
```

**Sin:**
- ❌ `[Gloo] Rank 0...`
- ❌ `Loading safetensors...`
- ❌ `Capturing CUDA graphs...`
- ❌ Barras de progreso de tqdm

**Con:**
- ✅ Mensajes informativos de Jarvis
- ✅ Prompt limpio `🟢 >`
- ✅ Respuestas del asistente

## 🧪 Testing

### Script de Validación: `test_clean_logs.sh`

```bash
./test_clean_logs.sh
```

Verifica:
- ✅ Ausencia de logs de safetensors
- ✅ Ausencia de logs de Gloo
- ✅ Ausencia de logs de CUDA graphs
- ✅ Ausencia de barras de progreso tqdm
- ✅ Presencia de logs normales de Jarvis

### Modo Debug

Para desarrolladores que necesitan ver logs técnicos:

```bash
python3 main.py --debug
```

Esto:
- Establece `JARVIS_DEBUG=1`
- Deshabilita todas las supresiones
- Muestra logs completos de vLLM, torch, etc.

## 🔧 Arquitectura

```
┌─────────────────────────────────────────────┐
│           main.py (entrada)                 │
│  1. Parse --debug flag                      │
│  2. setup_clean_terminal() ← TEMPRANO       │
│  3. Import otros módulos                    │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│      log_suppressor.py (core)               │
│  • configure_quiet_mode()                   │
│  • suppress_tqdm()                          │
│  • model_loading_context()                  │
│  • SuppressedOutput                         │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│    model_orchestrator.py (uso)              │
│  with model_loading_context():              │
│      llm = LLM(...)  ← SILENCIOSO           │
└─────────────────────────────────────────────┘
```

## 📝 Variables de Entorno Configuradas

```bash
TF_CPP_MIN_LOG_LEVEL=3              # TensorFlow
TRANSFORMERS_VERBOSITY=error        # Hugging Face Transformers
TOKENIZERS_PARALLELISM=false        # Tokenizers
VLLM_LOGGING_LEVEL=ERROR           # vLLM
VLLM_CONFIGURE_LOGGING=0           # vLLM autoconfiguration
VLLM_LOGGING_CONFIG_PATH=          # vLLM config path
TORCH_DISTRIBUTED_DETAIL=OFF       # PyTorch Distributed
NCCL_DEBUG=                        # NCCL (NVIDIA)
GLOO_LOG_LEVEL=ERROR              # Gloo backend
```

## 🎯 Loggers Suprimidos

```python
verbose_loggers = [
    'vllm',
    'vllm.engine',
    'vllm.worker',
    'vllm.model_executor',
    'torch',
    'torch.distributed',
    'torch.distributed.distributed_c10d',
    'transformers',
    'sentence_transformers',
    'chromadb',
    'httpx',
    'asyncio',
    'tqdm',
    'filelock',
    'huggingface_hub',
]
```

Cada uno configurado a nivel `CRITICAL` con `propagate=False`.

## ✅ Ventajas

1. **Experiencia de Usuario Mejorada**
   - Terminal limpio y profesional
   - Solo información relevante
   - Interfaz no contaminada

2. **Mantenible**
   - Código centralizado en un módulo
   - Fácil agregar nuevas supresiones
   - Respeta modo debug

3. **Robusto**
   - Context managers con cleanup garantizado
   - Manejo de errores (siempre muestra errores)
   - No interfiere con funcionamiento normal

4. **Flexible**
   - Flag `--debug` para desarrolladores
   - Configurable por entorno
   - Puede redirigir a logs si se necesita

## 🚀 Uso

### Usuario Final
```bash
python3 main.py
# Terminal limpio, solo interfaz de usuario
```

### Desarrollador/Debug
```bash
python3 main.py --debug
# Todos los logs técnicos visibles
```

### Scripts Automatizados
```bash
JARVIS_DEBUG=0 python3 main.py
# Fuerza modo silencioso
```

## 📌 Notas Importantes

- La supresión ocurre **antes** de importar librerías pesadas
- Los logs se redirigen a archivos en `logs/` (configuración existente)
- Los errores **siempre** se muestran, incluso en modo silencioso
- No afecta el logging asíncrono existente (QueueHandler)
- Compatible con sistema de métricas y monitoreo

## 🔮 Futuras Mejoras

1. **Niveles de verbosidad**
   - `--quiet`: Solo errores
   - `--normal`: Estado actual
   - `--verbose`: Algunos logs técnicos
   - `--debug`: Todo

2. **Filtrado selectivo**
   - Permitir ver logs de una librería específica
   - `--show-logs=vllm` para debug específico

3. **Dashboard de logs**
   - Interfaz web para ver logs en tiempo real
   - Separado de la terminal

## 📚 Referencias

- Python logging: https://docs.python.org/3/library/logging.html
- Context managers: https://docs.python.org/3/library/contextlib.html
- vLLM configuration: https://docs.vllm.ai/
- PyTorch distributed: https://pytorch.org/docs/stable/distributed.html
