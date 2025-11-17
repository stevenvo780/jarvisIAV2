# 🎤 Sistema de Voz para Jarvis - README

## ✅ Implementación Completada

Se ha añadido un sistema completo de **reconocimiento de voz** y **text-to-speech** al navegador web de Jarvis.

---

## 🚀 Inicio Rápido

### 1. Iniciar el servidor
```bash
cd /datos/repos/Personal/jarvisIAV2
python3 start_web.py --port 8091
```

### 2. Abrir el navegador
- URL: **http://localhost:8091**
- Navegador recomendado: **Chrome** o **Edge**
- Aceptar permisos del micrófono cuando se soliciten

### 3. Activar y usar
1. Clic en botón **🎤 Voz**
2. Di **"Jarvis"** en voz alta
3. Escucharás: *"Sí, dime"*
4. Haz tu pregunta
5. La respuesta aparecerá en texto y voz

---

## 🎯 Características Principales

### 🎤 Escucha Pasiva
- **Activación**: Botón "🎤 Voz"
- **Palabra clave**: "Jarvis"
- **Modo**: Escucha continua en segundo plano
- **Timeout**: 10 segundos para dar comando
- **Reinicio**: Automático tras procesar

### 🔊 Text-to-Speech
- **Activación**: Botón "🔊 TTS"
- **Función**: Lee automáticamente las respuestas
- **Voz**: Español (mejor disponible en sistema)
- **Independiente**: Funciona con o sin modo voz

### 💬 Conversaciones Naturales
- **Modo híbrido**: Voz + TTS simultáneos
- **Manos libres**: Sin necesidad de pulsar botones
- **Transcripción**: En tiempo real mientras hablas
- **Historial**: Todo se guarda automáticamente

---

## 📁 Archivos Modificados/Creados

### Modificados
- `src/web/api.py` - Endpoints de voz
- `src/web/templates/index.html` - Sistema completo de voz

### Documentación Creada
- `artifacts/voice_test_instructions.md` - Guía detallada de uso
- `artifacts/validate_voice_system.sh` - Script de validación
- `artifacts/voice_implementation_summary.md` - Resumen técnico completo
- `artifacts/voice_demo_visual.sh` - Demo visual ASCII
- `artifacts/VOICE_README.md` - Este archivo

---

## 🔧 Validación

### Automática
```bash
bash artifacts/validate_voice_system.sh
```

### Manual
1. Abrir http://localhost:8091
2. Verificar botones de voz en header
3. Probar escucha pasiva
4. Probar TTS
5. Probar modo híbrido

---

## 🌐 Compatibilidad

| Navegador | Reconocimiento | TTS | Estado |
|-----------|----------------|-----|---------|
| Chrome | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| Edge | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| Firefox | ⚠️ | ✅ | ⭐⭐⭐ |
| Safari | ⚠️ | ✅ | ⭐⭐⭐ |

**Nota**: Chrome y Edge tienen el mejor soporte completo.

---

## 🔐 Privacidad y Seguridad

✅ Todo el procesamiento de voz es **local** (navegador)  
✅ **No se envía audio** al servidor  
✅ Solo se envía **texto transcrito**  
✅ Permisos del micrófono **explícitos**  
✅ Protección **XSS** implementada  
✅ **CORS** restringido a localhost  

---

## 🐛 Troubleshooting

### No detecta el micrófono
1. Verificar permisos del navegador
2. Ir a Configuración → Privacidad → Micrófono
3. Permitir acceso a localhost
4. Recargar la página

### No detecta "Jarvis"
1. Hablar más claro y fuerte
2. Verificar logs en consola del navegador (F12)
3. Probar variaciones de pronunciación

### TTS no funciona
1. Verificar volumen del sistema
2. Probar con Chrome/Edge
3. Recargar la página

---

## 📚 Documentación Adicional

- **Guía completa**: `artifacts/voice_test_instructions.md`
- **Resumen técnico**: `artifacts/voice_implementation_summary.md`
- **Demo visual**: `bash artifacts/voice_demo_visual.sh`

---

## 🎉 Estado del Proyecto

✅ **Escucha pasiva** con palabra clave  
✅ **Text-to-speech** automático  
✅ **UI intuitiva** y reactiva  
✅ **Conversaciones naturales**  
✅ **Documentación completa**  
✅ **Scripts de validación**  
✅ **Seguridad** implementada  
✅ **Compatibilidad** multi-navegador  

**Estado**: ✅ **COMPLETADO Y FUNCIONAL**

---

## 🚀 Próximos Pasos Recomendados

### Probar ahora
```bash
# Terminal 1: Iniciar servidor
python3 start_web.py --port 8091

# Terminal 2: Validar
bash artifacts/validate_voice_system.sh

# Navegador: Abrir
# http://localhost:8091
```

### Personalizar
- Cambiar palabra clave (editar `WAKE_WORD` en index.html)
- Ajustar timeout (editar `COMMAND_TIMEOUT`)
- Configurar idioma/voz (editar `recognition.lang`, `utterance.lang`)

### Mejorar
- [ ] Selector de idiomas en UI
- [ ] Selector de voces disponibles
- [ ] Indicador de nivel de audio
- [ ] Comandos especiales de voz

---

## 📊 Métricas

- **Líneas de código JavaScript**: ~400
- **Líneas de CSS**: ~90
- **Endpoints nuevos**: 2
- **Funciones nuevas**: 12
- **Estados UI**: 4
- **Archivos documentación**: 5

---

## 👨‍💻 Desarrollo

**Desarrollado**: 17 de noviembre de 2025  
**Versión**: 1.0.0  
**Tecnologías**: Web Speech API, FastAPI, JavaScript ES6+  
**Compatibilidad**: Chrome 33+, Edge 79+, Firefox 49+, Safari 14.1+

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisar documentación en `artifacts/`
2. Ejecutar script de validación
3. Verificar logs en consola del navegador
4. Verificar logs del servidor: `tail -f logs/*.log`

---

## ✨ Resumen

Jarvis ahora puede:
- 🎤 **Escuchar pasivamente** hasta que digas "Jarvis"
- 🗣️ **Entender comandos de voz** en español
- 🔊 **Responder con voz natural**
- 💬 **Mantener conversaciones naturales**
- 💾 **Guardar todo en historial**
- 🔄 **Funcionar continuamente sin interrupciones**

**¡Disfruta conversando con Jarvis! 🚀**
