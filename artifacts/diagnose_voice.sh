#!/bin/bash
# Script de diagnóstico para problemas de reconocimiento de voz

echo "════════════════════════════════════════════════════════════"
echo "🔍 DIAGNÓSTICO DE VOZ - Jarvis"
echo "════════════════════════════════════════════════════════════"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "📋 GUÍA DE DIAGNÓSTICO PASO A PASO"
echo "════════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}1. VERIFICAR NAVEGADOR${NC}"
echo "   ✓ Chrome/Edge: Mejor soporte (RECOMENDADO)"
echo "   ⚠️  Firefox: Soporte limitado"
echo "   ⚠️  Safari: Soporte limitado"
echo ""

echo -e "${BLUE}2. VERIFICAR PERMISOS DEL MICRÓFONO${NC}"
echo "   • Abre Chrome en: http://localhost:8091"
echo "   • Haz clic en el ícono de CANDADO en la barra de direcciones"
echo "   • Verifica que 'Micrófono' esté en 'Permitir'"
echo "   • Si está bloqueado, cámbialo a 'Permitir' y RECARGA la página"
echo ""

echo -e "${BLUE}3. ABRIR CONSOLA DEL NAVEGADOR${NC}"
echo "   • Presiona F12 (o Cmd+Opt+I en Mac)"
echo "   • Ve a la pestaña 'Console'"
echo "   • Busca mensajes que digan:"
echo "     ${GREEN}✅ '🎤 Reconocimiento de voz iniciado'${NC}"
echo "     ${GREEN}✅ '🗣️ Escuchado: ...'${NC}"
echo "   • Si ves errores en ROJO, anótalos"
echo ""

echo -e "${BLUE}4. PROBAR EL MICRÓFONO${NC}"
echo "   • Haz clic en el botón '🎤 Voz'"
echo "   • Aparecerá un badge flotante en la esquina inferior derecha"
echo "   • Haz clic en '🔍 Probar Micrófono' en el badge"
echo "   • Di algo en voz alta"
echo "   • Deberías ver en la consola: ${GREEN}'✅ MICRÓFONO OK - Escuchado: ...'${NC}"
echo ""

echo -e "${BLUE}5. ACTIVAR MODO VOZ${NC}"
echo "   • Haz clic en el botón '🎤 Voz' en el header"
echo "   • El botón debe cambiar a: '🎤 ◉ Escuchando'"
echo "   • En la consola verás:"
echo "     ${GREEN}'🚀 Intentando iniciar reconocimiento de voz...'${NC}"
echo "     ${GREEN}'✅ Modo voz iniciado (escucha pasiva)'${NC}"
echo ""

echo -e "${BLUE}6. DECIR 'JARVIS'${NC}"
echo "   • Habla en voz ALTA y CLARA"
echo "   • Di: 'JARVIS' (o variaciones: 'YARBIS', 'JARBIS')"
echo "   • En la consola deberías ver:"
echo "     ${GREEN}'🗣️ Escuchado: jarvis (final) Confianza: XX%'${NC}"
echo "     ${GREEN}'✅ ¡Palabra clave detectada!'${NC}"
echo "   • El botón debe cambiar a ROJO parpadeante"
echo "   • Deberías escuchar: 'Sí, dime'"
echo ""

echo -e "${BLUE}7. DAR COMANDO${NC}"
echo "   • Una vez activado (botón rojo), tienes 10 segundos"
echo "   • Di tu pregunta o comando claramente"
echo "   • Ejemplo: 'Explícame qué es Python'"
echo "   • La transcripción aparecerá en tiempo real en el badge"
echo ""

echo "════════════════════════════════════════════════════════════"
echo -e "${YELLOW}⚠️  PROBLEMAS COMUNES Y SOLUCIONES${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""

echo -e "${RED}❌ 'NotAllowedError' o 'not-allowed'${NC}"
echo "   CAUSA: Permisos denegados"
echo "   SOLUCIÓN:"
echo "   1. Haz clic en el candado en la URL"
echo "   2. Cambia Micrófono a 'Permitir'"
echo "   3. Recarga la página (F5)"
echo ""

echo -e "${RED}❌ 'audio-capture' error${NC}"
echo "   CAUSA: No se puede acceder al micrófono"
echo "   SOLUCIÓN:"
echo "   1. Verifica que ningún otro programa esté usando el micrófono"
echo "   2. Verifica en Configuración del Sistema → Privacidad → Micrófono"
echo "   3. Asegúrate de que el navegador tenga permisos"
echo ""

