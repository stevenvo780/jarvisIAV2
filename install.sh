#!/bin/bash

echo "Instalando dependencias del sistema..."
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio

echo "Creando entorno virtual..."
python -m venv jarvis

echo "Activando entorno virtual..."
source jarvis/bin/activate

echo "Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Verificando instalación..."
python -c "import pyaudio; print('PyAudio OK')"
python -c "import speech_recognition; print('SpeechRecognition OK')"

echo "Instalación completada."
