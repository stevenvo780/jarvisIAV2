import logging
import os
from typing import Tuple, Optional, Dict
import google.generativeai as genai
from src.modules.system.ubuntu_commander import UbuntuCommander

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.ubuntu_commander = UbuntuCommander()
        
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada en variables de entorno")
        
        genai.configure(api_key=self.api_key)
        self.ai_model = genai.GenerativeModel("gemini-pro")
        
        self._update_command_prompt()
        self.valid_commands = self.ubuntu_commander.get_commands_info().keys()

    def _update_command_prompt(self):
        commands_info = self.ubuntu_commander.get_commands_info()
        commands_description = "\n".join([
            f"- {cmd}: {info['description']}" 
            for cmd, info in commands_info.items()
        ])
        
        self.command_prompt_template = f"""
        Eres un analizador de comandos para un asistente virtual. Analiza la siguiente entrada y determina:
        1. Si es un comando de sistema o una consulta general
        2. Si es un comando, identifica cuál de los siguientes comandos debe ejecutarse basado en el contexto y la intención del usuario:

        Comandos disponibles:
        {self._format_commands(self.ubuntu_commander.get_commands_info())}

        Formato de respuesta esperado:
        Si es un comando: "COMMAND:nombre_comando"
        Si es consulta general: "QUERY"

        Entrada del usuario: "{{input}}"
        """

    def _format_triggers(self, commands_info):
        return "\n".join([
            f"- {cmd}: {', '.join(info['triggers'])}"
            for cmd, info in commands_info.items()
            if 'triggers' in info
        ])

    def _format_commands(self, commands_info):
        return "\n".join([
            f"- {cmd}: {info['description']}" 
            for cmd, info in commands_info.items()
        ])

    def process_input(self, user_input: str) -> Tuple[str, str]:
        try:
            is_command, command_name = self._analyze_with_ai(user_input)
            
            if is_command and command_name in self.valid_commands:
                success = self.ubuntu_commander.execute_command(command_name)
                return (
                    f"Comando {command_name} ejecutado exitosamente" if success 
                    else f"Error ejecutando {command_name}",
                    "command"
                )

            return None, "query"
            
        except Exception as e:
            logger.error(f"Error en process_input: {e}")
            return f"Error procesando entrada: {str(e)}", "error"

    def _analyze_with_ai(self, user_input: str) -> Tuple[bool, Optional[str]]:
        try:
            prompt = self.command_prompt_template.format(input=user_input)
            response = self.ai_model.generate_content(prompt)
            
            if not response.text:
                return False, None
            
            result = response.text.strip()
            if result.startswith("COMMAND:"):
                command = result.replace("COMMAND:", "").strip()
                return True, command
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error analizando comando con IA: {e}")
            return False, None

    def register_command(self, command_name: str, command_func, command_config: Dict):
        self.ubuntu_commander.register_command(command_name, command_func, command_config)
        self._update_command_prompt()
