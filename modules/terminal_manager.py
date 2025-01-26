import sys
import os
import logging
import time
import threading
from typing import Optional, List, Tuple
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style

class TerminalManager:
    def __init__(self):
        self._setup_colors()
        self._setup_states()
        self.setup_logging()
        self.style = Style.from_dict({
            'header': '#00aa00 bold',
            'success': '#00aa00',
            'warning': '#aaaa00',
            'error': '#aa0000',
            'info': '#0000aa',
            'thinking': '#aa00aa',
            'response_google': '#4285F4',
            'response_openai': '#10a37f',
            'response_local': '#FF6B6B',
            'response_default': '#00aaaa',
            'voice_detected': '#00ff00 bold',
            'listening': '#4169E1',
            'processing': '#FFA500'
        })
        self.current_state = "🎤"
        self._prompt_lock = threading.Lock()
        self._last_state = None
        self._last_time = 0.0
        self._last_prompt = None

    def _setup_colors(self):
        self.COLORS = {
            'GREEN': '\033[92m',
            'RED': '\033[91m',
            'BLUE': '\033[94m',
            'CYAN': '\033[96m',
            'YELLOW': '\033[93m',
            'RESET': '\033[0m',
            'BOLD': '\033[1m'
        }

    def _setup_states(self):
        self.STATES = {
            'LISTENING': "👂",
            'PROCESSING': "⚡",
            'THINKING': "💭",
            'SPEAKING': "🗣️",
            'ERROR': "❌",
            'IDLE': "🟢",  # Cambiado de ⌨️ a 🟢
            'VOICE_IDLE': "🟢",  # Cambiado de 🎤 a 🟢
            'CHAT': "💬"
        }

    def setup_logging(self):
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            filename="logs/jarvis.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )
        for lib in ['alsa', 'jack', 'pulse', 'libav']:
            logging.getLogger(lib).setLevel(logging.CRITICAL)
            logging.getLogger(lib).propagate = False

    def print_error(self, message: str):
        print_formatted_text(HTML(f"✗ <error>{message}</error>"), style=self.style)

    def print_success(self, message: str):
        print_formatted_text(HTML(f"✓ <success>{message}</success>"), style=self.style)

    def print_warning(self, message: str):
        print_formatted_text(HTML(f"⚠ <warning>{message}</warning>"), style=self.style)

    def print_header(self, message: str):
        print_formatted_text(HTML(f"\n=== <header>{message}</header> ===\n"), style=self.style)

    def print_status(self, message: str):
        print_formatted_text(HTML(f"<info>[STATUS]</info> {message}"), style=self.style)

    def print_goodbye(self):
        print_formatted_text(HTML("\n<header>Goodbye!</header>\n"), style=self.style)

    def print_thinking(self):
        print_formatted_text(HTML("<thinking>Thinking...</thinking>"), style=self.style)

    def print_response(self, message: str, model_name: str = None):
        style_key = f'response_{model_name.lower()}' if model_name else 'response_default'
        if style_key not in self.style.style_rules:
            style_key = 'response_default'
            
        prefix = f"[{model_name.upper()}] " if model_name else ""
        
        lines = message.split('\n')
        for line in lines:
            print_formatted_text(
                HTML(f"<{style_key}>{prefix}{line}</{style_key}>"), 
                style=self.style
            )
        sys.stdout.flush()

    def update_prompt_state(self, state: str, message: str = ""):
        with self._prompt_lock:
            now = time.time()
            new_prompt = None
            
            # Evitar actualizaciones muy frecuentes del mismo estado
            if state == self._last_state and (now - self._last_time < 0.5):
                return
                
            self._last_state = state
            self._last_time = now
            state_icon = self.STATES.get(state, "🟢")
            
            # Determinar el nuevo prompt
            if state in ['LISTENING', 'PROCESSING', 'THINKING']:
                new_prompt = f"{state_icon}"
            elif message and state == 'ERROR':
                new_prompt = f"{state_icon} {message}"
            else:
                new_prompt = f"{state_icon} > "
            
            # Solo actualizar si el prompt es diferente
            if new_prompt != self._last_prompt:
                print("\r" + " " * 100 + "\r", end="", flush=True)
                print(new_prompt, end="", flush=True)
                self._last_prompt = new_prompt

    def print_user_input(self, text: str):
        print_formatted_text(
            HTML(f"<command>USR> {text}</command>"), 
            style=self.style
        )

    def print_voice_detected(self, text: str):
        with self._prompt_lock:
            print("\r" + " " * 100 + "\r", end="", flush=True)
            print(f"🎤 {text}")
            self._last_prompt = "🟢 > "
            print(self._last_prompt, end="", flush=True)
