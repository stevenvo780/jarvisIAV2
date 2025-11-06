#!/bin/bash
# install_upgrade.sh - Jarvis IA V2 Upgrade Installation
# Este script instala todas las dependencias necesarias para la actualización

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                 Jarvis IA V2 - Upgrade Installation            ║"
echo "║                    Multi-GPU Deep Learning Assistant            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Función para mensajes de éxito
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Función para mensajes de advertencia
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Función para mensajes de error
error() {
    echo -e "${RED}❌ $1${NC}"
}

# Función para mensajes de información
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verificar NVIDIA drivers
echo ""
info "Verificando drivers NVIDIA..."
if ! command -v nvidia-smi &> /dev/null; then
    error "nvidia-smi no encontrado. Instala los drivers NVIDIA primero."
    exit 1
fi

echo ""
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo ""
success "Drivers NVIDIA detectados correctamente"

# Verificar CUDA
echo ""
info "Verificando CUDA..."
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $5}' | cut -c2-)
    success "CUDA $CUDA_VERSION detectado"
else
    warning "nvcc no encontrado. Asegúrate de tener CUDA Toolkit instalado."
    warning "Descarga desde: https://developer.nvidia.com/cuda-downloads"
fi

# Verificar Python
echo ""
info "Verificando Python..."
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
if [[ $(echo "$PYTHON_VERSION 3.10" | awk '{print ($1 >= $2)}') -eq 1 ]]; then
    success "Python $PYTHON_VERSION detectado"
else
    error "Python 3.10+ requerido. Versión actual: $PYTHON_VERSION"
    exit 1
fi

# Crear entorno virtual
echo ""
info "Creando entorno virtual..."
if [ -d "venv_v2" ]; then
    warning "El entorno virtual 'venv_v2' ya existe."
    read -p "¿Deseas recrearlo? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf venv_v2
        python3 -m venv venv_v2
        success "Entorno virtual recreado"
    else
        info "Usando entorno existente"
    fi
else
    python3 -m venv venv_v2
    success "Entorno virtual creado"
fi

# Activar entorno virtual
source venv_v2/bin/activate
success "Entorno virtual activado"

# Actualizar pip
echo ""
info "Actualizando pip, setuptools y wheel..."
pip install --upgrade pip setuptools wheel -q
success "Herramientas base actualizadas"

# Instalar PyTorch con CUDA 12.4
echo ""
info "Instalando PyTorch con CUDA 12.4..."
echo "Esto puede tomar varios minutos..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
success "PyTorch instalado"

# Verificar PyTorch + CUDA
echo ""
info "Verificando instalación de PyTorch..."
python3 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'Dispositivos CUDA: {torch.cuda.device_count()}')"
success "PyTorch configurado correctamente"

# Instalar dependencias del sistema para Flash Attention
echo ""
info "Verificando dependencias para Flash Attention..."
if ! command -v ninja &> /dev/null; then
    warning "Ninja build no encontrado. Instalando..."
    sudo apt-get update -qq
    sudo apt-get install -y ninja-build
fi
success "Dependencias del sistema verificadas"

# Instalar Flash Attention
echo ""
info "Instalando Flash Attention (puede tomar 10-15 minutos)..."
warning "Este paso requiere compilación desde fuente..."
MAX_JOBS=4 pip install flash-attn --no-build-isolation || {
    warning "Flash Attention falló. Continuando sin ella..."
    warning "Puedes instalarla manualmente después: pip install flash-attn --no-build-isolation"
}

# Instalar vLLM
echo ""
info "Instalando vLLM para inferencia optimizada..."
pip install vllm
success "vLLM instalado"

# Instalar llama-cpp-python con CUDA
echo ""
info "Instalando llama-cpp-python con soporte CUDA..."
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python[server] || {
    warning "llama-cpp-python con CUDA falló. Instalando versión CPU..."
    pip install llama-cpp-python[server]
}

# Instalar CTranslate2 para Whisper
echo ""
info "Instalando CTranslate2 para Whisper optimizado..."
pip install ctranslate2
success "CTranslate2 instalado"

# Instalar dependencias restantes
echo ""
info "Instalando dependencias restantes desde requirements_v2.txt..."
pip install -r requirements_v2.txt
success "Todas las dependencias instaladas"

# Instalar dependencias de audio del sistema
echo ""
info "Verificando dependencias de audio del sistema..."
sudo apt-get update -qq
sudo apt-get install -y portaudio19-dev python3-pyaudio alsa-utils pulseaudio
success "Dependencias de audio instaladas"

# Crear estructura de directorios
echo ""
info "Creando estructura de directorios..."
mkdir -p models/llm
mkdir -p models/whisper
mkdir -p models/embeddings
mkdir -p vectorstore/chromadb
mkdir -p cache/model_cache
mkdir -p logs
mkdir -p artifacts
success "Estructura de directorios creada"

# Resumen final
echo ""
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  Instalación Completada                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
success "Instalación completada exitosamente!"
echo ""
info "Próximos pasos:"
echo "  1. Activa el entorno: source venv_v2/bin/activate"
echo "  2. Descarga los modelos: python scripts/download_models.py"
echo "  3. Lee UPGRADE_PLAN.md para la guía completa"
echo ""
warning "IMPORTANTE: Algunos modelos pueden requerir autenticación en HuggingFace"
info "Ejecuta: huggingface-cli login"
echo ""
success "¡Jarvis está listo para la actualización!"
echo ""
