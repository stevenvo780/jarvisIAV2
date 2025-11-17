# 🔧 SOLUCIÓN DE PROBLEMAS: No Escucha / No Detecta Voz

## ⚠️ PROBLEMA REPORTADO
"No es capaz de escucharme, le digo jarvis y nunca se activa o escribe nada, no toma órdenes"

---

## ✅ CAMBIOS REALIZADOS

Se han mejorado las siguientes funcionalidades:

### 1. **Detección de Palabra Clave Mejorada**
- Ahora acepta **múltiples variaciones**: jarvis, yarbis, jarbis, harbis, yarvis
- Mejor logging para debugging
- Muestra confianza del reconocimiento

### 2. **Manejo de Errores Robusto**
- Mensajes de error específicos según el tipo
- Mejor gestión de reconexión automática
- Detección de problemas de permisos

### 3. **Botón de Prueba del Micrófono**
- Nuevo botón "🔍 Probar Micrófono" en el badge flotante
- Permite verificar que el micrófono funcione antes de usar el sistema
- Da feedback inmediato

### 4. **Logs Detallados**
- Cada evento ahora registra información completa en consola
- Incluye estado actual, confianza, y si es parcial/final
- Facilita el debugging

---

## 🚀 CÓMO PROBAR LOS CAMBIOS

### **PASO 1: Recargar la Página**
```
1. Ve a: http://localhost:8091
2. Presiona F5 o Ctrl+R (Cmd+R en Mac)
3. Acepta los permisos del micrófono si aparecen
```

### **PASO 2: Abrir Consola del Navegador**
```
1. Presiona F12 (o clic derecho → Inspeccionar)
2. Ve a la pestaña "Console"
3. Deja la consola abierta para ver los logs
```

### **PASO 3: Probar el Micrófono**
```
1. Haz clic en el botón "🎤 Voz" en el header
2. Aparecerá un badge flotante (esquina inferior derecha)
3. Haz clic en "🔍 Probar Micrófono"
4. Di algo en voz ALTA (ej: "Hola")
5. Verifica en consola que veas: ✅ MICRÓFONO OK - Escuchado: ...
```

### **PASO 4: Activar Modo Voz**
```
1. Si la prueba funcionó, el modo voz ya está activo
2. Di "JARVIS" en voz ALTA y CLARA
3. Verifica en consola los logs:
   🗣️ Escuchado: jarvis (final) Confianza: XX%
   ✅ ¡Palabra clave detectada!
```

### **PASO 5: Dar Comando**
```
1. Tras escuchar "Sí, dime"
2. Di tu pregunta claramente
3. Ej: "Explícame qué es Python"
```

---

## 🔍 CHECKLIST DE DIAGNÓSTICO

### ☐ **Permisos del Micrófono**
```
□ Haz clic en el candado en la barra de URL
□ Verifica que "Micrófono" esté en "Permitir"
□ Si está bloqueado, cámbialo y recarga (F5)
```

### ☐ **Navegador Correcto**
```
□ Usa Chrome o Edge (mejor soporte)
□ Versión actualizada del navegador
□ No uses modo incógnito (puede bloquear permisos)
```

### ☐ **Hardware**
```
□ Micrófono conectado y funcionando
□ No está siendo usado por otra aplicación
□ Nivel de volumen del micrófono adecuado
□ Prueba el micrófono en otra app (ej: grabar audio)
```

### ☐ **Consola del Navegador**
```
□ Consola abierta (F12)
□ Sin errores en ROJO
□ Ves logs "🎤 Reconocimiento iniciado"
□ Ves logs "🗣️ Escuchado: ..." cuando hablas
```

---

## 🐛 ERRORES ESPECÍFICOS Y SOLUCIONES

### ❌ **ERROR: "not-allowed" o "NotAllowedError"**
**Causa:** Permisos denegados

**Solución:**
1. Haz clic en el candado en la URL
2. Micrófono → Permitir
3. Recarga la página (F5)
4. Vuelve a hacer clic en "🎤 Voz"

---

### ❌ **ERROR: "audio-capture"**
**Causa:** No se puede capturar audio

**Solución:**
1. Cierra otras apps que usen el micrófono (Zoom, Discord, etc.)
2. Verifica en Configuración del Sistema:
   - Linux: `pavucontrol` → Pestaña Input
   - Windows: Configuración → Privacidad → Micrófono
   - Mac: Preferencias → Seguridad → Micrófono
3. Reinicia el navegador

---

### ❌ **No aparecen logs "🗣️ Escuchado: ..." en consola**
**Causa:** El reconocimiento no está recibiendo audio

**Solución:**
1. Usa el botón "🔍 Probar Micrófono"
2. Si la prueba NO funciona:
   - El micrófono no está conectado
   - Los permisos están bloqueados
   - El navegador no soporta Web Speech API
3. Si la prueba SÍ funciona:
   - Verifica que el modo voz esté ACTIVO (botón verde)
   - Habla más FUERTE
   - Acércate más al micrófono

---

### ❌ **Logs aparecen pero no detecta "Jarvis"**
**Causa:** Pronunciación o configuración de idioma

