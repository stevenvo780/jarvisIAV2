import os
import logging
import time
import threading
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import ANSI

class TerminalManager:
    GREEN = '\033[32m'
    RED = '\033[31m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    YELLOW = '\033[33m'
    MAGENTA = '\033[35m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CLEAR_LINE = '\r\033[K'

    AGENT_EMOJIS = {
        'google': '🔍',
        'openai': '🤖',
        'local': '🏠',
        'system': '⚙️',
        'error': '🚨',
        'voice': '🎙️'
    }

    STATES = {
        'LISTENING': {'icon': "👂"},
        'PROCESSING': {'icon': "⚡"},
        'THINKING': {'icon': "💭"},
        'SPEAKING': {'icon': "🗣️"},
        'ERROR': {'icon': "❌"},
        'IDLE': {'icon': "🟢"},
        'NEUTRAL': {'icon': ""}
    }

    def __init__(self):
        self.current_state = self.STATES['IDLE']['icon']
        self._prompt_lock = threading.Lock()
        self._last_state = None
        self._last_time = 0.0
        self._last_prompt = None
        self._initial_prompt_shown = False
        self.setup_logging()

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
        formatted_text = ANSI(f"{self.RED}{self.BOLD}✗ {message}{self.RESET}")
        print_formatted_text(formatted_text)

    def print_success(self, message: str):
        formatted_text = ANSI(f"{self.GREEN}{self.BOLD}✓ {message}{self.RESET}")
        print_formatted_text(formatted_text)

    def print_warning(self, message: str):
        formatted_text = ANSI(f"{self.YELLOW}{self.BOLD}⚠ {message}{self.RESET}")
        print_formatted_text(formatted_text)

    def print_header(self, message: str):
        formatted_text = ANSI(f"\n{self.BOLD}{self.CYAN}=== {message} ==={self.RESET}\n")
        print_formatted_text(formatted_text)

    def print_status(self, message: str):
        formatted_text = ANSI(f"{self.BLUE}{self.BOLD}[STATUS] {message}{self.RESET}")
        print_formatted_text(formatted_text)

    def print_goodbye(self):
        formatted_text = ANSI(f"\n{self.GREEN}¡Adiós!{self.RESET}\n")
        print_formatted_text(formatted_text)

    def print_response(self, message: str, agent_name: str = None):
        message = str(message) if message is not None else ""

        prefix = ""
        if agent_name and agent_name.lower() in self.AGENT_EMOJIS:
            emoji = self.AGENT_EMOJIS[agent_name.lower()]
            prefix = f"{emoji} "
        
        formatted_lines = []
        for line in message.split('\n'):
            formatted_lines.append(f"{prefix}{line}")
        formatted_message = '\n'.join(formatted_lines)
        print_formatted_text(formatted_message)
        
        if self._last_prompt:
            print_formatted_text(ANSI(self._last_prompt), end='', flush=True)

    def update_prompt_state(self, state: str):
        with self._prompt_lock:
            now = time.time()
            if state == self._last_state and (now - self._last_time < 0.5):
                return
            
            self._last_state = state
            self._last_time = now
            
            state_props = self.STATES.get(state, {'icon': '>'})
            new_prompt = f"\r{state_props['icon']} "
            
            if new_prompt != self._last_prompt:
                print_formatted_text(ANSI(new_prompt), end='', flush=True)
                self._last_prompt = new_prompt
