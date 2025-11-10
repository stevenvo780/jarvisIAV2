#!/usr/bin/env bash
# Ciclo infinito simple: una consulta por vez

QUERIES=(
    "¿Cuánto es 12 * 7?"
    "¿Qué es la recursividad?"
    "Define inteligencia artificial"
    "¿Cómo funciona HTTP?"
    "¿Qué es Python?"
    "Explica Git en 2 líneas"
    "¿Cuál es la raíz de 256?"
    "¿Quién fue Alan Turing?"
    "¿Qué es Docker?"
    "Define algoritmo"
)

iteration=1
while true; do
    query="${QUERIES[$((iteration % ${#QUERIES[@]}))]}"
    echo "[$iteration] $(date '+%H:%M:%S') → $query"
    
    timeout 90 python3 main.py -q "$query" -m qwen-14b 2>&1 | grep -E "🟢|Error" | head -3
    
    echo "✓ Completado. Esperando 5s..."
    sleep 5
    
    ((iteration++))
done