**Solución:**
1. Verifica en consola qué detecta exactamente
2. Prueba variaciones:
   - "YARBIS"
   - "JARBIS"
   - "HARBIS"
3. Habla más claro y despacio
4. Verifica que los logs muestren:
   ```
   🗣️ Escuchado: jarvis (final) Confianza: XX%
   ```
5. Si dice "(parcial)" en lugar de "(final)", espera un momento

---

### ❌ **Se activa pero no procesa el comando**
**Causa:** Timeout o comando no finalizado

**Solución:**
1. Tras decir "Jarvis", tienes 10 segundos
2. Di tu comando completo SIN PAUSAS
3. Verifica en consola:
   ```
   📝 Procesando comando: [tu texto]
   ```
4. Si no ves ese log, el comando no se finalizó correctamente

---

## 📊 LOGS ESPERADOS (Flujo Completo)

```javascript
// 1. Al cargar página
✅ Text-to-Speech inicializado
✅ Reconocimiento de voz inicializado

// 2. Al activar modo voz
🚀 Intentando iniciar reconocimiento de voz...
🎤 Reconocimiento de voz iniciado
✅ Modo voz iniciado (escucha pasiva)
📢 IMPORTANTE: Asegúrate de hablar en voz alta y clara
📢 Variaciones aceptadas: "jarvis", "yarbis", "jarbis"

// 3. Al decir algo (cualquier cosa)
🗣️ Escuchado: hola (parcial) Confianza: 0.8 Estado: PASIVO
🗣️ Escuchado: hola que tal (final) Confianza: 0.9 Estado: PASIVO

// 4. Al decir "Jarvis"
🗣️ Escuchado: jarvis (final) Confianza: 0.95 Estado: PASIVO
✅ ¡Palabra clave detectada!
🎯 Palabra clave detectada - Activando modo comando

// 5. Al dar comando
🗣️ Escuchado: qué es python (parcial) Confianza: 0.8 Estado: COMANDO
🗣️ Escuchado: qué es python (final) Confianza: 0.9 Estado: COMANDO
📝 Procesando comando: qué es python
```

---

## 🎯 TEST RÁPIDO DE 1 MINUTO

### Ejecuta este test paso a paso:

```bash
# 1. Verificar servidor
curl http://localhost:8091/health
# Debe responder: {"status":"ok",...}

# 2. Abrir navegador
# Chrome/Edge en: http://localhost:8091

# 3. Abrir consola (F12)

# 4. Clic en "🎤 Voz"
# Debe aparecer badge flotante

# 5. Clic en "🔍 Probar Micrófono"
# Di: "Hola"
# Consola debe mostrar: ✅ MICRÓFONO OK

# 6. Di en voz ALTA: "JARVIS"
# Consola debe mostrar: ✅ ¡Palabra clave detectada!

# 7. Di: "Qué hora es"
# Debe procesarse y responder
```

**Si TODOS los pasos funcionan:** ✅ Sistema OK
**Si falla en paso 5:** ❌ Problema de permisos/hardware
**Si falla en paso 6:** ❌ Problema de reconocimiento/pronunciación
**Si falla en paso 7:** ❌ Problema de procesamiento/backend

---

## 🔧 COMANDOS DE DIAGNÓSTICO

```bash
# Script completo de diagnóstico
bash /datos/repos/Personal/jarvisIAV2/artifacts/diagnose_voice.sh

# Verificar servidor
curl http://localhost:8091/api/status | jq '.'

# Verificar config de voz
curl http://localhost:8091/api/voice/config | jq '.'
```

---

## 📱 CONTACTO Y SOPORTE

Si después de seguir TODOS los pasos anteriores el problema persiste:

1. **Copia TODOS los logs de la consola** (desde que cargas la página hasta que falla)
2. **Toma captura** de:
   - La consola del navegador (F12)
   - Los permisos del micrófono (candado en URL)
3. **Anota**:
   - Navegador y versión
   - Sistema operativo
   - Qué dice EXACTAMENTE en la consola cuando hablas
   - Si el botón "🔍 Probar Micrófono" funciona o no

---

## ✅ CAMBIOS EN EL CÓDIGO

### Archivos Modificados:
- `src/web/templates/index.html`:
  - Mejora en detección de palabra clave (líneas ~606-630)
  - Mejor manejo de errores (líneas ~632-650)
  - Reinicio automático robusto (líneas ~652-675)
  - Función de prueba de micrófono (líneas ~836-885)
  - Mejores mensajes de debug (líneas ~770-795)

### Archivos Nuevos:
- `artifacts/diagnose_voice.sh` - Script de diagnóstico completo
- `artifacts/TROUBLESHOOTING_VOICE.md` - Este documento

---

## 🎉 SIGUIENTE PASO

1. **Recarga la página** en el navegador (F5)
2. **Sigue el test rápido** de arriba
3. **Revisa los logs** en la consola del navegador
4. **Usa el botón de prueba** del micrófono

Si todo funciona: ¡Disfruta conversando con Jarvis! 🚀

Si sigue sin funcionar: Envía los logs completos para investigación más profunda.
