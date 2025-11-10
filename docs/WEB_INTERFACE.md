# 🌐 Jarvis Web Interface

## Interfaz Web Moderna para Jarvis AI Assistant

Una interfaz web limpia, moderna y profesional para interactuar con Jarvis sin los logs técnicos que contaminan la terminal.

---

## ✨ Características

- 🎨 **Diseño Moderno**: Interfaz tipo ChatGPT con dark mode
- 🚀 **Sin Logs Técnicos**: Experiencia limpia sin logs de vLLM, torch, etc.
- 💬 **Chat en Tiempo Real**: Respuestas instantáneas
- 📱 **Responsive**: Funciona en desktop, tablet y móvil
- 📊 **Monitor de Estado**: Ve el status de modelos y GPUs en tiempo real
- 💾 **Historial Persistente**: Guarda tu conversación
- ⚡ **API REST**: Backend con FastAPI
- 🔌 **WebSocket**: Soporte para streaming (futuro)

---

## 🚀 Inicio Rápido

### 1. Instalar Dependencias

```bash
pip install fastapi uvicorn python-multipart
```

### 2. Iniciar Jarvis Web

```bash
python3 start_web.py
```

O especifica puerto personalizado:

```bash
python3 start_web.py --port 8090
```

### 3. Abrir en Navegador

Abre tu navegador en:
```
http://localhost:8090
```

---

## 📁 Arquitectura

```
src/web/
├── api.py              # Backend FastAPI
├── templates/
│   └── index.html      # Frontend (HTML/CSS/JS)
└── static/             # Archivos estáticos (futuro)

start_web.py            # Launcher principal
```

### Backend (FastAPI)

- **`/api/status`** - Estado del sistema (modelos, GPUs)
- **`/api/chat`** - Enviar mensaje y recibir respuesta
- **`/api/history`** - Obtener/limpiar historial
- **`/ws/chat`** - WebSocket para streaming (experimental)

### Frontend (Vanilla JS)

- HTML5 + CSS3 (sin frameworks)
- Diseño responsive
- Dark mode nativo
- Animaciones suaves
- Formateo de markdown básico

---

## 🎨 Interfaz

### Pantalla de Bienvenida

```
🤖 Jarvis AI Assistant
¡Hola! Soy Jarvis 👋
Tu asistente AI con múltiples GPUs y RAG

[💡 ¿Qué puedes hacer?]
[🎓 Explica Machine Learning]
[💻 Ayuda con Python]
[⚙️ Tu configuración]
```

### Chat

```
╭─────────────────────────────────────────╮
│ 🤖 Jarvis AI Assistant     🗑️ Limpiar  │
│ 🟢 Listo (1 modelo, 1 GPU)             │
├─────────────────────────────────────────┤
│                                         │
│  👤  Hola, ¿cómo estás?                │
│      11:30 PM                           │
│                                         │
│  🤖  ¡Hola! Estoy aquí para ayudarte.  │
│      ¿En qué puedo asistirte hoy? 🌟   │
│      11:30 PM                           │
│                                         │
├─────────────────────────────────────────┤
│  Escribe tu mensaje aquí...  [Enviar 🚀]│
╰─────────────────────────────────────────╯
```

---

## ⚙️ Configuración

### Opciones de Línea de Comando

```bash
python3 start_web.py [opciones]

Opciones:
  --port PORT    Puerto para interfaz web (default: 8090)
  --host HOST    Host para interfaz web (default: 0.0.0.0)
  --debug        Activar modo debug
```

### Variables de Entorno

```bash
# En archivo .env o export directo
JARVIS_DEBUG=0          # Desactivar logs técnicos
ENABLE_TTS=false        # Desactivar TTS
ENABLE_WHISPER=false    # Desactivar reconocimiento de voz
```

---

## 🔧 Desarrollo

### Ejecutar Solo Backend

```bash
cd src/web
python3 api.py
```

### Hot Reload (uvicorn)

```bash
uvicorn src.web.api:app --reload --port 8090
```

