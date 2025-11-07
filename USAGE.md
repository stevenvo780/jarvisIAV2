# Jarvis AI Assistant - Guía de Uso

## 🚀 Modos de Ejecución

### 1. Modo Interactivo (Terminal)
```bash
python main.py
```
Inicia la interfaz interactiva de terminal donde puedes chatear con Jarvis.

### 2. Modo Comando (No bloqueante)
```bash
# Consulta simple
python main.py --query "¿Cuál es la capital de Francia?"

# Con modelo específico
python main.py --query "Explica la teoría de la relatividad" --model llama-70b

# Ver modelos disponibles
python main.py --list-models

# Ver estadísticas del sistema
python main.py --stats
```

## 📊 Verificar Estado del Sistema

### Ver modelos configurados y cargados
```bash
python main.py --list-models
```

**Salida esperada:**
```
======================================================================
AVAILABLE MODELS
======================================================================

📊 GPU Count: 2
📦 Models Loaded: 0

🎮 RTX 5070 Ti (GPU 0)
   VRAM: 477MB / 16303MB (2.9%)

🎮 RTX 2060 (GPU 1)
   VRAM: 2383MB / 6144MB (38.8%)

📋 Configured Models:
  ⬜ NOT LOADED llama-70b: Llama-3.3-70B-Instruct (GPU 0, 14000MB)
  ⬜ NOT LOADED qwen-32b: Qwen2.5-32B-Instruct (GPU 0, 10000MB)
  ⬜ NOT LOADED deepseek-14b: DeepSeek-R1-Distill-Qwen-14B (GPU 0, 9000MB)
  ⬜ NOT LOADED llama-8b: Llama-3.2-8B-Instruct (GPU 1, 4500MB)
```

## 🔧 Configuración

### Modelos Locales vs API

El sistema puede funcionar con:

1. **Modelos Locales** (requiere descarga):
   - GPU 0 (RTX 5070 Ti 16GB): Llama-70B, Qwen-32B, DeepSeek-14B
   - GPU 1 (RTX 2060 6GB): Llama-8B

2. **Modelos API** (sin descarga, requiere claves):
   - OpenAI: GPT-4o-mini
   - Google: Gemini-2.0-Flash (gratis)
   - Anthropic: Claude-3.5-Sonnet

### Configurar Claves API

Edita el archivo `.env`:

```bash
# OpenAI (GPT-4o-mini)
OPENAI_API_KEY=sk-your-key-here

# Google Gemini (GRATIS)
GOOGLE_API_KEY=your-google-api-key

# Anthropic Claude
ANTHROPIC_API_KEY=your-anthropic-key
```

### Descargar Modelos Locales

```bash
# Modelo para GPU 0 (RTX 5070 Ti)
python scripts/download_models.py --category llm_gpu1 --skip-existing

# Modelo para GPU 1 (RTX 2060)
python scripts/download_models.py --category llm_gpu2 --skip-existing

# Embeddings para RAG (opcional)
python scripts/download_models.py --category embeddings --skip-existing

# Whisper para voz (opcional)
python scripts/download_models.py --category whisper --skip-existing
```

## 🎛️ Funcionalidades Opcionales

### Habilitar RAG (Memoria de Largo Plazo)

En `.env`:
```bash
ENABLE_RAG=true
```

Requiere descargar modelo de embeddings (~2GB):
```bash
python scripts/download_models.py --category embeddings
```

### Habilitar Reconocimiento de Voz

En `.env`:
```bash
ENABLE_WHISPER=true
```

Requiere descargar modelo Whisper (~3GB):
```bash
python scripts/download_models.py --category whisper
```

## 💡 Ejemplos de Uso

### Modo Comando (Recomendado para scripts/automatización)

```bash
# Pregunta simple
python main.py -q "¿Qué es Python?"

# Análisis de código
python main.py -q "Explica qué hace este código: def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"

# Traducción
python main.py -q "Traduce al inglés: Hola, ¿cómo estás?"

# Matemáticas
python main.py -q "Calcula la raíz cuadrada de 2"
```

### Integración con Scripts

```bash
#!/bin/bash

# Procesar múltiples consultas
questions=(
    "¿Qué es la inteligencia artificial?"
    "Explica machine learning"
    "¿Qué es deep learning?"
)

for q in "${questions[@]}"; do
    python main.py --query "$q" >> respuestas.txt
done
```

## 🔍 Troubleshooting

### No hay modelos cargados

**Síntoma:** `Models Loaded: 0`

**Soluciones:**
1. Configura claves API en `.env` para usar modelos en la nube (más rápido)
2. Descarga modelos locales con `scripts/download_models.py`

### Error de VRAM insuficiente

**Síntoma:** `Insufficient VRAM for Llama-3.2-8B-Instruct`

**Soluciones:**
1. La GPU 1 está casi llena por otros procesos
2. Libera VRAM: `nvidia-smi` → identifica procesos → kill
3. Usa modelos API en su lugar

### Modo interactivo se queda bloqueado

**Solución:** Usa modo comando en su lugar:
```bash
python main.py --query "tu pregunta aquí"
```

## 📈 Próximos Pasos

1. **Configurar API (Más rápido):**
   ```bash
   # Consigue clave gratis de Google
   # https://aistudio.google.com/apikey
   echo "GOOGLE_API_KEY=tu-clave-aqui" >> .env
   ```

2. **O descargar modelos locales:**
   ```bash
   python scripts/download_models.py --category llm_gpu2
   ```

3. **Probar:**
   ```bash
   python main.py --query "Hola, ¿cómo funciona Jarvis?"
   ```
