#!/bin/bash
# Script para ejecutar Jarvis IA V2
# Uso: ./run_jarvis.sh [opciones]
# Ejemplos:
#   ./run_jarvis.sh                              # Modo interactivo
#   ./run_jarvis.sh --query "Tu pregunta"        # Modo comando
#   ./run_jarvis.sh --stats                      # Ver estadísticas

cd "$(dirname "$0")"
source .venv/bin/activate
python main.py "$@"
