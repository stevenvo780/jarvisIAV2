import threading
import sys
import logging
import os
from queue import Queue
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

class TextHandler:
    def __init__(self, terminal_manager, input_queue, tts=None, state=None):
        self.terminal = terminal_manager
        self.input_queue = input_queue
        self.running = True
        self.tts = tts
        self.state = state or {'running': True, 'voice_active': False}
        self.commands = ['exit', 'salir', 'quit', 'voz on', 'voz off', 'help', 'clear']
        self.session = PromptSession()
        self.style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'command': '#884444',
            'username': '#884444 italic'
        })
        
    def start(self):
        """Inicia el manejador de texto en un hilo separado"""
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()

    def stop(self):
        """Detiene el manejador de texto"""
        self.running = False
        if hasattr(self, 'input_thread'):
            self.input_thread.join(timeout=1)

    def _get_formatted_prompt(self):
        """Genera un prompt formateado"""
        voice_status = "🎤" if self.state.get('voice_active', False) else "⌨️"
        return HTML(f"<username>{voice_status}</username> <prompt>></prompt> ")

    def _input_loop(self):
        """Bucle principal de entrada de texto mejorado"""
        while self.running:
            try:
                # Usar prompt_toolkit para entrada mejorada
                text = self.session.prompt(
                    self._get_formatted_prompt(),
                    style=self.style,
                    enable_history=True,
                    complete_while_typing=True,
                    mouse_support=True
                ).strip()

                if text:
                    self._process_input(text)
                    
            except KeyboardInterrupt:
                continue
            except EOFError:
                self.running = False
                break
            except Exception as e:
                logging.error(f"Error en entrada de texto: {e}")
                continue

    def _process_input(self, text: str):
        """Procesa el texto ingresado con mejor manejo de comandos"""
        # Eliminar caracteres ^M
        text = text.replace('\r', '').replace('\n', '')
        text = text.strip()
        if not text:
            return

        try:
            text_lower = text.lower().strip()
            
            # Comandos del sistema
            if text_lower in ['exit', 'salir', 'quit']:
                self.state['running'] = False
                self.terminal.print_success("\nSaliendo del sistema...")
                return
                
            if text_lower == 'clear':
                clear()
                return
                
            if text_lower == 'voz off':
                self.state['voice_active'] = False
                self.terminal.print_success("Modo voz desactivado")
                return
                
            if text_lower == 'voz on':
                self.state['voice_active'] = True
                self.terminal.print_success("Modo voz activado")
                return

            if text_lower == 'help':
                self._show_help()
                return

            # Enviar a la cola solo si es un texto válido
            if text_lower:
                self.input_queue.put(('keyboard', text))
                
        except Exception as e:
            logging.error(f"Error procesando entrada: {str(e)}")
            self.terminal.print_error(f"Error: {str(e)}")

    def _show_help(self):
        """Muestra ayuda de comandos disponibles"""
        help_text = """
Comandos disponibles:
  - exit, salir, quit : Salir del sistema
  - clear            : Limpiar pantalla
  - voz on/off      : Activar/desactivar modo voz
  - help            : Mostrar esta ayuda
"""
        print(help_text)
