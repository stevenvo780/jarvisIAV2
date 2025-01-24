import speech_recognition as sr

class VoiceTrigger:
    def __init__(self, wake_word="Hey Jarvis", language="es-ES"):
        self.wake_word = wake_word.lower()
        self.language = language
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
        except OSError:
            self.microphone = None

    def listen_for_activation(self):
        # Lógica para detectar la frase de activación
        return True  # Ejemplo

    def capture_query(self):
        # Lógica para capturar la consulta del usuario
        return "Tu pregunta aquí"