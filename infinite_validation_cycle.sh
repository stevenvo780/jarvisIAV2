#!/usr/bin/env bash
# Ciclo infinito de validación para Jarvis - NO PARAR
# Ejecuta consultas variadas, detecta errores, prioriza modelo local

set -euo pipefail

QUERIES=(
    "¿Cuál es la capital de Francia?"
    "Explica fotosíntesis en 10 palabras"
    "Genera código: factorial en Python"
    "Calcula: 123 + 456 - 78"
    "Resume brevemente: Teoría de la relatividad"
    "Lista 5 lenguajes de programación populares"
    "¿Qué es un agujero negro?"
    "Define: Machine Learning"
    "¿Cuántos continentes hay?"
    "Escribe un haiku sobre el océano"
    "Explica qué es DNA en 15 palabras"
    "¿Quién escribió 'Don Quijote'?"
    "Genera función Python: ordenar lista"
    "Calcula: 50 * 8 / 4"
    "Define brevemente: blockchain"
    "¿Cuál es el océano más grande?"
    "Explica gravedad en términos simples"
    "Lista 3 componentes de una computadora"
    "¿Qué es HTTP?"
    "Traduce 'Hello World' al español"
)

ITERATION=1
LOG_FILE="logs/infinite_validation_$(date +%Y%m%d_%H%M%S).log"

mkdir -p logs

echo "🚀 CICLO INFINITO INICIADO - $(date)" | tee -a "$LOG_FILE"
echo "📊 Total queries: ${#QUERIES[@]}" | tee -a "$LOG_FILE"
echo "🔄 Iterando indefinidamente... CTRL+C para detener" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

while true; do
    QUERY_IDX=$((RANDOM % ${#QUERIES[@]}))
    QUERY="${QUERIES[$QUERY_IDX]}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
    echo "🔵 ITERACIÓN $ITERATION - $(date +%H:%M:%S)" | tee -a "$LOG_FILE"
    echo "📝 Query: $QUERY" | tee -a "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
    
    # Ejecutar query y capturar salida
    START_TIME=$(date +%s)
    
    if python3 main.py --query "$QUERY" 2>&1 | tee -a "$LOG_FILE" | tail -15; then
        EXIT_CODE=0
    else
        EXIT_CODE=$?
    fi
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ SUCCESS (${DURATION}s)" | tee -a "$LOG_FILE"
    else
        echo "❌ ERROR: Exit code $EXIT_CODE (${DURATION}s)" | tee -a "$LOG_FILE"
    fi
    
    echo "" | tee -a "$LOG_FILE"
    
    # Cleanup procesos zombies vLLM
    ZOMBIE_PIDS=$(pgrep -f "EngineCore" 2>/dev/null || true)
    if [ -n "$ZOMBIE_PIDS" ]; then
        echo "🧹 Limpiando procesos zombie: $ZOMBIE_PIDS" | tee -a "$LOG_FILE"
        echo "$ZOMBIE_PIDS" | xargs kill -9 2>/dev/null || true
    fi
    
    ITERATION=$((ITERATION + 1))
    
    # Breve pausa para evitar saturación
    sleep 2
done
