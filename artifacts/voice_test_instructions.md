# 🎤 Instrucciones para Probar el Sistema de Voz de Jarvis

## ✅ Funcionalidades Implementadas

### 1. **Escucha Pasiva con Palabra Clave**
   - El sistema escucha continuamente en segundo plano
   - Al detectar la palabra "**Jarvis**", se activa automáticamente
   - Proporciona feedback visual y auditivo

### 2. **Text-to-Speech (TTS) Automático**
   - Las respuestas de Jarvis se leen automáticamente
   - Voz en español (selecciona la mejor voz disponible)
   - Control ON/OFF independiente

### 3. **Conversaciones Naturales**
   - Modo comando activo por 10 segundos tras activación
   - Procesamiento automático del comando
   - Respuesta visual + auditiva

## 🚀 Cómo Probar

### Paso 1: Iniciar el Servidor
```bash
cd /datos/repos/Personal/jarvisIAV2
python3 start_web.py --port 8091
```

### Paso 2: Abrir el Navegador
1. Abre **Chrome** o **Edge** (Firefox tiene soporte limitado)
2. Ve a: `http://localhost:8091`
3. **Importante**: Acepta los permisos del micrófono cuando se soliciten

### Paso 3: Activar el Sistema de Voz

#### **Opción A: Escucha Pasiva (Recomendado)**
1. Haz clic en el botón **🎤 Voz** en la parte superior
2. El botón debe cambiar a **🎤 ◉ Escuchando**
3. Verás un badge flotante: "Di 'Jarvis' para activar"

#### **Opción B: TTS (Lectura Automática)**
1. Haz clic en el botón **🔊 TTS**
2. El botón debe cambiar a **🔊 TTS On**
3. Todas las respuestas se leerán automáticamente

### Paso 4: Interactuar con Jarvis

#### **Usando Voz (Escucha Pasiva)**
1. Con el modo voz activo, di en voz alta: **"Jarvis"**
2. El sistema responderá: *"Sí, dime"*
3. El botón cambiará a **rojo parpadeante**
4. El badge mostrará: *"¿En qué puedo ayudarte?"*
5. Haz tu pregunta (tienes 10 segundos)
6. Ejemplo: *"¿Qué hora es?"* o *"Explícame qué es Python"*

#### **Usando Texto + TTS**
1. Activa solo el modo TTS
2. Escribe tu mensaje normalmente
3. Envía con Enter o el botón "Enviar 🚀"
4. La respuesta se leerá automáticamente

## 🎯 Ejemplos de Uso

### Conversación Completa por Voz
```
Usuario: "Jarvis"
Jarvis: [Voz] "Sí, dime"
Usuario: "¿Qué puedes hacer?"
Jarvis: [Voz + Texto] "Soy un asistente AI que puede..."
```

### Conversación Mixta (Texto + TTS)
```
Usuario: [Escribe] "Explícame machine learning"
Jarvis: [Voz + Texto] "Machine learning es..."
```

### Modo Pasivo Continuo
1. Activa modo voz
2. El sistema queda escuchando permanentemente
3. Di "Jarvis" cuando quieras hacer una pregunta
4. Vuelve a modo pasivo automáticamente tras 10s de inactividad

## 🔧 Controles Disponibles

| Botón | Función | Comportamiento |
|-------|---------|----------------|
| 🎤 Voz | Activar/Desactivar escucha pasiva | Toggle ON/OFF |
| 🔊 TTS | Activar/Desactivar lectura automática | Toggle ON/OFF |
| 🗑️ Limpiar | Borrar historial de chat | Confirmación requerida |

## 📊 Indicadores Visuales

### Estado de Escucha
- **🎤 Voz**: Modo voz desactivado
- **🎤 ◉ Escuchando**: Modo pasivo activo
- **🎤 ● Escuchando** (rojo parpadeante): Esperando comando

