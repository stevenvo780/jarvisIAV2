# 🚀 INICIO RÁPIDO - Jarvis Web Interface

## ¿Qué es esto?

Una **interfaz web limpia** para Jarvis que **elimina todos los logs técnicos** de tu terminal. Ahora chatea con Jarvis desde el navegador, como ChatGPT.

---

## 🏃 Iniciar en 3 pasos

### 1️⃣ Abre una terminal y ejecuta:
```bash
cd /datos/repos/Personal/jarvisIAV2
python3 start_web.py
```

### 2️⃣ Espera ~25 segundos hasta ver:
```
🚀 JARVIS AI ASSISTANT - WEB INTERFACE
============================================================
📱 Interfaz web: http://localhost:8090
⚙️  Puerto: 8090
============================================================
```

### 3️⃣ Abre tu navegador en:
```
http://localhost:8090
```

**¡Listo!** 🎉 Ahora puedes chatear sin ver logs técnicos.

---

## 🎨 ¿Qué verás?

Una interfaz moderna con:
- ✅ Tema oscuro profesional
- ✅ Chat interactivo con burbujas
- ✅ Indicador "Jarvis está escribiendo..."
- ✅ Historial de conversación
- ✅ Sin frameworks, solo HTML/CSS/JS

**Experiencia similar a**: ChatGPT, Claude, Gemini

---

## 💬 Ejemplo de Uso

1. **Abre** `http://localhost:8090` en tu navegador
2. **Escribe** en el cuadro de texto: "Hola, ¿cómo estás?"
3. **Presiona** Enter o clic en "Enviar"
4. **Espera** ~30-70 segundos (primera vez, mientras carga el modelo)
5. **Lee** la respuesta de Jarvis en la interfaz

**Nota**: Las respuestas siguientes serán más rápidas (~10-30s) porque el modelo ya está en memoria.

---

## 🛑 Detener el servidor

En la terminal donde ejecutaste `python3 start_web.py`, presiona:
```
Ctrl + C
```

O si está en background:
```bash
pkill -f "python3 start_web.py"
```

---

## 🆘 Problemas Comunes

### El servidor no inicia
**Solución**: Verifica que no haya otro proceso usando el puerto 8090:
```bash
lsof -i :8090
# Si hay algo, mátalo:
kill -9 <PID>
```

### "GPU sin memoria"
**Solución**: Limpia procesos vLLM antiguos:
```bash
pkill -9 -f vllm
# O verifica con:
nvidia-smi
```

### El chat no responde
**Solución**: Espera ~30-70 segundos. La primera respuesta tarda mientras carga el modelo de 14B parámetros.

### Error al cargar
**Solución**: Reinicia el servidor:
```bash
pkill -f "python3 start_web.py"
python3 start_web.py
```

---

## 📊 ¿Qué pasa en segundo plano?

Mientras chateas, el servidor:
1. 🧠 Busca contexto relevante en 357 memorias (RAG)
2. 🤖 Selecciona el modelo apropiado (Qwen2.5-14B-AWQ)
3. ⚡ Genera respuesta en GPU 0 (RTX 5070 Ti)
4. 💾 Guarda la conversación en el historial
5. 📝 Aprende de tus interacciones

**Todo esto sin ensuciar tu terminal con logs** ✨

---

## 🔧 Configuración Avanzada (Opcional)

### Cambiar puerto:
Edita `start_web.py` línea 124:
```python
uvicorn.run("api:app", host="0.0.0.0", port=8090)  # Cambia 8090
```

### Ver logs técnicos:
```bash
tail -f /tmp/jarvis_web.log
```

### Habilitar modo debug:
En `start_web.py` línea 124:
```python
uvicorn.run("api:app", host="0.0.0.0", port=8090, reload=True, log_level="debug")
```

---

## 🎯 Ventajas vs Terminal

| Terminal (`main.py`) | Web (`start_web.py`) |
|---------------------|---------------------|
| ❌ Logs técnicos contaminan | ✅ UI limpia sin logs |
| ❌ Difícil de leer | ✅ Diseño moderno |
| ❌ Solo texto plano | ✅ Burbujas de chat |
| ❌ Sin historial visual | ✅ Historial completo |
| ❌ No responsive | ✅ Funciona en móvil |

---

## 📚 Más Información

- **Documentación completa**: `WEB_FINAL_SUMMARY.md`
- **Guía de solución de problemas**: `WEB_TROUBLESHOOTING.md`
- **Detalles técnicos**: `WEB_INTERFACE.md`
- **Resultados de pruebas**: `WEB_TEST_RESULTS.md`

---

## 🎉 ¡Disfruta tu nueva interfaz!

Si tienes preguntas o problemas, revisa los documentos arriba o ejecuta:
```bash
python3 test_web_interface.py
```

Para verificar que todo funciona correctamente.

---

**Creado**: 2025-11-09  
**Versión**: 1.0  
**Estado**: ✅ Probado y funcionando
