import os
import logging
import google.generativeai as palm

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
            # Ajusta "model" y otros parámetros según sea necesario.
            response = palm.chat(
                model="models/gemini-2.0-experimental",
                messages=[{"role": "user", "content": query}],
                temperature=0.7,
                top_p=0.9
            )

            # Si la respuesta contiene 'last', devuélvela. De lo contrario, 
            # maneja la situación de no tener un resultado válido.
            if hasattr(response, 'last') and response.last:
                return response.last
            else:
                return "No se obtuvo una respuesta válida desde Gemini 2.0 experimental."

        except Exception as e:
            logging.error(f"Error en GoogleModel.get_response: {e}")
            return f"Error al procesar la solicitud: {str(e)}"