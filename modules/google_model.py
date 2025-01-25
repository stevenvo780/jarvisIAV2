import os
import logging
import google.generativeai as palm
import subprocess


class GoogleModel:
    def __init__(self, api_key=None):
        """
        Inicializa la clase GoogleModel, configurando la clave de API.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("No se encontró GOOGLE_API_KEY en las variables de entorno")

    def get_response(self, query: str) -> str:
        """
        Envía la solicitud al modelo Gemini 2.0 experimental y retorna la respuesta.
        """

        # Configurar la API de PaLM con la clave del entorno:
        palm.configure(api_key=self.api_key)

        try:
            # Realizar la llamada al modelo de Gemini 2.0.
            response = palm.chat(
                model="models/gemini-2.0-experimental",
                messages=[{"role": "user", "content": query}],
                temperature=0.7,
                top_p=0.9
            )

            # Si la respuesta contiene 'last', devuélvela.
            if hasattr(response, 'last') and response.last:
                return response.last
            else:
                return "No se obtuvo una respuesta válida desde Gemini 2.0 experimental."

        except Exception as e:
            logging.error(f"Error en GoogleModel.get_response: {e}")
            return f"Error al procesar la solicitud: {str(e)}"

    def extract_command(self, message: str) -> str:
        """
        Extrae un posible comando de un mensaje usando un formato estándar.
        Por ejemplo, si el modelo responde algo como: 
          'COMANDO: ls -la'
        se devolverá 'ls -la'. Si no se encuentra un formato correspondiente,
        se devuelve una cadena vacía.
        """
        marker = "COMANDO:"
        # Dividir la respuesta para detectar la sección de comando
        if marker in message:
            # Parte posterior al marcador, eliminando espacios en blanco
            return message.split(marker, 1)[1].strip()
        return ""

    def execute_os_command(self, command: str) -> str:
        """
        Ejecuta un comando del OS y retorna su salida.
        En caso de error, retorna una cadena con el mensaje de error.
        """
        if not command:
            return "No se recibió un comando para ejecutar."
        try:
            # Se recomienda usar subprocess.run para mayor control y seguridad
            result = subprocess.run(
                command, 
                shell=True,
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip() if result.stdout else "Comando ejecutado con éxito pero sin salida."
            else:
                return f"Error durante la ejecución del comando:\n{result.stderr}"
        except Exception as e:
            logging.error(f"Error al ejecutar comando: {e}")
            return f"Excepción al ejecutar comando: {str(e)}"

    def get_structured_response(self, query: str) -> dict:
        """
        Envía la solicitud al modelo, detecta si hay un comando
        y retorna un diccionario con la estructura:
        {
            "raw_response": <texto completo>,
            "command_detected": <bool>,
            "command": <string o ''>,
            "command_result": <string o ''>
        }
        """
        # 1. Obtener la respuesta sin procesar
        raw_response = self.get_response(query)

        # 2. Intentar extraer el comando
        extracted_command = self.extract_command(raw_response)
        command_detected = bool(extracted_command)

        command_execution_result = ""
        if command_detected:
            # 3. Ejecutar el comando si se detectó
            command_execution_result = self.execute_os_command(extracted_command)

        # 4. Retornar la estructura con la información
        return {
            "raw_response": raw_response,
            "command_detected": command_detected,
            "command": extracted_command,
            "command_result": command_execution_result
        }