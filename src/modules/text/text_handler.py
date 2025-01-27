import threading
import sys
import logging
from queue import Queue
import time
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout
from modules.command_manager import CommandManager

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
        self.command_manager = CommandManager(tts=tts, state=self.state)

    def stop(self):
        self.running = False

    def run_interactive(self):
        print("\nJarvis Text Interface - Escribe 'help' para ver los comandos")
        
        with patch_stdout():
            while self.running and self.state.get('running', True):
                try:
                    time.sleep(0.05)
                    
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
        icon = "🟢"  # Cambiado de usar 🎤/⌨️ a usar siempre 🟢
        return HTML(f"{icon} > ")

    def _process_input(self, text: str):
        if not text or text.isspace():
            self.terminal.print_warning("Comando vacío. Intenta de nuevo.")
            return

            
        text = text.strip()
        text_lower = text.lower()
        
        # System commands
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

        self.input_queue.put(('text', text))

    def _show_help(self):
        help_text = """
            Available commands:
            - exit, salir, quit : Exit the system
            - clear             : Clear the screen
            - voz on/off       : Enable/disable voice mode
            - help             : Show this help
            """
        print(help_text)
    
    def stop(self):
        self.running = False
        self.state['running'] = False
