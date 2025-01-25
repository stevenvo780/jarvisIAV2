import webbrowser
import speech_recognition as sr
from time import sleep
import pyaudio
import os
import sys
import warnings
from contextlib import contextmanager
import ctypes

# Silenciar mensajes de error de ALSA
ctypes.CDLL('libasound.so').snd_lib_error_set_handler(None)

# Redirigir stderr a /dev/null para suprimir mensajes de JACK
@contextmanager
def suppress_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# Ignorar advertencias
warnings.filterwarnings("ignore")

def listar_dispositivos():
    with suppress_stderr():
        p = pyaudio.PyAudio()
        info = "\nDispositivos de audio disponibles:\n"
        for i in range(p.get_device_count()):
            info += f"Dispositivo {i}: {p.get_device_info_by_index(i)['name']}\n"
        p.terminate()
        print(info)

def configurar_microfono():
    r = sr.Recognizer()
    # Ajustar parámetros para mejor reconocimiento
    r.energy_threshold = 4000
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.5
    return r

def escuchar_microfono(recognizer, microfono):
    try:
        with microfono as source:
            print('Ajustando al ruido ambiente... Espere')
            # Aumentar la duración del ajuste de ruido
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print('Hola, soy tu asistente por voz: ')
            # Aumentar timeout para mejor captura
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
        return audio
    except sr.WaitTimeoutError:
        print("Tiempo de espera agotado")
        return None
    except Exception as e:
        print(f"Error al escuchar: {str(e)}")
        return None

def main():
    try:
        with suppress_stderr():
            # Mostrar dispositivos disponibles al inicio
            listar_dispositivos()
            
            # Intentar usar un dispositivo específico si hay problemas
            mic = sr.Microphone(device_index=6)  # None usa el dispositivo por defecto
            r = configurar_microfono()
            
            while True:
                try:
                    audio = escuchar_microfono(r, mic)
                    if audio:
                        try:
                            text = r.recognize_google(audio, language='es-ES')
                            print('Has dicho: {}'.format(text))
                            
                            if "amazon" in text.lower():
                                webbrowser.open('http://amazon.es')
                            elif "noticias" in text.lower():
                                webbrowser.open('http://noticiasfinancieras.info')
                            elif "que tal" in text.lower():
                                print("Bien y tu?")
                            elif "salir" in text.lower():
                                print("Hasta luego!")
                                break
                                
                        except sr.UnknownValueError:
                            print("No pude entender el audio")
                        except sr.RequestError as e:
                            print(f"Error en la petición a Google Speech Recognition; {str(e)}")
                    
                    sleep(0.5)  # Pequeña pausa para evitar sobrecarga de CPU
                    
                except KeyboardInterrupt:
                    print("\nPrograma terminado por el usuario")
                    break
                except Exception as e:
                    print(f"Error inesperado: {str(e)}")
                    continue

    except KeyboardInterrupt:
        print("\nPrograma terminado por el usuario")
    except Exception as e:
        print(f"Error crítico: {str(e)}")

if __name__ == "__main__":
    with suppress_stderr():
        main()