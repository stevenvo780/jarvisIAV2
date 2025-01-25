import sys
import os
import logging
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
            'response': '#00aaaa'
        })

    def _setup_colors(self):
        """Configures ANSI color codes."""
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
        """Visual states for the system."""
        self.STATES = {
            'LISTENING': f"{self.COLORS['GREEN']}🟢{self.COLORS['RESET']}",
            'IDLE': f"{self.COLORS['RED']}🔴{self.COLORS['RESET']}",
            'THINKING': f"{self.COLORS['BLUE']}💭{self.COLORS['RESET']}"
        }

    def setup_logging(self):
        """Sets up logging, silencing unnecessary logs."""
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
        """Shows formatted error messages."""
        print_formatted_text(HTML(f"✗ <error>{message}</error>"), style=self.style)

    def print_success(self, message: str):
        """Shows formatted success messages."""
        print_formatted_text(HTML(f"✓ <success>{message}</success>"), style=self.style)

    def print_warning(self, message: str):
        """Shows formatted warning messages."""
        print_formatted_text(HTML(f"⚠ <warning>{message}</warning>"), style=self.style)

    def print_header(self, message: str):
        """Header for important messages."""
        print_formatted_text(HTML(f"\n=== <header>{message}</header> ===\n"), style=self.style)

    def print_status(self, message: str):
        """Status message."""
        print_formatted_text(HTML(f"<info>[STATUS]</info> {message}"), style=self.style)

    def print_goodbye(self):
        """Farewell message."""
        print_formatted_text(HTML("\n<header>Goodbye!</header>\n"), style=self.style)

    def print_thinking(self):
        """Indicator of system processing."""
        print_formatted_text(HTML("<thinking>Thinking...</thinking>"), style=self.style)

    def print_response(self, message: str):
        """Prints system responses in a dedicated style."""
        lines = message.split('\n')
        for line in lines:
            print_formatted_text(HTML(f"<response>{line}</response>"), style=self.style)
        sys.stdout.flush()
