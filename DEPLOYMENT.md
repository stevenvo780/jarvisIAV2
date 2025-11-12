# 🚀 GUÍA DE DEPLOYMENT - JARVIS IA V2

**Versión**: 2.1.0
**Fecha**: 2025-11-12
**Estado**: Production Ready

---

## 📋 MÉTODOS DE DEPLOYMENT

1. [Desarrollo Local](#desarrollo-local) - Más rápido
2. [Docker Compose](#docker-compose) - Recomendado para producción
3. [Docker Manual](#docker-manual) - Control avanzado
4. [Bare Metal](#bare-metal) - Máximo rendimiento

---

## 🔧 PREREQUISITOS

### **Hardware Mínimo**
- GPU: NVIDIA con 8GB+ VRAM (16GB recomendado)
- RAM: 16GB+ (32GB recomendado)
- Disco: 50GB+ libre (para modelos)
- CPU: 4+ cores

### **Software**
- Ubuntu 22.04+ / Debian 11+
- Python 3.10+
- CUDA 12.4+
- Docker + Docker Compose (para deployment con Docker)
- nvidia-docker2 (para GPU en Docker)

---

## 1️⃣ DESARROLLO LOCAL

### **Instalación Rápida**

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd jarvisIAV2

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 5. Iniciar servidor
python3 start_web.py
```

### **Acceder**
```
http://localhost:8090
```

### **Comandos Útiles**

```bash
# Con debug
python3 start_web.py --debug

# Puerto custom
python3 start_web.py --port 8080

# Con auto-cleanup GPU
export JARVIS_AUTO_CLEANUP_GPU=1
python3 start_web.py
```

---

## 2️⃣ DOCKER COMPOSE (Recomendado)

### **Instalación**

```bash
# 1. Asegúrate de tener Docker y nvidia-docker
sudo apt-get install docker.io docker-compose
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 2. Configurar .env
cp .env.example .env
# Editar .env con tus configuraciones

# 3. Construir imagen
docker-compose build

# 4. Iniciar servicio
docker-compose up -d
```

### **Verificar Estado**

```bash
# Ver logs
docker-compose logs -f jarvis-web

# Ver estado
docker-compose ps

# Health check
curl http://localhost:8090/health
```

### **Comandos Útiles**

```bash
# Detener
docker-compose down

# Reiniciar
docker-compose restart

# Reconstruir imagen
docker-compose build --no-cache

# Ver logs de un servicio específico
docker-compose logs -f jarvis-web

# Ejecutar comando dentro del container
docker-compose exec jarvis-web bash
```

### **Configuración Avanzada**

Editar `docker-compose.yml`:

```yaml
services:
  jarvis-web:
    environment:
      # Activar API keys
      - JARVIS_API_KEYS=secret-key-1,secret-key-2

      # Configurar CORS
      - JARVIS_ALLOWED_ORIGIN=https://tu-dominio.com

      # Debug mode
      - JARVIS_DEBUG=1

    # Cambiar puerto
    ports:
      - "8080:8090"

    # Límites de recursos
    deploy:
      resources:
        limits:
          memory: 32G
          cpus: '8'
```

---

## 3️⃣ DOCKER MANUAL

### **Build**

```bash
# Construir imagen
docker build -t jarvis-ia:2.1.0 .

# Con cache disabled
docker build --no-cache -t jarvis-ia:2.1.0 .
```

### **Run**

```bash
docker run -d \
  --name jarvis-web \
  --gpus all \
  -p 8090:8090 \
  -v $(pwd)/models:/app/models:ro \
  -v $(pwd)/vectorstore:/app/vectorstore \
  -v $(pwd)/logs:/app/logs \
  -e CUDA_VISIBLE_DEVICES=0 \
  -e JARVIS_AUTO_CLEANUP_GPU=1 \
  jarvis-ia:2.1.0
```

### **Con API Keys**

```bash
docker run -d \
  --name jarvis-web \
  --gpus all \
  -p 8090:8090 \
  -v $(pwd)/models:/app/models:ro \
  -v $(pwd)/vectorstore:/app/vectorstore \
  -e JARVIS_API_KEYS="secret-key-1,secret-key-2" \
  jarvis-ia:2.1.0
```

---

## 4️⃣ BARE METAL (Producción)

### **Setup Completo**

```bash
# 1. Usuario dedicado
sudo useradd -m -s /bin/bash jarvis
sudo usermod -aG video jarvis  # Para acceso GPU

# 2. Instalar en directorio dedicado
sudo mkdir /opt/jarvis
sudo chown jarvis:jarvis /opt/jarvis
cd /opt/jarvis

# 3. Clonar e instalar
git clone <repo-url> .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configurar systemd service
sudo cp deployment/jarvis-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jarvis-web
sudo systemctl start jarvis-web
```

### **Systemd Service**

Crear `/etc/systemd/system/jarvis-web.service`:

```ini
[Unit]
Description=Jarvis IA Web Interface
After=network.target

[Service]
Type=simple
User=jarvis
Group=jarvis
WorkingDirectory=/opt/jarvis
Environment="PATH=/opt/jarvis/venv/bin"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="JARVIS_AUTO_CLEANUP_GPU=1"
ExecStart=/opt/jarvis/venv/bin/python3 /opt/jarvis/start_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### **Comandos Systemd**

```bash
# Iniciar
sudo systemctl start jarvis-web

# Detener
sudo systemctl stop jarvis-web

# Reiniciar
sudo systemctl restart jarvis-web

# Ver estado
sudo systemctl status jarvis-web

# Ver logs
sudo journalctl -u jarvis-web -f
```

---

## 🔒 SEGURIDAD EN PRODUCCIÓN

### **1. API Keys**

```bash
# Generar API key seguro
openssl rand -hex 32

# Configurar en .env
JARVIS_API_KEYS=abc123...,def456...
```

Usar en requests:
```bash
curl -H "X-Api-Key: abc123..." http://localhost:8090/api/chat
```

### **2. HTTPS con Nginx**

```nginx
# /etc/nginx/sites-available/jarvis
server {
    listen 443 ssl http2;
    server_name jarvis.tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Para SSE streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        chunked_transfer_encoding off;
    }
}
```

### **3. Firewall**

```bash
# Permitir solo SSH y HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# No exponer puerto 8090 directamente
# (usar proxy reverso)
```

### **4. Rate Limiting**

Ya incluido en la aplicación (10 req/min si slowapi instalado).

Para configurar:
```bash
# .env
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_PERIOD=minute
```

---

## 📊 MONITORING

### **Health Checks**

```bash
# Simple
curl http://localhost:8090/health

# Detallado (requiere API key si configurado)
curl -H "X-Api-Key: your-key" http://localhost:8090/api/status
```

### **Logs**

```bash
# Docker Compose
docker-compose logs -f --tail=100 jarvis-web

# Bare Metal
tail -f logs/jarvis.log

# Systemd
sudo journalctl -u jarvis-web -f
```

### **Métricas**

Ver `logs/learning/stats.json` para estadísticas de uso.

---

## 🧪 TESTING POST-DEPLOYMENT

```bash
# 1. Health check
curl http://localhost:8090/health
# Esperado: {"status":"ok",...}

# 2. API Status
curl http://localhost:8090/api/status
# Esperado: {"status":"ready","models_loaded":1,...}

# 3. Chat (sin API key)
curl -X POST http://localhost:8090/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hola"}'

# 4. Chat (con API key)
curl -X POST http://localhost:8090/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: your-key" \
  -d '{"message":"Hola"}'

# 5. Streaming SSE (navegador)
# Abrir: http://localhost:8090
```

---

## 🐛 TROUBLESHOOTING

### **GPU no detectada**

```bash
# Verificar CUDA
nvidia-smi

# Verificar en Docker
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Verificar variable
echo $CUDA_VISIBLE_DEVICES
```

### **Modelo no carga**

```bash
# Ver logs
docker-compose logs jarvis-web | grep "model"

# Verificar rutas
ls -lh models/

# Limpiar procesos vLLM
export JARVIS_AUTO_CLEANUP_GPU=1
# O manualmente:
pkill -9 -f vllm
```

### **Puerto ya en uso**

```bash
# Buscar proceso
sudo lsof -i :8090

# Matar proceso
sudo kill -9 <PID>

# O cambiar puerto
python3 start_web.py --port 8091
```

### **Permisos**

```bash
# Dar permisos a usuario jarvis
sudo chown -R jarvis:jarvis /opt/jarvis

# GPU access
sudo usermod -aG video jarvis
sudo usermod -aG render jarvis
```

---

## 📦 BACKUP Y RESTORE

### **Backup**

```bash
# Vectorstore (importante)
tar -czf vectorstore-backup-$(date +%Y%m%d).tar.gz vectorstore/

# Logs y configuración
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env logs/ src/config/
```

### **Restore**

```bash
# Vectorstore
tar -xzf vectorstore-backup-20251112.tar.gz

# Configuración
tar -xzf config-backup-20251112.tar.gz
```

---

## 🔄 UPDATES

### **Actualizar Código**

```bash
# Development
git pull origin master
pip install -r requirements.txt --upgrade
python3 start_web.py

# Docker Compose
git pull origin master
docker-compose build
docker-compose up -d

# Systemd
cd /opt/jarvis
git pull origin master
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart jarvis-web
```

---

## 📞 SOPORTE

- **Logs**: `logs/jarvis.log`, `logs/errors.log`
- **Issues**: Ver `MEJORAS_IMPLEMENTADAS.md`
- **Tests**: `pytest tests/test_web_api.py -v`

---

**¡Deployment exitoso! 🚀**

Accede a tu Jarvis en: **http://localhost:8090**
