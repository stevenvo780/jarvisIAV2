#!/bin/bash
# Quick Start Script para Jarvis IA V2
# Descarga y configura modelos para RTX 5070 Ti

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_header() {
    echo -e "${BOLD}${BLUE}======================================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}======================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
clear
print_header "🤖 Jarvis IA V2 - Quick Start"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "main.py" ]; then
    print_error "Por favor ejecuta este script desde el directorio raíz de jarvisIAV2"
    exit 1
fi

# Verificar entorno virtual
if [ ! -d ".venv" ]; then
    print_error "Entorno virtual no encontrado. Ejecuta primero: python -m venv .venv"
    exit 1
fi

# Activar entorno
print_info "Activando entorno virtual..."
source .venv/bin/activate

# Verificar GPU
print_info "Verificando GPUs disponibles..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | nl
    print_success "GPUs detectadas"
else
    print_warning "nvidia-smi no disponible - No se detectaron GPUs NVIDIA"
fi

echo ""
print_header "📥 Opciones de Descarga"
echo ""

echo -e "${BOLD}Selecciona qué descargar:${NC}"
echo ""
echo "1) ⭐ STARTER Pack (Recomendado) - 12GB, 30-40 min"
echo "   • Qwen2.5-14B-AWQ (6GB VRAM) - General, código, math"
echo "   • Mistral-7B-AWQ (3.5GB VRAM) - Ultra-rápido"
echo "   → Puedes cargar AMBOS simultáneamente"
echo ""
echo "2) 💎 PREMIUM Pack - 66GB, 2-3 horas"
echo "   • Llama-3.3-70B-AWQ (14GB VRAM) - Flagship"
echo "   • Qwen2.5-32B-AWQ (10GB VRAM) - Premium"
echo "   • DeepSeek-R1-14B (9GB VRAM) - Chain-of-Thought"
echo "   → Solo 1 a la vez, máxima calidad"
echo ""
echo "3) 🎯 Solo embeddings - 2GB, 10 min"
echo "   • BGE-M3 para RAG"
echo ""
echo "4) ❌ Salir (usar solo APIs)"
echo ""

read -p "Opción [1-4]: " choice

case $choice in
    1)
        CATEGORY="llm_gpu0_starter"
        print_info "Descargando STARTER Pack..."
        ;;
    2)
        CATEGORY="llm_gpu0_advanced"
        print_warning "PREMIUM Pack requiere ~66GB de espacio libre"
        read -p "¿Continuar? [y/N]: " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            print_info "Descarga cancelada"
            exit 0
        fi
        ;;
    3)
        CATEGORY="embeddings"
        print_info "Descargando embeddings..."
        ;;
    4)
        print_info "Puedes usar Jarvis con APIs (OpenAI, Google Gemini)"
        print_info "Ejecuta: python main.py --query 'Tu pregunta'"
        exit 0
        ;;
    *)
        print_error "Opción inválida"
        exit 1
        ;;
esac

# Verificar espacio en disco
FREE_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
print_info "Espacio libre: ${FREE_SPACE}GB"

if [ "$CATEGORY" = "llm_gpu0_advanced" ] && [ "$FREE_SPACE" -lt 70 ]; then
    print_error "No hay suficiente espacio en disco (necesitas ~70GB libres)"
    exit 1
fi

if [ "$CATEGORY" = "llm_gpu0_starter" ] && [ "$FREE_SPACE" -lt 15 ]; then
    print_error "No hay suficiente espacio en disco (necesitas ~15GB libres)"
    exit 1
fi

print_success "Espacio en disco suficiente"

# Verificar token HuggingFace
if [ -z "$HUGGINGFACE_TOKEN" ]; then
    print_warning "Variable HUGGINGFACE_TOKEN no configurada"
    print_info "Cargando desde .env..."
    if [ -f ".env" ]; then
        export $(cat .env | grep HUGGINGFACE_TOKEN | xargs)
    fi
fi

echo ""
print_header "⬇️ Iniciando Descarga"
echo ""

# Descargar
python scripts/download_models.py --category "$CATEGORY"

if [ $? -eq 0 ]; then
    echo ""
    print_header "🎉 Descarga Completada"
    echo ""
    print_success "Modelos descargados correctamente"
    echo ""
    print_info "Ahora puedes usar Jarvis:"
    echo ""
    echo "  # Modo comando único:"
    echo "  python main.py --query '¿Qué es la inteligencia artificial?'"
    echo ""
    echo "  # Modo interactivo:"
    echo "  python main.py"
    echo ""
    echo "  # Ver estadísticas:"
    echo "  python main.py --stats"
    echo ""
else
    print_error "Error durante la descarga"
    exit 1
fi