### Badge Flotante (inferior derecha)
- **"Di 'Jarvis' para activar"**: Modo pasivo
- **"¿En qué puedo ayudarte?"**: Modo activo (10s)
- **"Escuchando: [texto]"**: Transcripción en tiempo real

### Estado TTS
- **🔊 TTS**: Desactivado
- **🔊 TTS On**: Activado (fondo verde)

## ⚙️ Configuración

### Persistencia
- Las preferencias se guardan en `localStorage`
- Se restauran automáticamente al recargar la página

### Idioma
- **Reconocimiento**: `es-ES` (Español de España)
- **TTS**: Voz en español (mejor disponible)
- Puedes cambiar el idioma editando `recognition.lang` y `utterance.lang`

### Timeouts
- **Comando activo**: 10 segundos
- **Reinicio automático**: Inmediato tras finalizar comando

## 🐛 Solución de Problemas

### El micrófono no funciona
1. Verifica permisos del navegador (ícono de candado en la barra de direcciones)
2. Usa Chrome o Edge (mejor soporte)
3. Asegúrate de que no haya otra app usando el micrófono

### No detecta la palabra "Jarvis"
1. Habla claro y un poco más fuerte
2. Verifica en la consola del navegador (F12) los logs: `🗣️ Escuchado:`
3. Prueba variaciones: "Jarvis", "yar-bis", "har-vis"

### TTS no funciona
1. Verifica el volumen del sistema
2. Abre la consola (F12) y busca errores de TTS
3. Prueba con otro navegador (Chrome/Edge recomendados)

### Se desactiva solo
1. Es normal tras 10s de inactividad en modo comando
2. Volverá a modo pasivo automáticamente
3. Reinicio automático si se pierde la conexión

## 🔐 Privacidad

- **Todo el procesamiento de voz es local** (Web Speech API del navegador)
- No se envía audio al servidor
- Solo se envía el texto transcrito
- Los permisos del micrófono se solicitan explícitamente

## 📝 Notas Técnicas

### Tecnologías Utilizadas
- **Web Speech API**: Reconocimiento de voz nativo del navegador
- **SpeechSynthesis API**: TTS nativo del navegador
- **WebSocket**: Streaming de respuestas (opcional)
- **LocalStorage**: Persistencia de preferencias

### Compatibilidad
| Navegador | Reconocimiento | TTS |
|-----------|----------------|-----|
| Chrome | ✅ Completo | ✅ Completo |
| Edge | ✅ Completo | ✅ Completo |
| Firefox | ⚠️ Limitado | ✅ Completo |
| Safari | ⚠️ Limitado | ✅ Completo |

### Arquitectura
```
Frontend (index.html)
├── Web Speech API (SpeechRecognition)
│   ├── Escucha continua
│   ├── Detección de palabra clave
│   └── Transcripción en tiempo real
├── Speech Synthesis API
│   ├── Reproducción de respuestas
│   └── Selección automática de voz
└── FastAPI Backend
    ├── /api/chat (POST) - Procesar mensajes
    ├── /api/voice/config (GET) - Configuración
    └── /api/voice/settings (POST) - Actualizar config
```

## 🎉 Características Avanzadas

### Transcripción en Tiempo Real
- Muestra el texto mientras hablas
- Actualización continua del badge
- Feedback visual inmediato

### Reinicio Automático
- Si el reconocimiento se detiene, se reinicia solo
- Tolerancia a fallos de red
- Manejo de errores graceful

### Modo Híbrido
- Puedes usar voz y texto simultáneamente
- TTS funciona independientemente del modo voz
- Conversaciones naturales y flexibles

## 📚 Próximas Mejoras

- [ ] Selector de idiomas en UI
- [ ] Selector de voces TTS
- [ ] Comandos de voz especiales (ej: "limpia el chat")
- [ ] Indicador de nivel de audio
- [ ] Historial de comandos de voz
- [ ] Configuración de velocidad/tono de voz
- [ ] Wake word personalizable
- [ ] Múltiples palabras clave
