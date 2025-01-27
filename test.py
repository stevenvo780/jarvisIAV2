#!/usr/bin/env python3
import os
import logging
import google.generativeai as genai
from typing import Optional, Dict, Any
import platform
import subprocess
import webbrowser

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleModel:
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada en variables de entorno")

        default_config = {
            'model_name': "gemini-2.0-flash-exp",  # Asegúrate de que este modelo esté disponible para tu API Key
            'logging_level': logging.INFO
        }
        self.config = {**default_config, **(config or {})}
        logger.setLevel(self.config['logging_level'])
        genai.configure(api_key=self.api_key)

    def get_response(self, query: str) -> str:
        """
        Envía una consulta al modelo de Google y obtiene la respuesta.
        """
        try:
            model = genai.GenerativeModel(self.config['model_name'])
            # Construir el prompt con instrucciones para el modelo
            prompt = (
                "Eres un asistente que puede realizar acciones en la computadora del usuario. "
                "Si el usuario quiere realizar una acción como 'Abrir calculadora', 'Abrir navegador' o 'Reproducir música', "
                "responde con 'CALL_FUNCTION: nombre_funcion'. Si no, responde normalmente."
                f"\n\nUsuario: {query}"
                "\nAsistente:"
            )
            response = model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            return "No se generó ninguna respuesta."
        except Exception as e:
            logger.error(f"Error en Google API: {str(e)}")
            return f"Error en la llamada a la API: {e}"

# Funciones para ejecutar acciones específicas
def abrir_calculadora():
    print("Abriendo calculadora...")
    try:
        sistema = platform.system()
        if sistema == "Windows":
            subprocess.Popen('calc.exe')
        elif sistema == "Darwin":  # MacOS
            subprocess.Popen(['open', '-a', 'Calculator'])
        elif sistema == "Linux":
            # Intenta abrir gnome-calculator; ajusta si usas otro entorno de escritorio
            subprocess.Popen(['gnome-calculator'])
        else:
            print("Sistema operativo no soportado para abrir la calculadora.")
    except Exception as e:
        print(f"Error al abrir la calculadora: {e}")

def abrir_navegador():
    print("Abriendo navegador...")
    try:
        # Abre el navegador predeterminado con la página de inicio de Google
        webbrowser.open("https://www.google.com")
    except Exception as e:
        print(f"Error al abrir el navegador: {e}")

def reproducir_musica():
    print("Reproduciendo música...")
    try:
        sistema = platform.system()
        if sistema == "Windows":
            subprocess.Popen(['start', 'wmplayer'], shell=True)
        elif sistema == "Darwin":  # MacOS
            subprocess.Popen(['open', '-a', 'Music'])
        elif sistema == "Linux":
            # Intenta abrir Rhythmbox; ajusta si usas otro reproductor
            subprocess.Popen(['rhythmbox'])
        else:
            print("Sistema operativo no soportado para reproducir música.")
    except Exception as e:
        print(f"Error al reproducir música: {e}")

# Mapeo de nombres de funciones en español a funciones de Python
function_mapping = {
    "abrir_calculadora": abrir_calculadora,
    "abrir_navegador": abrir_navegador,
    "reproducir_musica": reproducir_musica,
    # Agrega más mapeos según sea necesario
}

def main():
    google_model = GoogleModel()

    print("Escribe un comando (por ejemplo, 'Abrir calculadora'). Escribe 'quit' para salir.")
    while True:
        user_input = input("\n> ")
        if user_input.lower() in ["quit", "exit"]:
            print("Saliendo.")
            break

        response = google_model.get_response(user_input)
        print(f"Respuesta del modelo: {response}")

        # Lógica para ejecutar funciones basadas en la respuesta del modelo
        if response.startswith("CALL_FUNCTION:"):
            function_name = response.replace("CALL_FUNCTION:", "").strip().lower()
            # Buscar la función en el mapeo
            func = function_mapping.get(function_name)
            if func:
                func()
            else:
                print(f"No se reconoce la función '{function_name}'.")
        else:
            # Respuesta normal del modelo
            print("AI dice:", response)

if __name__ == "__main__":
    main()
