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
        if "audio" in self.config and "listening_enabled" in self.config["audio"]:
            self.state['listening_active'] = self.config["audio"]["listening_enabled"]

    def handle_command(self, command: str):
        try:
            command = command.lower().strip()
            parts = command.split()
            
            if command in ['help', 'ayuda']:
                help_text = (
                    "Comandos disponibles:\n"
                    "- enable listening: Activa el sistema de escucha\n"
                    "- disable listening: Desactiva el sistema de escucha\n"
                    "- enable speech: Activa el TTS\n"
                    "- disable speech: Desactiva el TTS\n"
                    "- para/stop/detente/silencio: Detiene la acción actual\n"
                    "- clear/limpiar/cls: Limpia la terminal\n"
                    "- exit/quit/salir: Finaliza el programa\n"
                    "- config [tts|effects] [on|off]: Configura opciones\n"
                )
                return help_text, True

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

            if command == "enable listening":
                if self.audio_handler:
                    msg = self.audio_handler.set_listening(True)
                    self.config['audio']['listening_enabled'] = True
                    self.save_config()
                    return msg, True
                return "Voice system not available", False

            if command == "disable listening":
                if self.audio_handler:
                    msg = self.audio_handler.set_listening(False)
                    self.config['audio']['listening_enabled'] = False
                    self.save_config()
                    return msg, True
                return "Voice system not available", False

            if command == "enable speech":
                self.config['audio']['tts_enabled'] = True
                self.save_config()
                return "Speech enabled", True

            if command == "disable speech":
                self.config['audio']['tts_enabled'] = False
                if self.tts:
                    self.tts.stop_speaking()
                self.save_config()
                return "Speech disabled", True

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
            if "audio" not in self.config:
                self.config["audio"] = {}
            self.config["audio"].setdefault("tts_enabled", True)
            self.config["audio"].setdefault("sound_effects_enabled", True)
            self.config["audio"].setdefault("listening_enabled", True)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self.config = {"audio": {"tts_enabled": True, "sound_effects_enabled": True, "listening_enabled": True}}

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