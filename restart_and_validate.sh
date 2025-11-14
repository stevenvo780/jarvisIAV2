#!/bin/bash
# Script de automatización completa: Reinicio y validación de JarvisIA V2

set -e

echo "================================================"
echo "🚀 JarvisIA V2 - Reinicio y Validación Completa"
echo "================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para logging
log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# 1. Limpiar procesos existentes
echo "🧹 Paso 1: Limpiando procesos existentes..."
pkill -9 -f "start_web.py" 2>/dev/null || true
pkill -9 -f "python3.*jarvis" 2>/dev/null || true
docker-compose down 2>/dev/null || true
sleep 2
log_success "Procesos limpiados"
echo ""

# 2. Limpiar memoria GPU
echo "🎮 Paso 2: Limpiando memoria GPU..."
if command -v nvidia-smi &> /dev/null; then
    # Obtener PIDs de procesos VLLM o modelos en GPU
    GPU_PIDS=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null || echo "")
    if [ ! -z "$GPU_PIDS" ]; then
        echo "$GPU_PIDS" | while read pid; do
            if [ ! -z "$pid" ] && [ "$pid" -gt 0 ]; then
                kill -9 $pid 2>/dev/null || true
            fi
        done
        sleep 3
    fi
    
    # Verificar memoria liberada
    GPU_MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n1)
    if [ "$GPU_MEM" -lt 1000 ]; then
        log_success "Memoria GPU liberada: ${GPU_MEM}MB"
    else
        log_warning "Memoria GPU aún ocupada: ${GPU_MEM}MB"
    fi
else
    log_warning "nvidia-smi no disponible, saltando limpieza GPU"
fi
echo ""

# 3. Limpiar caché Python
echo "🗑️  Paso 3: Limpiando caché Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
log_success "Caché Python limpiado"
echo ""

# 4. Verificar dependencias
echo "📦 Paso 4: Verificando dependencias..."
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt --no-cache-dir 2>&1 | grep -v "already satisfied" || true
    log_success "Dependencias verificadas"
else
    log_warning "requirements.txt no encontrado"
fi
echo ""

# 5. Levantar el programa
echo "🚀 Paso 5: Levantando JarvisIA V2..."
export JARVIS_DEBUG=0
export GLOO_LOG_LEVEL=ERROR
export NCCL_LOG_LEVEL=ERROR

# Iniciar en background y capturar PID
nohup python3 start_web.py --port 8090 > logs/web_startup.log 2>&1 &
WEB_PID=$!
echo $WEB_PID > /tmp/jarvis_web.pid

log_success "Programa iniciado (PID: $WEB_PID)"
echo ""

# 6. Esperar a que el servidor esté listo
echo "⏳ Paso 6: Esperando inicialización del servidor..."
MAX_WAIT=60
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8090/health > /dev/null 2>&1; then
        log_success "Servidor listo en http://localhost:8090"
        break
    fi
    sleep 2
    COUNTER=$((COUNTER + 2))
    echo -n "."
done
echo ""

if [ $COUNTER -ge $MAX_WAIT ]; then
    log_error "Servidor no respondió después de ${MAX_WAIT}s"
    echo "📋 Últimas líneas del log:"
    tail -n 20 logs/web_startup.log
    exit 1
fi
echo ""

# 7. Ejecutar tests automatizados
echo "🧪 Paso 7: Ejecutando suite de tests automatizados..."
pytest tests/test_automated_full_suite.py -v --tb=short -x 2>&1 | tee /tmp/test_results.log

TEST_EXIT_CODE=${PIPESTATUS[0]}

if [ $TEST_EXIT_CODE -eq 0 ]; then
    log_success "Todos los tests pasaron exitosamente"
else
    log_error "Algunos tests fallaron (exit code: $TEST_EXIT_CODE)"
fi
echo ""

# 8. Verificar estado final
echo "🔍 Paso 8: Verificación final del sistema..."

# Verificar proceso vivo
if ps -p $WEB_PID > /dev/null; then
    log_success "Proceso principal activo (PID: $WEB_PID)"
else
    log_error "Proceso principal no está corriendo"
fi

# Verificar endpoint health
if curl -s http://localhost:8090/health > /dev/null 2>&1; then
    HEALTH_DATA=$(curl -s http://localhost:8090/health)
    log_success "API respondiendo correctamente"
    echo "   $HEALTH_DATA"
else
    log_error "API no responde"
fi

# Verificar memoria GPU
if command -v nvidia-smi &> /dev/null; then
    GPU_MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n1)
    GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -n1)
    log_success "GPU - Memoria: ${GPU_MEM}MB, Utilización: ${GPU_UTIL}%"
fi
echo ""

# 9. Resumen final
echo "================================================"
echo "📊 RESUMEN FINAL"
echo "================================================"
echo ""
echo "✅ Programa: JarvisIA V2"
echo "🌐 URL: http://localhost:8090"
echo "🔢 PID: $WEB_PID"
echo "📝 Log: logs/web_startup.log"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}🎉 SISTEMA OPERATIVO Y VALIDADO${NC}"
else
    echo -e "${YELLOW}⚠️  SISTEMA OPERATIVO CON ADVERTENCIAS${NC}"
fi

echo ""
echo "Comandos útiles:"
echo "  - Ver logs: tail -f logs/web_startup.log"
echo "  - Estado: curl http://localhost:8090/health"
echo "  - Detener: kill $WEB_PID"
echo "  - GPU: nvidia-smi"
echo ""

exit $TEST_EXIT_CODE
