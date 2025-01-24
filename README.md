# Jarvis IA V2

Asistente virtual con capacidades de procesamiento de voz y texto.

## Requisitos Previos

```bash
# Dependencias del sistema
sudo apt-get update
sudo apt-get install -y python3-pip python3-pyaudio libasound2-dev portaudio19-dev

# Dependencias de audio
sudo apt-get install -y alsa-utils pulseaudio python3-pygame

# Dependencias de Python
pip install -r requirements.txt
```

## Configuración

1. Crea un archivo `.env` en la raíz del proyecto:
```
OPENAI_API_KEY=tu_clave_api
GOOGLE_API_KEY=tu_clave_api
```

2. Asegúrate de tener permisos de audio:
```bash
sudo usermod -a -G audio $USER
```

## Configuración del Modelo Local

1. Descarga el modelo más ligero de Llama 2:
```bash
# Crear directorio para modelos
mkdir -p ~/.local/share/jarvis/models
cd ~/.local/share/jarvis/models

# Descargar modelo (necesitas cuenta en HuggingFace)
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
```

2. Requisitos de sistema:
- Mínimo 8GB RAM
- CPU con AVX2 (la mayoría de CPUs desde 2017)
- ~4GB espacio en disco

3. Ajusta los parámetros en `local_model.py` según tu hardware:
- `n_threads`: Número de hilos CPU (default: 4)
- `n_ctx`: Tamaño del contexto (default: 512)
- `n_batch`: Tamaño del batch (default: 512)

## Uso

```bash
python main.py
```

- Di "Hey Jarvis" para activar por voz
- Presiona Enter para modo chat
- En modo chat:
  - "voz on/off": Activa/desactiva respuestas habladas
  - "limpiar": Limpia historial de conversación
  - "salir": Sale del modo chat

## Solución de Problemas

### Audio
- Error "No se encontró micrófono USB":
  - Verifica conexión USB
  - `arecord -l` para listar dispositivos
  - Ajusta `device_index` en VoiceTrigger

### Modelos
- Error de API:
  - Verifica claves en .env
  - Revisa conexión a internet
  - Los logs están en logs/jarvis.log

## Añadir Nuevos Modelos

1. Crea una nueva clase que herede de BaseModel
2. Implementa el método get_response()
3. Registra el modelo en ModelManager
