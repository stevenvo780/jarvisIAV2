# Dockerfile para Jarvis IA V2
FROM nvidia/cuda:12.4.0-base-ubuntu22.04

# Metadata
LABEL maintainer="Jarvis IA Team"
LABEL description="Jarvis AI Assistant con soporte GPU"
LABEL version="2.1.0"

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Instalar Python y dependencias del sistema
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cachear dependencias)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copiar código del proyecto
COPY . .

# Crear directorios necesarios
RUN mkdir -p models vectorstore logs logs/learning

# Exponer puerto
EXPOSE 8090

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

# Comando por defecto
CMD ["python3", "start_web.py", "--host", "0.0.0.0", "--port", "8090"]
