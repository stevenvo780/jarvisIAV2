# 🤖 Jarvis AI Assistant V2

Asistente de IA avanzado con interfaz web moderna y capacidades multimodales.

## 🚀 Inicio Rápido

### Interfaz Web (Recomendado)
```bash
python3 start_web.py
# Abre: http://localhost:8090
```

### Terminal Tradicional
```bash
python3 main.py
```

---

## ✨ Características

### Interfaz Web
- 🎨 Diseño moderno tipo ChatGPT
- 🌙 Tema oscuro profesional
- 📱 Responsive (móvil, tablet, desktop)
- 💬 Chat interactivo con historial
- 🚫 Sin logs técnicos visibles
- ⚡ Indicadores de estado en tiempo real

### Core
- �� Múltiples modelos LLM (Qwen, LLaMA, DeepSeek)
- 🎯 Selección automática por dificultad de query
- 💾 Sistema RAG con ChromaDB + BGE-M3
- 🔊 Procesamiento de voz (TTS/STT)
- 📊 Monitoreo de GPU en tiempo real
- 🔄 Gestión dinámica de modelos

---

## 📋 Requisitos

- Python 3.10+
- CUDA 11.8+ (para GPU)
- 16GB+ VRAM (RTX 3090/4090/5070 Ti recomendado)
- 32GB+ RAM

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env con tus API keys

# Iniciar
python3 start_web.py
```

---

## 🎛️ Configuración

### Modelos Soportados

- **Qwen2.5-14B-Instruct-AWQ** (default) - Balanceado
- **Qwen2.5-32B-Instruct-GPTQ** - Alto rendimiento
- **LLaMA 3.1 70B** - Tareas complejas
- **DeepSeek 14B** - Código especializado

### Variables de Entorno

```bash
# API Keys (opcional, para fallback)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPINFRA_API_KEY=...

# GPU
CUDA_VISIBLE_DEVICES=0

# Puerto web
WEB_PORT=8090
```

---

## 📁 Estructura del Proyecto

```
jarvisIAV2/
├── src/
│   ├── web/              # Interfaz web (FastAPI)
│   ├── modules/          # Módulos core
│   │   ├── orchestrator/ # Gestión de modelos
│   │   ├── embeddings/   # Sistema RAG
│   │   ├── audio/        # TTS/STT
│   │   └── text/         # Procesamiento texto
│   └── utils/            # Utilidades
├── main.py               # Entrada terminal
├── start_web.py          # Entrada web
└── README.md
```

---

## 🧪 Uso

### Interfaz Web

1. **Iniciar servidor**: `python3 start_web.py`
2. **Abrir navegador**: http://localhost:8090
3. **Chatear**: ¡Listo!

### Terminal

```bash
python3 main.py

>>> Hola Jarvis
🤖 ¡Hola! ¿En qué puedo ayudarte?
```

---

## 🔧 Arquitectura

```
Usuario → FastAPI/Terminal
    ↓
ModelOrchestrator
    ↓
vLLM/Transformers (GPU)
    ↓
RAG (ChromaDB)
    ↓
Respuesta
```

---

## 📊 Rendimiento

### Benchmarks (RTX 5070 Ti 16GB)

| Modelo | Carga | Respuesta | Throughput |
|--------|-------|-----------|------------|
| Qwen-14B-AWQ | ~16s | ~30-40s | 5.6 tok/s |
| Qwen-32B-GPTQ | ~25s | ~50-60s | 3.2 tok/s |

---

## 🐛 Troubleshooting

### Puerto 8090 en uso
```bash
lsof -ti:8090 | xargs kill -9
```

### GPU sin memoria
```bash
pkill -9 -f vllm
```

---

## 📝 Licencia

MIT License

---

**Versión**: 2.0  
**Estado**: ✅ Producción  
**Última actualización**: Noviembre 2025
