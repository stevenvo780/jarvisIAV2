import threading
import sys
import logging
import os
from queue import Queue

class TextHandler:
    def __init__(self, terminal_manager, input_queue):
        self.terminal = terminal_manager
        self.input_queue = input_queue
        self.running = True
        self.commands = ['exit', 'salir', 'quit', 'voz on', 'voz off', 'help']
        
    def start(self):
        """Inicia el manejador de texto en un hilo separado"""
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()

    def stop(self):
        """Detiene el manejador de texto"""
        self.running = False
        if hasattr(self, 'input_thread'):
            self.input_thread.join(timeout=1)

    def _input_loop(self):
        """Bucle principal de entrada de texto"""
        # Configurar modo raw del terminal
        try:
            import termios
            import tty
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except ImportError:
            old_settings = None

        try:
            while self.running:
                try:
                    # Obtener entrada limpia
                    line = self._get_clean_input()
                    if line:
                        self._process_input(line.strip())
                except (EOFError, KeyboardInterrupt):
                    self.running = False
                except Exception as e:
                    logging.error(f"Error en entrada de texto: {e}")
                    continue

        finally:
            # Restaurar configuración original del terminal
            if old_settings is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def _get_clean_input(self) -> str:
        """Obtiene entrada limpia del usuario manejando caracteres especiales"""
        buffer = []
        prompt = self.terminal.get_prompt()
        sys.stdout.write(prompt)
        sys.stdout.flush()

        while self.running:
            char = sys.stdin.read(1)
            
            # Manejar tecla Enter
            if char in ['\n', '\r']:
                sys.stdout.write('\n')
                sys.stdout.flush()
                return ''.join(buffer)
            
            # Manejar backspace
            elif char == '\x7f':  # backspace
                if buffer:
                    buffer.pop()
                    sys.stdout.write('\b \b')  # Borrar último carácter
                    sys.stdout.flush()
            
            # Ignorar caracteres de control excepto los manejados
            elif ord(char) < 32:
                continue
            
            # Caracteres normales
            else:
                buffer.append(char)
                sys.stdout.write(char)
                sys.stdout.flush()

    def _process_input(self, text: str):
        """Procesa el texto ingresado"""
        if text:
            self.terminal.clear_display()
            self.input_queue.put(('keyboard', text))
