import logging
import json
import os
from prompt_toolkit.shortcuts import clear

class Actions:
    def __init__(self, tts=None, state=None, audio_effects=None, audio_handler=None):
        self.tts = tts
        self.state = state or {}
        self.audio_effects = audio_effects 
        self.audio_handler = audio_handler
        self.config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
        self.load_config()

    def handle_command(self, command: str):
        try:
            command = command.lower().strip()
            parts = command.split()
            
            if command in ['para', 'stop', 'detente', 'silencio']:
                if self.tts:
                    self.tts.stop_speaking()
                return "Vale", True

            if command in ['exit', 'quit', 'salir']:
                self.state['running'] = False
                return None, True
            
            if command in ['clear', 'limpiar', 'cls']:
                clear()
                return None, True

            main_cmd = parts[0]
            if main_cmd == 'config':
                if len(parts) < 3:
                    return "Uso: config [tts|effects] [on|off]"
                
                setting, value = parts[1], parts[2] == 'on'
                
                if setting == 'tts':
                    self.config['audio']['tts_enabled'] = value
                    if self.tts and not value:
                        self.tts.stop_speaking()
                    self.save_config()
                    return f"TTS {'activado' if value else 'desactivado'}", True
                    
                elif setting == 'effects':
                    self.config['audio']['sound_effects_enabled'] = value
                    self.save_config()
                    return f"Efectos de sonido {'activados' if value else 'desactivados'}", True
                    
                return "Configuración no válida", True

            return None, False

        except Exception as e:
            logging.error(f"Error handling command: {e}")
            return f"Error: {str(e)}", False

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

    def _toggle_listening(self):
        if self.audio_handler:
            return self.audio_handler.toggle_listening(), True
        return "Sistema de voz no disponible", False