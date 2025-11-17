#!/bin/bash
# Script para reiniciar Jarvis Web con recuperación de errores

echo "🔄 Reiniciando Jarvis Web con modo recuperación..."

# Matar procesos anteriores
pkill -f "start_web.py" 2>/dev/null
sleep 2

# Verificar que se hayan terminado
if pgrep -f "start_web.py" > /dev/null; then
    echo "⚠️  Procesos aún activos, forzando terminación..."
    pkill -9 -f "start_web.py"
    sleep 1
fi

cd /datos/repos/Personal/jarvisIAV2

# Limpiar logs antiguos
echo "🧹 Limpiando logs antiguos..."
> logs/errors.log
> logs/jarvis.log 2>/dev/null

# Configurar variables de entorno para modo recuperación
export JARVIS_DEBUG=0
export CUDA_VISIBLE_DEVICES=0

echo "🚀 Iniciando servidor en puerto 8091..."
echo "📝 Logs: tail -f logs/errors.log"
echo ""

# Iniciar servidor con nohup
nohup python3 start_web.py --port 8091 > /tmp/jarvis_web_startup.log 2>&1 &

JARVIS_PID=$!
echo "✅ Servidor iniciado con PID: $JARVIS_PID"

# Esperar inicialización
echo "⏳ Esperando inicialización (15 segundos)..."
sleep 15

# Verificar estado
echo ""
echo "🔍 Verificando estado del servidor..."

# Verificar proceso
if ps -p $JARVIS_PID > /dev/null 2>&1; then
    echo "✅ Proceso activo (PID: $JARVIS_PID)"
else
    echo "❌ ERROR: El proceso no está corriendo"
    echo "Ver logs de inicio: cat /tmp/jarvis_web_startup.log"
    exit 1
fi

# Verificar puerto
if lsof -i :8091 > /dev/null 2>&1; then
    echo "✅ Puerto 8091 está en uso"
else
    echo "⚠️  Puerto 8091 no está en uso aún"
fi

# Verificar health endpoint
echo ""
echo "🏥 Verificando health endpoint..."
HEALTH_CHECK=$(curl -s http://localhost:8091/health 2>&1)
if echo "$HEALTH_CHECK" | grep -q "ok"; then
    echo "✅ Health check OK"
else
    echo "⚠️  Health check no responde correctamente"
    echo "Respuesta: $HEALTH_CHECK"
fi

# Verificar status endpoint
echo ""
echo "📊 Verificando status del sistema..."
STATUS=$(curl -s http://localhost:8091/api/status 2>&1)
if echo "$STATUS" | grep -q "status"; then
    echo "✅ Status endpoint OK"
    echo "$STATUS" | jq '.' 2>/dev/null || echo "$STATUS"
else
    echo "⚠️  Status no responde correctamente"
    echo "Respuesta: $STATUS"
fi

# Probar chat con mensaje simple
echo ""
echo "💬 Probando endpoint de chat..."
CHAT_TEST=$(curl -s -X POST http://localhost:8091/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"Hola","timestamp":"2025-11-17T12:00:00"}' 2>&1)

if echo "$CHAT_TEST" | grep -q "response"; then
    RESPONSE=$(echo "$CHAT_TEST" | jq -r '.response' 2>/dev/null)
    if echo "$RESPONSE" | grep -iq "error"; then
        echo "⚠️  Chat responde pero con error:"
        echo "   $RESPONSE"
    else
        echo "✅ Chat funcionando correctamente"
        echo "   Respuesta: ${RESPONSE:0:100}..."
    fi
else
    echo "❌ Chat no responde correctamente"
    echo "Respuesta: $CHAT_TEST"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "🎯 RESUMEN"
echo "════════════════════════════════════════════════════"
echo "PID: $JARVIS_PID"
echo "Puerto: 8091"
echo "URL: http://localhost:8091"
echo ""
echo "📋 COMANDOS ÚTILES:"
echo "  Ver logs:      tail -f logs/errors.log"
echo "  Ver proceso:   ps -p $JARVIS_PID -f"
echo "  Detener:       kill $JARVIS_PID"
echo "  Estado:        curl http://localhost:8091/api/status | jq '.'"
echo ""
echo "🎤 PRUEBA DE VOZ:"
echo "  1. Abre: http://localhost:8091"
echo "  2. Presiona F12 (consola)"
echo "  3. Clic en '🎤 Voz'"
echo "  4. Clic en '🔍 Probar Micrófono'"
echo "  5. Di 'Jarvis' en voz alta"
echo ""
echo "════════════════════════════════════════════════════"