echo -e "${RED}❌ No detecta 'Jarvis'${NC}"
echo "   CAUSA: Reconocimiento no escucha o mala pronunciación"
echo "   SOLUCIÓN:"
echo "   1. Habla MÁS FUERTE y más CLARO"
echo "   2. Prueba variaciones: 'YARBIS', 'JARBIS', 'HARBIS'"
echo "   3. Verifica en la consola que veas '🗣️ Escuchado: ...'"
echo "   4. Si no ves NADA en consola, el micrófono no está funcionando"
echo ""

echo -e "${RED}❌ Se desactiva solo${NC}"
echo "   CAUSA: Normal después de 10 segundos sin comando"
echo "   SOLUCIÓN:"
echo "   1. Es comportamiento normal"
echo "   2. Vuelve a decir 'Jarvis' para reactivar"
echo ""

echo -e "${RED}❌ 'no-speech' error${NC}"
echo "   CAUSA: No se detectó voz (es normal, solo espera)"
echo "   SOLUCIÓN:"
echo "   1. Este error es normal y no detiene el reconocimiento"
echo "   2. Solo significa que está esperando que hables"
echo ""

echo "════════════════════════════════════════════════════════════"
echo -e "${BLUE}🔧 COMANDOS DE VERIFICACIÓN${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""

echo "# Verificar que el servidor esté corriendo:"
echo "curl http://localhost:8091/health"
echo ""

echo "# Verificar configuración de voz:"
echo "curl http://localhost:8091/api/voice/config | jq '.'"
echo ""

echo "# Ver logs del servidor:"
echo "tail -f logs/*.log 2>/dev/null || echo 'No hay logs disponibles'"
echo ""

echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ CHECKLIST DE VERIFICACIÓN${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""

# Verificaciones automáticas
echo "Verificando servidor..."
if curl -s http://localhost:8091/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Servidor web activo"
else
    echo -e "  ${RED}✗${NC} Servidor web NO responde"
    echo "     Inicia con: python3 start_web.py --port 8091"
fi

echo ""
echo "Verificando endpoints de voz..."
if curl -s http://localhost:8091/api/voice/config > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Endpoints de voz disponibles"
else
    echo -e "  ${RED}✗${NC} Endpoints de voz NO disponibles"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo -e "${BLUE}📝 LOGS A REVISAR EN CONSOLA DEL NAVEGADOR${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""

cat << 'EOF'
LOGS ESPERADOS (en orden):

1. Al cargar la página:
   ✅ Text-to-Speech inicializado
   ✅ Reconocimiento de voz inicializado

2. Al hacer clic en "🎤 Voz":
   🚀 Intentando iniciar reconocimiento de voz...
   🎤 Reconocimiento de voz iniciado
   ✅ Modo voz iniciado (escucha pasiva)
   📢 IMPORTANTE: Asegúrate de hablar en voz alta y clara

3. Al hablar:
   🗣️ Escuchado: [tu texto] (parcial/final) Confianza: XX%

4. Al decir "Jarvis":
   🗣️ Escuchado: jarvis (final) Confianza: XX% Estado: PASIVO
   ✅ ¡Palabra clave detectada!
   🎯 Palabra clave detectada - Activando modo comando

5. Al dar comando:
   🗣️ Escuchado: [tu comando] (final) Confianza: XX% Estado: COMANDO
   📝 Procesando comando: [tu comando]

LOGS DE ERROR (NO deberías ver estos):
   ❌ Error en reconocimiento: not-allowed
   ❌ Error en reconocimiento: audio-capture
   ❌ Error en reconocimiento: network
EOF

echo ""
echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}🎯 RESUMEN DE PASOS${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "1. Abre Chrome/Edge en http://localhost:8091"
echo "2. Permite el acceso al micrófono (ícono de candado)"
echo "3. Abre consola (F12)"
echo "4. Haz clic en '🎤 Voz'"
echo "5. Haz clic en '🔍 Probar Micrófono' (en el badge flotante)"
echo "6. Si la prueba funciona, di 'JARVIS' en voz alta"
echo "7. Cuando escuches 'Sí, dime', haz tu pregunta"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
