import logging
import json
import os

class CommandManager:
    def __init__(self, tts=None, state=None, audio_effects=None):
        self.tts = tts
        self.state = state or {}
        self.audio_effects = audio_effects
        self.config_file = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self.config = {"audio": {"tts_enabled": True, "sound_effects_enabled": True}}

    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def handle_command(self, command: str):
        try:
            parts = command.lower().strip().split()
            main_cmd = parts[0]

            if main_cmd == 'config':
                if len(parts) < 3:
                    return "Uso: config [tts|effects] [on|off]"
                
                setting = parts[1]
                value = parts[2] == 'on'

                if setting == 'tts':
                    self.config['audio']['tts_enabled'] = value
                    if self.tts:
                        if not value:
                            self.tts.stop_speaking()
                    self.save_config()
                    return f"TTS {'activado' if value else 'desactivado'}"

                elif setting == 'effects':
                    self.config['audio']['sound_effects_enabled'] = value
                    self.save_config()
                    return f"Efectos de sonido {'activados' if value else 'desactivados'}"

                return "Configuración no válida"

            elif main_cmd in ['stop', 'para']:
                if self.tts:
                    self.tts.stop_speaking()
                return True
                
            elif main_cmd in ['exit', 'quit', 'salir']:
                if self.state:
                    self.state['running'] = False
                return True

            return False

        except Exception as e:
            logging.error(f"Error handling command: {e}")
            return f"Error: {str(e)}"