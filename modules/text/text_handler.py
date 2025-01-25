import threading
import sys
import logging
from queue import Queue
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout

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

    def run_interactive(self):
        """Ejecuta el bucle de entrada de texto en el hilo principal."""
        print("\nJarvis Text Interface - Escribe 'help' para ver los comandos")
        
        while self.running and self.state.get('running', True):
            try:
                user_input = self.session.prompt(
                    self._get_formatted_prompt(),
                    style=self.style
                ).strip()

                if user_input:
                    self._process_input(user_input)
                    
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                logging.error(f"Error de entrada: {e}")
                continue

    def _get_formatted_prompt(self):
        """Genera un prompt formateado."""
        icon = "🎤" if self.state.get('voice_active', False) else "⌨️"
        return HTML(f"{icon} <prompt>></prompt> ")

    def _process_input(self, text: str):
        """Process user text commands or forward them to Jarvis."""
        if not text or text.isspace():
            return
            
        text = text.strip()
        text_lower = text.lower()
        
        # System commands con feedback mejorado
        if text_lower in ['exit', 'salir', 'quit']:
            self.state['running'] = False
            self.terminal.print_success("👋 Saliendo del sistema...")
            return
                
        if text_lower == 'clear':
            clear()
            print("🧹 Pantalla limpiada")
            return
                
        if text_lower == 'voz off':
            self.state['voice_active'] = False
            self.terminal.print_success("🔇 Modo voz desactivado")
            return
                
        if text_lower == 'voz on':
            self.state['voice_active'] = True
            self.terminal.print_success("🔊 Modo voz activado")
            return

        if text_lower == 'help':
            self._show_help()
            return

        # Input normal al sistema
        self.input_queue.put(('keyboard', text))

    def _show_help(self):
        """Shows help commands."""
        help_text = """
Available commands:
  - exit, salir, quit : Exit the system
  - clear             : Clear the screen
  - voz on/off        : Enable/disable voice mode
  - help              : Show this help
"""
        print(help_text)
    
    def stop(self):
        """Stops the text handler gracefully."""
        self.running = False
        self.state['running'] = False
