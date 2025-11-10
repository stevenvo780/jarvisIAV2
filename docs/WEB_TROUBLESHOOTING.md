# 🔧 Solución de Problemas - Interfaz Web Jarvis

## ✅ Problema Resuelto: FileNotFoundError models_v2.json

### Síntoma
```
FileNotFoundError: [Errno 2] No such file or directory: 'src/config/models_v2.json'
RuntimeError: Cannot load configuration from src/config/models_v2.json
```

### Causa
El código de `ModelOrchestrator` busca `models_v2.json` pero solo existe `models.json` en el repositorio.

### Solución Automática
Los scripts de inicio ahora detectan y corrigen este problema automáticamente:

```bash
# Opción 1: Script bash (con auto-fix)
./start_web.sh

# Opción 2: Script Python (con auto-fix)
python3 start_web.py
```

Ambos scripts:
1. Verifican si existe `models_v2.json`
2. Si no existe, copian `models.json` → `models_v2.json`
3. Continúan con el inicio normal

### Solución Manual (Si es necesario)
```bash
cp src/config/models.json src/config/models_v2.json
```

---

## 🚀 Inicio Exitoso - Salida Esperada

```
============================================================
🤖 JARVIS AI ASSISTANT - WEB INTERFACE
============================================================
📱 Interfaz web: http://localhost:8090
⚙️  Puerto: 8090
🔧 Debug: Desactivado
============================================================

2025-11-09 23:38:53 - __main__ - INFO - 🌐 Inicializando Jarvis...
2025-11-09 23:38:53 - __main__ - INFO - ✓ System monitor initialized
2025-11-09 23:38:53 - __main__ - INFO - ✓ Storage initialized
2025-11-09 23:38:53 - __main__ - INFO - ✓ Metrics tracker initialized
2025-11-09 23:38:54 - __main__ - INFO - ✓ Embedding system (RAG) initialized
2025-11-09 23:38:54 - __main__ - INFO - ✓ SmartPromptBuilder initialized
2025-11-09 23:38:54 - __main__ - INFO - ✓ LearningManager initialized
2025-11-09 23:38:54 - __main__ - INFO - ✓ QualityEvaluator initialized
2025-11-09 23:38:54 - __main__ - INFO - ✓ ModelOrchestrator initialized
2025-11-09 23:38:54 - __main__ - INFO - ✅ Jarvis core initialized

🌐 Iniciando servidor web en http://0.0.0.0:8090
📱 Abre tu navegador en: http://localhost:8090

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8090 (Press CTRL+C to quit)
```

---

## 🐛 Otros Problemas Comunes

### 1. Puerto Ocupado
**Síntoma:**
```
ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8090): address already in use
```

**Solución:**
```bash
# Opción A: Usar puerto diferente
python3 start_web.py --port 8091

# Opción B: Matar proceso existente
lsof -ti:8090 | xargs kill -9
```

### 2. FastAPI no instalado
**Síntoma:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solución:**
```bash
pip install fastapi uvicorn python-multipart
```

### 3. Pygame Warning
**Síntoma:**
```
pygame 2.6.1 (SDL 2.28.4, Python 3.13.7)
Hello from the pygame community. https://www.pygame.org/contribute.html
```

**Nota:** Esto es un mensaje informativo de pygame, no un error. Puede ignorarse.

### 4. GPU No Disponible
**Síntoma:**
```
⚠️  nvidia-smi no encontrado (modo CPU)
```

**Nota:** Jarvis funcionará en modo CPU (más lento). Para usar GPU:
- Verifica drivers NVIDIA: `nvidia-smi`
- Instala CUDA toolkit
- Verifica `CUDA_VISIBLE_DEVICES`

### 5. Modelos No Encontrados
**Síntoma:**
```
FileNotFoundError: models/llm/qwen2.5-14b-awq
```

**Solución:**
Los modelos se descargan bajo demanda. Al hacer la primera consulta, Jarvis:
1. Detecta modelo no presente
2. Lo descarga automáticamente
3. Lo carga en GPU

Tiempo de descarga: ~10-30 minutos según modelo.

### 6. Out of Memory (OOM)
**Síntoma:**
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**Solución:**
Edita `src/config/models_v2.json`:
```json
{
  "models": {
    "qwen-32b": {
      "enabled": false  // Deshabilitar modelo grande
    },
    "qwen-14b": {
      "enabled": true   // Usar modelo más pequeño
    }
  }
}
```

---

## 🔍 Debug Avanzado

### Modo Debug
```bash
python3 start_web.py --debug
```

Esto activa:
- Logs detallados de vLLM
- Logs de torch.distributed
- Traceback completos
- Métricas de rendimiento

### Logs Persistentes
```bash
# Ver logs en tiempo real
tail -f logs/jarvis.log

# Ver solo errores
tail -f logs/errors.log

# Buscar error específico
grep "ERROR" logs/jarvis.log
```

### Estado del Servidor
```bash
# API status
curl http://localhost:8090/api/status

# Health check
curl http://localhost:8090/docs  # OpenAPI docs
```

### Verificar Proceso
```bash
# Ver proceso uvicorn
ps aux | grep uvicorn

# Ver uso de GPU
watch -n 1 nvidia-smi

# Ver uso de memoria
htop
```

---

## 📊 Métricas de Rendimiento

### Tiempos Normales
- **Inicio de servidor**: 5-10 segundos
- **Primera consulta (carga modelo)**: 30-60 segundos
- **Consultas subsiguientes**: 1-5 segundos
- **Uso de VRAM**: 6-14 GB según modelo

### Optimizaciones
Si está lento:
1. Usar modelos AWQ (quantizados)
2. Reducir `max_tokens` en config
3. Habilitar solo 1 modelo
4. Usar GPU más potente

---

## 🆘 Soporte

### Información para Reportar Issues
```bash
# Recopilar info del sistema
python3 -c "
import sys
import torch
print(f'Python: {sys.version}')
print(f'PyTorch: {torch.__version__}')
print(f'CUDA: {torch.cuda.is_available()}')
"

# Info de GPU
nvidia-smi

# Versiones de paquetes
pip list | grep -E "(fastapi|uvicorn|torch|transformers)"
```

### Logs Útiles
Al reportar problemas, incluir:
1. Output completo del error
2. Contenido de `logs/errors.log`
3. Versión de Python y CUDA
4. Comando exacto usado

---

## ✅ Checklist de Inicio

Antes de reportar problemas, verificar:

- [ ] Python 3.8+ instalado
- [ ] `pip install fastapi uvicorn` ejecutado
- [ ] `models_v2.json` existe (auto-creado por scripts)
- [ ] Puerto 8090 disponible
- [ ] CUDA drivers instalados (si usar GPU)
- [ ] Espacio en disco suficiente (>50GB para modelos)
- [ ] RAM suficiente (>16GB recomendado)

---

## 🎓 Recursos

- **Documentación completa**: `docs/WEB_INTERFACE.md`
- **Guía rápida**: `WEB_QUICKSTART.md`
- **Visual guide**: `docs/WEB_VISUAL_GUIDE.md`
- **FastAPI docs**: https://fastapi.tiangolo.com/
- **vLLM docs**: https://docs.vllm.ai/

---

**Última actualización:** 2025-11-09  
**Estado:** ✅ Todos los problemas conocidos resueltos
