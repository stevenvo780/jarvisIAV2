# Instalación de Jarvis IA V2

## Requisitos del Sistema

- Python 3.10+
- pip
- Dispositivos de audio (micrófono/altavoces)
- 8GB RAM mínimo

## Dependencias del Sistema

### Ubuntu/Debian

1. Instalar dependencias del sistema:
```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio
```

2. Instalar usando el script:
```bash
chmod +x install.sh
./install.sh
```

## Instalación Manual

Si prefieres instalar manualmente:

```bash
# Crear entorno virtual
python -m venv jarvis
source jarvis/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

## Windows

1. Crear y activar entorno virtual:
```bash
python -m venv jarvis
jarvis\Scripts\activate
```

2. Instalar PyAudio:
   - Opción 1: `pip install pyaudio`
   - Opción 2: Descargar wheel desde https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

3. Instalar resto de dependencias:
```bash
pip install -r requirements.txt
```

## Verificación

Ejecuta estos comandos para verificar la instalación:
```bash
python -c "import pyaudio; print('PyAudio OK')"
python -c "import speech_recognition; print('SpeechRecognition OK')"
```

## Solución de Problemas

Si hay problemas con PyAudio:
```bash
# Desinstalar PyAudio si está instalado
pip uninstall pyaudio

# Instalar dependencias del sistema
sudo apt-get install -y python3.10-dev portaudio19-dev python3-pyaudio

# Reinstalar PyAudio
pip install PyAudio==0.2.14
```
