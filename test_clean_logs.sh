#!/bin/bash
# Test para verificar que los logs verbosos están suprimidos
# 
# Uso: ./test_clean_logs.sh
#
# Verifica que al ejecutar Jarvis:
# - NO aparezcan logs de safetensors loading
# - NO aparezcan logs de Gloo (torch.distributed)
# - NO aparezcan logs de CUDA graphs
# - NO aparezcan barras de progreso de tqdm
# - SÍ aparezcan los logs normales de interfaz de usuario

echo "🧪 Iniciando test de logs limpios..."

# Archivo temporal para capturar output
LOG_FILE="/tmp/jarvis_clean_test.log"
rm -f "$LOG_FILE"

# Iniciar Jarvis en background
CUDA_VISIBLE_DEVICES=0 python3 main.py > "$LOG_FILE" 2>&1 &
PID=$!

echo "⏳ Esperando 90 segundos para que cargue el modelo..."
sleep 90

# Verificar si los logs verbosos están presentes
echo ""
echo "📊 Verificando presencia de logs verbosos..."

ISSUES_FOUND=0

if grep -q "Loading safetensors" "$LOG_FILE"; then
    echo "❌ FALLO: Se encontraron logs de safetensors"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "✅ PASS: No hay logs de safetensors"
fi

if grep -q "\[Gloo\]" "$LOG_FILE"; then
    echo "❌ FALLO: Se encontraron logs de Gloo (torch.distributed)"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "✅ PASS: No hay logs de Gloo"
fi

if grep -q "Capturing CUDA graphs" "$LOG_FILE"; then
    echo "❌ FALLO: Se encontraron logs de CUDA graphs"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "✅ PASS: No hay logs de CUDA graphs"
fi

if grep -q "it/s\]" "$LOG_FILE"; then
    echo "⚠️  ADVERTENCIA: Se encontraron barras de progreso de tqdm"
    # No contar como fallo crítico
else
    echo "✅ PASS: No hay barras de progreso de tqdm"
fi

# Verificar que los logs normales de Jarvis sí estén
if grep -q "Starting Jarvis AI Assistant" "$LOG_FILE"; then
    echo "✅ PASS: Logs normales de Jarvis presentes"
else
    echo "❌ FALLO: Los logs normales de Jarvis no están presentes"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Limpiar
kill $PID 2>/dev/null
wait $PID 2>/dev/null

echo ""
echo "📝 Primeras 50 líneas del log:"
head -50 "$LOG_FILE"

echo ""
if [ $ISSUES_FOUND -eq 0 ]; then
    echo "✅ TEST EXITOSO: Logs limpios verificados"
    exit 0
else
    echo "❌ TEST FALLIDO: Se encontraron $ISSUES_FOUND problemas"
    exit 1
fi
