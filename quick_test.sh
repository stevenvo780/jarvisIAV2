#!/bin/bash
# Quick Test - Verificación rápida del sistema JarvisIA V2

echo "🧪 TEST RÁPIDO DE JARVIS IA V2"
echo "=============================="
echo ""

# 1. Health Check
echo "1️⃣  Health Check..."
HEALTH=$(curl -s http://localhost:8090/health)
if echo "$HEALTH" | grep -q "ok"; then
    echo "   ✅ API está respondiendo"
else
    echo "   ❌ API no responde"
    exit 1
fi
echo ""

# 2. System Status
echo "2️⃣  System Status..."
STATUS=$(curl -s http://localhost:8090/api/status)
echo "   $STATUS" | jq .
echo ""

# 3. GPU Check
echo "3️⃣  GPU Status..."
nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader | while read line; do
    echo "   GPU $line"
done
echo ""

# 4. Process Check
echo "4️⃣  Process Check..."
PROC=$(ps aux | grep "start_web.py" | grep -v grep | wc -l)
if [ "$PROC" -gt 0 ]; then
    echo "   ✅ Proceso activo"
    ps aux | grep "start_web.py" | grep -v grep | awk '{print "   PID: " $2 ", CPU: " $3 "%, MEM: " $4 "%"}'
else
    echo "   ❌ Proceso no encontrado"
    exit 1
fi
echo ""

# 5. Test Simple de Chat
echo "5️⃣  Test de Chat (simple)..."
CHAT_RESPONSE=$(curl -s -X POST http://localhost:8090/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Di hola en una palabra", "stream": false}' \
  --max-time 120)

if [ $? -eq 0 ]; then
    echo "   ✅ Chat endpoint respondió"
    echo "$CHAT_RESPONSE" | jq -r '.response' | head -c 100
    echo "..."
else
    echo "   ⚠️  Chat endpoint timeout o error (normal en primera carga)"
fi
echo ""

echo "=============================="
echo "🎉 TEST COMPLETADO"
echo ""
echo "📋 Comandos útiles:"
echo "   - Ver logs: tail -f logs/web_startup.log"
echo "   - Navegador: http://localhost:8090"
echo "   - Detener: kill \$(pgrep -f start_web.py)"
