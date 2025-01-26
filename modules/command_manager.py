import logging

class CommandManager:
    def __init__(self, tts=None, state=None):
        self.tts = tts
        self.state = state or {}

    def handle_command(self, command: str):
        try:
            cmd = command.lower().strip()
            if cmd in ['stop', 'para']:
                if self.tts:
                    self.tts.stop_speaking()
                return True
            if cmd in ['exit', 'quit', 'salir']:
                if self.state:
                    self.state['running'] = False
                return True
            return False
        except Exception as e:
            logging.error(f"Error handling command: {e}")