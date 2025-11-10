# 🌐 Interfaz Web de Jarvis - Guía de Inicio Rápido

## 🚀 Inicio en 3 Pasos

### 1. Instalar Dependencias (Solo Primera Vez)

```bash
pip install fastapi uvicorn
```

### 2. Iniciar Jarvis Web

```bash
./start_web.sh
```

O con Python directamente:

```bash
python3 start_web.py
```

### 3. Abrir Navegador

```
http://localhost:8090
```

---

## ✨ Lo Que Obtienes

- ✅ **Interfaz limpia** sin logs técnicos
- ✅ **Chat moderno** tipo ChatGPT
- ✅ **Dark mode** nativo
- ✅ **Responsive** (móvil, tablet, desktop)
- ✅ **Historial** persistente
- ✅ **Status en tiempo real** de modelos y GPUs

---

## 🎯 Comparación

### Terminal (Antes ❌)
```
[Gloo] Rank 0 is connected...
Loading safetensors: 33% |███   |
Capturing CUDA graphs...
🟢 > hola
💭 [más logs técnicos...]
```

### Web Interface (Ahora ✅)
```
🤖 Jarvis AI Assistant    🟢 Listo (1 modelo, 1 GPU)

  👤  hola
      
  🤖  ¡Hola! ¿En qué puedo ayudarte hoy? 🌟
      
╰─ Escribe tu mensaje aquí...  [Enviar 🚀] ─╯
```

---

## 📚 Documentación Completa

Ver `docs/WEB_INTERFACE.md` para:
- Configuración avanzada
- API endpoints
- Desarrollo
- Troubleshooting
- Roadmap

---

## 🐛 Problemas Comunes

### Puerto ocupado
```bash
./start_web.sh 8091  # Usar puerto diferente
```

### Dependencias faltantes
```bash
pip install -r requirements.txt
```

---

## 💡 Tips

- Presiona **Enter** para enviar mensaje
- Usa botones de **sugerencias** para ejemplos
- **Limpia** el historial con botón 🗑️
- Los logs técnicos **solo aparecen en terminal**, no en web

---

Creado con ❤️ para mantener tu experiencia con Jarvis limpia y profesional