### Inspeccionar API

API docs automática:
```
http://localhost:8090/docs
```

---

## 🌟 Características Detalladas

### 1. Sistema de Chat

- **Input automático**: Focus en input al cargar
- **Enter para enviar**: Presiona Enter para enviar mensaje
- **Sugerencias**: Botones de ejemplo para comenzar
- **Timestamps**: Cada mensaje con hora
- **Avatares**: Íconos diferenciados usuario/asistente

### 2. Indicadores Visuales

- **Typing Indicator**: Animación mientras Jarvis piensa
- **Status Dot**: Verde cuando está listo, amarillo inicializando
- **Error Messages**: Notificaciones de errores temporales
- **Loading States**: Botón deshabilitado mientras procesa

### 3. Historial

- **Persistente**: Se guarda en memoria del servidor
- **Carga Automática**: Se carga al abrir página
- **Limpiar**: Botón para borrar historial
- **Últimos 50**: Muestra últimos 50 mensajes

### 4. Responsive Design

- **Desktop**: Layout completo con sidebar (futuro)
- **Tablet**: Chat optimizado
- **Mobile**: Interface touch-friendly

---

## 🔐 Seguridad

- CORS configurado para localhost
- Sin autenticación (desarrollo local)
- Validación de inputs en backend
- Sanitización de HTML básica

**⚠️ Nota**: No exponer a internet sin autenticación adicional

---

## 🐛 Troubleshooting

### Puerto ocupado

```bash
# Error: address already in use
# Solución: Usar puerto diferente
python3 start_web.py --port 8091
```

### FastAPI no instalado

```bash
pip install fastapi uvicorn
```

### No se conecta a Jarvis

- Verificar que `start_web.py` inicializó correctamente
- Ver logs en terminal
- Verificar endpoint `/api/status`

### Los logs todavía aparecen

Los logs técnicos (vLLM, Gloo, etc.) **solo aparecen en la terminal donde ejecutas `start_web.py`**, NO en la interfaz web del navegador. Esto es intencional - la interfaz web está completamente aislada.

---

## 📊 Comparación: Terminal vs Web

| Feature | Terminal | Web Interface |
|---------|----------|---------------|
| Logs técnicos | ✅ Visibles | ❌ Ocultos |
| Interfaz | 🟢 Texto | 🎨 Gráfica |
| Historial | ⚠️ Limitado | ✅ Completo |
| Markdown | ❌ No | ✅ Sí |
| Múltiples sesiones | ❌ No | ✅ Sí (tabs) |
| Mobile-friendly | ❌ No | ✅ Sí |
| Copy/paste | ⚠️ Terminal | ✅ Fácil |

---

## 🎯 Roadmap

### v1.1 (Próximamente)
- [ ] WebSocket streaming de respuestas
- [ ] Syntax highlighting para código
- [ ] Export de conversaciones
- [ ] Temas personalizables

### v1.2 (Futuro)
- [ ] Múltiples conversaciones (tabs)
- [ ] Upload de archivos
- [ ] Voice input en navegador
- [ ] Autenticación con usuarios

### v2.0 (Futuro)
- [ ] Sistema de plugins
- [ ] Dashboard de analytics
- [ ] API pública documentada
- [ ] Mobile app (PWA)

---

## 📚 Recursos Adicionales

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Uvicorn Docs](https://www.uvicorn.org/)
- [WebSocket Tutorial](https://fastapi.tiangolo.com/advanced/websockets/)

---

## 🤝 Contribuir

Para mejorar la interfaz web:

1. Edita `src/web/templates/index.html` para frontend
2. Edita `src/web/api.py` para backend
3. Reinicia `start_web.py`

---

## 📄 Licencia

Same as Jarvis AI Assistant main project

---

## 🎉 ¡Disfruta!

Ahora puedes usar Jarvis con una interfaz limpia y profesional, sin preocuparte por los logs técnicos en la terminal.

**¿Preguntas?** Abre un issue o pregunta a Jarvis directamente 😉
