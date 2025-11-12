# 🔄 INSTRUCCIONES PARA REINICIO Y PRUEBAS CON PLAYWRIGHT MCP

**Fecha**: 2025-11-12
**Estado**: ✅ MCP Playwright instalado correctamente

---

## ✅ LO QUE SE HA HECHO

### 1. **Commit de Mejoras** ✅
Se hizo commit de todas las mejoras implementadas:
```bash
git log -1 --oneline
# 9ce4b00 feat: Mejoras críticas de seguridad, rendimiento y UX en Jarvis Web
```

**Archivos modificados**:
- ✅ `src/modules/orchestrator/model_orchestrator.py` - Pre-carga de modelos
- ✅ `src/web/api.py` - CORS, validación, uptime, historial
- ✅ `src/web/templates/index.html` - XSS, retry, estilos
- ✅ `start_web.py` - Supresión de logs
- ✅ `MEJORAS_IMPLEMENTADAS.md` - Documentación completa
- ✅ `MEJORAS_ADICIONALES.md` - 12 mejoras adicionales identificadas

### 2. **MCP Playwright Instalado** ✅
```bash
# Instalado exitosamente
claude mcp list
# playwright: npx @playwright/mcp@latest - ✓ Connected
```

**Configuración guardada en**: `~/.claude.json`

---

## 🚀 CÓMO REINICIAR CLAUDE CODE PARA USAR PLAYWRIGHT MCP

### **Opción 1: Reinicio desde la sesión actual (Recomendado)**

En tu terminal actual donde está corriendo Claude Code, simplemente **cierra la sesión** y vuelve a ejecutar:

```bash
# En el directorio del proyecto
cd /datos/repos/Personal/jarvisIAV2

# Reiniciar Claude Code
claude
```

### **Opción 2: Desde una nueva terminal**

```bash
cd /datos/repos/Personal/jarvisIAV2
claude
```

El MCP de Playwright estará **automáticamente disponible** porque está configurado para este proyecto específico.

---

## 🧪 PRUEBAS EXHAUSTIVAS CON PLAYWRIGHT MCP

Una vez que reinicies Claude Code, podrás pedirme que haga pruebas exhaustivas como:

### **Pruebas Básicas**
```
"Usa Playwright MCP para abrir http://localhost:8090 y verificar que la página carga correctamente"
```

### **Pruebas de Funcionalidad**
```
"Usa Playwright MCP para:
1. Abrir http://localhost:8090
2. Verificar que el status muestra 'Listo'
3. Enviar un mensaje de prueba en el chat
4. Verificar que se recibe una respuesta
5. Tomar screenshot de la interfaz"
```

### **Pruebas de Seguridad**
```
"Usa Playwright MCP para verificar que la sanitización XSS funciona:
1. Enviar mensaje con <script>alert('XSS')</script>
2. Verificar que el script NO se ejecuta
3. Verificar que se muestra como texto escapado"
```

### **Pruebas de Responsividad**
```
"Usa Playwright MCP para:
1. Abrir http://localhost:8090 en viewport mobile (375x667)
2. Verificar que la interfaz se adapta correctamente
3. Probar el input y botón de envío
4. Tomar screenshots en mobile, tablet y desktop"
```

### **Pruebas de Errores**
```
"Usa Playwright MCP para:
1. Verificar el comportamiento cuando el servidor no responde
2. Verificar el retry automático
3. Verificar mensajes de error en la UI"
```

### **Pruebas de Rendimiento**
```
"Usa Playwright MCP para:
1. Medir el tiempo de carga de la página
2. Verificar que no hay errores en la consola del navegador
3. Medir el tiempo de respuesta del chat"
```

---

## 🎬 COMANDOS DISPONIBLES EN PLAYWRIGHT MCP

Una vez reiniciado, podré usar estos comandos:

### **Navegación**
- `playwright_navigate` - Ir a una URL
- `playwright_screenshot` - Tomar screenshot
- `playwright_pdf` - Generar PDF de la página

### **Interacción**
- `playwright_click` - Click en elemento
- `playwright_fill` - Rellenar input
- `playwright_select_option` - Seleccionar en dropdown
- `playwright_hover` - Hover sobre elemento

### **Inspección**
- `playwright_evaluate` - Ejecutar JavaScript
- `playwright_get_by_*` - Buscar elementos (text, role, label, etc.)
- `playwright_console` - Capturar logs de consola

### **Testing**
- `playwright_expect_*` - Aserciones (visible, hidden, value, etc.)

---

