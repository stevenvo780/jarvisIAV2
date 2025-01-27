import subprocess
import logging
import json
import os
from typing import Dict, Callable, Any
import webbrowser

logger = logging.getLogger(__name__)

class UbuntuCommander:
    def __init__(self):
        self.commands_config = self._load_commands_config()
        self.commands = {}
        self._register_default_commands()

    def _load_commands_config(self) -> Dict:
        config_path = os.path.join('src', 'config', 'commands_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading commands config: {e}")
            return {"system_commands": {}}

    def _register_default_commands(self):
        default_methods = {
            '_open_calculator': self._open_calculator,
            '_open_browser': self._open_browser,
            '_play_music': self._play_music,
            '_open_terminal': self._open_terminal,
            '_open_settings': self._open_settings
        }

        for cmd_name, cmd_info in self.commands_config['system_commands'].items():
            method_name = cmd_info.get('method')
            if method_name in default_methods:
                self.commands[cmd_name] = {
                    'func': default_methods[method_name],
                    'config': cmd_info
                }

    def execute_command(self, command_name: str, **kwargs) -> bool:
        if command_name not in self.commands:
            logger.error(f"Command {command_name} not found")
            return False

        command = self.commands[command_name]
        try:
            params = {**command['config'].get('default_params', {}), **kwargs}
            return command['func'](**params)
        except Exception as e:
            logger.error(f"Error executing command {command_name}: {e}")
            return False

    def register_command(self, command_name: str, command_func: Callable, command_config: Dict) -> None:
        self.commands[command_name] = {
            'func': command_func,
            'config': command_config
        }
        # Actualizar la configuración en memoria
        if 'system_commands' not in self.commands_config:
            self.commands_config['system_commands'] = {}
        self.commands_config['system_commands'][command_name] = command_config

    def get_commands_info(self) -> Dict:
        return self.commands_config['system_commands']

    def _open_calculator(self) -> bool:
        try:
            subprocess.Popen(['gnome-calculator'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo calculadora: {e}")
            return False

    def _open_browser(self, url: str = "https://www.google.com") -> bool:
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Error abriendo navegador: {e}")
            return False

    def _play_music(self) -> bool:
        try:
            subprocess.Popen(['rhythmbox'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo reproductor de música: {e}")
            return False

    def _open_terminal(self) -> bool:
        try:
            subprocess.Popen(['gnome-terminal'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo terminal: {e}")
            return False

    def _open_settings(self) -> bool:
        try:
            subprocess.Popen(['gnome-control-center'])
            return True
        except Exception as e:
            logger.error(f"Error abriendo configuración: {e}")
            return False
