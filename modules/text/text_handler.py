import threading
import sys
import logging
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
        """Starts the text handler on a separate thread."""
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()

    def stop(self):
        """Stops text input loop."""
        self.running = False
        if hasattr(self, 'input_thread'):
            self.input_thread.join(timeout=1)

    def _get_formatted_prompt(self):
        """Generates a formatted prompt string."""
        voice_status = "🎤" if self.state.get('voice_active', False) else "⌨️"
        return HTML(f"<username>{voice_status}</username> <prompt>></prompt> ")

    def _input_loop(self):
        """Main loop for reading user text input with prompt_toolkit."""
        while self.running and self.state.get('running', True):
            try:
                user_input = self.session.prompt(
                    self._get_formatted_prompt(),
                    style=self.style,
                    enable_history=True,
                    mouse_support=False
                ).strip()

                if user_input:
                    self._process_input(user_input)
                    
            except KeyboardInterrupt:
                # If user presses Ctrl+C, ignore and continue
                continue
            except EOFError:
                # If user presses Ctrl+D, we exit
                self.running = False
                break
            except Exception as e:
                logging.error(f"Text input error: {e}")
                continue

    def _process_input(self, text: str):
        """Process user text commands or forward them to Jarvis."""
        # Remove \r or \n to avoid extra carriage returns
        text = text.replace('\r', '').replace('\n', '').strip()
        if not text:
            return

        text_lower = text.lower()
        
        # System commands
        if text_lower in ['exit', 'salir', 'quit']:
            self.state['running'] = False
            self.terminal.print_success("\nExiting system...")
            return
                
        if text_lower == 'clear':
            clear()
            return
                
        if text_lower == 'voz off':
            self.state['voice_active'] = False
            self.terminal.print_success("Voice mode disabled")
            return
                
        if text_lower == 'voz on':
            self.state['voice_active'] = True
            self.terminal.print_success("Voice mode enabled")
            return

        if text_lower == 'help':
            self._show_help()
            return

        # Otherwise, send text to the queue
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