## 📋 CHECKLIST DE PRUEBAS EXHAUSTIVAS

Cuando reinicies, podré hacer estas pruebas:

### **Frontend** ✓
- [ ] Página carga sin errores
- [ ] Status indicator muestra estado correcto
- [ ] Chat input acepta texto
- [ ] Botón de envío funciona
- [ ] Mensajes se muestran correctamente
- [ ] Timestamps se formatean bien
- [ ] Favicon aparece
- [ ] Estilos de código se aplican
- [ ] Límite de 5000 caracteres funciona
- [ ] Sanitización XSS funciona
- [ ] Retry en errores funciona
- [ ] Responsividad mobile/tablet/desktop

### **Backend** ✓
- [ ] `/` sirve index.html
- [ ] `/api/status` devuelve JSON correcto
- [ ] `/api/history` devuelve historial
- [ ] `/api/chat` procesa mensajes
- [ ] Validación de input funciona (backend)
- [ ] CORS solo permite localhost
- [ ] Paginación en historial funciona
- [ ] Uptime se calcula correctamente

### **Integración** ✓
- [ ] Mensaje enviado → respuesta recibida
- [ ] Historial se guarda correctamente
- [ ] Limpiar historial funciona
- [ ] Errores se manejan gracefully
- [ ] Reconexión automática funciona

### **Rendimiento** ✓
- [ ] Primera carga < 3s
- [ ] Tiempo de respuesta razonable
- [ ] No hay memory leaks en frontend
- [ ] Modelo se pre-carga al inicio

### **Seguridad** ✓
- [ ] XSS bloqueado
- [ ] CORS restringido
- [ ] Input validation funciona
- [ ] No hay errores expuestos al usuario

---

## 🐛 SI ALGO FALLA

### **MCP no disponible después de reiniciar**

Verifica la configuración:
```bash
cat ~/.claude.json | grep -A 5 "jarvisIAV2"
```

Debería mostrar:
```json
{
  "projects": {
    "/datos/repos/Personal/jarvisIAV2": {
      "mcpServers": {
        "playwright": {
          "type": "stdio",
          "command": "npx",
          "args": ["@playwright/mcp@latest"]
        }
      }
    }
  }
}
```

### **Re-instalar si es necesario**

```bash
cd /datos/repos/Personal/jarvisIAV2
claude mcp remove playwright
claude mcp add playwright -s local npx '@playwright/mcp@latest'
claude mcp list  # Verificar
```

---

## 📊 MEJORAS IDENTIFICADAS PENDIENTES

Creé un documento completo con **12 mejoras adicionales** en:
- **`MEJORAS_ADICIONALES.md`** - Análisis detallado

**Prioridades altas**:
1. 🟠 Streaming de respuestas (SSE) - UX crítica
2. 🟠 Rate limiting - Seguridad
3. 🟡 GPU memory management - Estabilidad
4. 🟡 API keys - Autenticación opcional

---

## 🎉 RESUMEN

### **Estado Actual**
- ✅ 17/20 mejoras implementadas y commiteadas
- ✅ MCP Playwright instalado y configurado
- ✅ Documentación completa creada
- ✅ 12 mejoras adicionales identificadas

### **Próximos Pasos**
1. **REINICIAR** Claude Code en este directorio
2. **PROBAR** con Playwright MCP todas las funcionalidades
3. **IMPLEMENTAR** mejoras de Fase 1 si es necesario

### **Comandos para después del reinicio**
```bash
# Ejemplo de prueba completa
claude

# Luego en la sesión:
"Usa Playwright MCP para hacer una prueba completa de Jarvis:
1. Abrir http://localhost:8090
2. Verificar que carga correctamente
3. Enviar mensaje de prueba
4. Verificar respuesta
5. Probar sanitización XSS con <script>alert(1)</script>
6. Verificar límite de caracteres (5000+)
7. Tomar screenshots
8. Reportar cualquier problema encontrado"
```

---

## 🔗 ARCHIVOS CREADOS

1. **`MEJORAS_IMPLEMENTADAS.md`** - Changelog completo de las 17 mejoras
2. **`MEJORAS_ADICIONALES.md`** - 12 mejoras identificadas con priorización
3. **`INSTRUCCIONES_REINICIO.md`** - Este archivo

---

**Listo para reiniciar y probar con Playwright MCP! 🚀**

Cuando reinicies Claude Code en este directorio, el MCP de Playwright estará automáticamente disponible y podrás pedirme que haga pruebas exhaustivas de toda la interfaz web de Jarvis.
