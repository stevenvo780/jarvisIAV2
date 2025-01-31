import logging
import time
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout

class TextHandler:
    def __init__(
        self,
        terminal_manager,
        input_queue,
        actions
        ):
        self.terminal = terminal_manager
        self.input_queue = input_queue
        self.actions = actions
        self.running = True
        self.session = PromptSession()
        self.style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'command': '#884444',
            'username': '#884444 italic'
        })

    def run_interactive(self):
        with patch_stdout():
            while self.running:
                try:
                    time.sleep(0.05)
                    user_input = self.session.prompt(
                        self._get_formatted_prompt(),
                        style=self.style
                    ).strip()

                    if user_input:
                        self._handle_input(user_input)
                        
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
                except Exception as e:
                    logging.error(f"Error de entrada: {e}")
                    continue

    def _get_formatted_prompt(self):
        icon = "🟢"
        return HTML(f"{icon} > ")

    def _handle_input(self, text: str):
        if not text or text.isspace():
            self.terminal.print_warning("Comando vacío. Intenta de nuevo.")
            return

        self.input_queue.put(('text', text))
        
    def stop(self):
        self.running = False
