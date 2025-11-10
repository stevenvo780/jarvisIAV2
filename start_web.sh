#!/bin/bash
# Quick Start Script para Jarvis Web Interface

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════╗"
echo "║     🤖 JARVIS AI - WEB INTERFACE LAUNCHER         ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PORT=${1:-8090}
DEBUG_MODE=${2:-false}

echo -e "${BLUE}📋 Configuración:${NC}"
echo "   Puerto: $PORT"
echo "   Debug: $DEBUG_MODE"
echo ""

# Check Python
echo -e "${BLUE}🔍 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 no encontrado${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 encontrado: $(python3 --version)${NC}"

# Check dependencies
echo -e "${BLUE}🔍 Verificando dependencias...${NC}"
MISSING_DEPS=()

if ! python3 -c "import fastapi" 2>/dev/null; then
    MISSING_DEPS+=("fastapi")
fi

if ! python3 -c "import uvicorn" 2>/dev/null; then
    MISSING_DEPS+=("uvicorn")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Faltan dependencias: ${MISSING_DEPS[*]}${NC}"
    echo -e "${BLUE}📦 Instalando dependencias...${NC}"
    pip install "${MISSING_DEPS[@]}"
    echo -e "${GREEN}✅ Dependencias instaladas${NC}"
else
    echo -e "${GREEN}✅ Todas las dependencias instaladas${NC}"
fi

# Check CUDA
echo -e "${BLUE}🔍 Verificando GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi --list-gpus 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ GPUs disponibles: $GPU_COUNT${NC}"
else
    echo -e "${YELLOW}⚠️  nvidia-smi no encontrado (modo CPU)${NC}"
fi

echo ""
echo -e "${BLUE}🚀 Iniciando Jarvis Web Interface...${NC}"
echo ""

# Set GPU (usar GPU 0 por defecto)
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}

# Build command
CMD="python3 start_web.py --port $PORT"
if [ "$DEBUG_MODE" = "true" ]; then
    CMD="$CMD --debug"
fi

echo -e "${GREEN}📱 Abre tu navegador en:${NC}"
echo -e "   ${BLUE}http://localhost:$PORT${NC}"
echo ""
echo -e "${YELLOW}💡 Tip: Presiona Ctrl+C para detener${NC}"
echo ""
echo "════════════════════════════════════════════════════"
echo ""

# Execute
exec $CMD
