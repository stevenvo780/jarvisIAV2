import logging
import os
from typing import Tuple, Optional, Dict
import google.generativeai as genai
from modules.system.base_commander import BaseCommander
from modules.system.calendar_manager import CalendarManager
from src.modules.system.ubuntu_commander import UbuntuCommander

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada en variables de entorno")
        
        genai.configure(api_key=self.api_key)
        self.ai_model = genai.GenerativeModel("gemini-pro")
        self.modules = {}
        self._register_default_modules()
        self._update_command_prompt()
        self.calendar_manager = CalendarManager()

    def _register_default_modules(self):
        self.register_module('SYSTEM', UbuntuCommander())
        self.register_module('CALENDAR', CalendarManager())

    def register_module(self, name: str, module: BaseCommander):
        self.modules[name] = module
        self._update_command_prompt()

    def _build_commands_description(self):
        descriptions = []
        for module_name, module in self.modules.items():
            descriptions.extend(module.get_command_descriptions())
        return descriptions

    def _update_command_prompt(self):
        commands = self._build_commands_description()
        commands_text = "\n".join([
            f"Módulo: {cmd['prefix']}\n"
            f"Comando: {cmd['command']}\n"
            f"Descripción: {cmd['description']}\n"
            f"Ejemplos: {', '.join(cmd['examples'])}\n"
            for cmd in commands
        ])
        
        self.command_prompt_template = f"""
        Eres un asistente experto en entender comandos e intenciones del usuario.
        Tu tarea es mapear la entrada a uno de estos comandos específicos.

        Comandos disponibles:
        {commands_text}

        Reglas de decisión:
        1. Para comandos del sistema (SYSTEM):
           - Si mencionan "abrir", "iniciar", "ejecutar" -> mapear al comando correspondiente
           - Ejemplos:
             "abre la calculadora" -> "SYSTEM_CALCULATOR"
             "abrir navegador" -> "SYSTEM_BROWSER"
             "pon música" -> "SYSTEM_MUSIC"

        2. Para eventos del calendario (CALENDAR):
           - Si mencionan "recordar", "agendar", "evento" -> "CALENDAR_CREATE:título"
           - Para consultas de agenda -> "CALENDAR_LIST"
           - Ejemplos:
             "recuérdame llamar a mamá" -> "CALENDAR_CREATE:Llamar a mamá"
             "qué eventos tengo" -> "CALENDAR_LIST"

        3. Si no coincide con ningún comando -> "QUERY"

        Instrucción: Analiza esta entrada y responde SOLO con el comando correspondiente.
        Entrada: "{{input}}"
        """

    def process_input(self, user_input: str) -> Tuple[str, str]:
        try:
            result = self._analyze_with_ai(user_input)
            logger.info(f"AI analysis result: {result}")
            
            if not result or result == "QUERY":
                return None, "query"

            try:
                if '_' in result:
                    prefix, remainder = result.split('_', 1)
                    command, *args = remainder.split(':', 1)
                    
                    prefix = prefix.upper()
                    command = command.upper()
                    
                    if prefix in self.modules:
                        module = self.modules[prefix]
                        additional_info = args[0] if args else ""
                        response, success = module.execute_command(
                            command, 
                            text=user_input,
                            title=additional_info
                        )
                        logger.info(f"Command executed: {prefix}_{command} -> {success}")
                        return response, "command" if success else "error"
            except ValueError:
                pass
            
            return None, "query"
            
        except Exception as e:
            logger.error(f"Error en process_input: {e}")
            return f"Error procesando entrada: {str(e)}", "error"

    def _analyze_with_ai(self, user_input: str) -> Optional[str]:
        try:
            prompt = self.command_prompt_template.format(input=user_input)
            response = self.ai_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0,
                    'top_p': 1,
                    'top_k': 1,
                }
            )
            
            if response.text:
                result = response.text.strip()
                logger.info(f"AI response: {result}")
                return result
            
            return self._fallback_trigger_check(user_input)
            
        except Exception as e:
            logger.error(f"Error analizando con IA: {e}")
            return self._fallback_trigger_check(user_input)

    def _fallback_trigger_check(self, user_input: str) -> Optional[str]:
        lower_input = user_input.lower()
        for prefix, module in self.modules.items():
            for cmd_name, cmd_info in module.commands.items():
                if any(trigger.lower() in lower_input for trigger in cmd_info.get('triggers', [])):
                    if prefix == "CALENDAR" and cmd_name == "CREATE":
                        if not any(time_indicator in lower_input for time_indicator in 
                                 ['mañana', 'hoy', ' am', ' pm', 'a las']):
                            continue
                    logger.info(f"Trigger match found: {prefix}_{cmd_name}")
                    return f"{prefix}_{cmd_name}"
        return None

    def register_command(self, command_name: str, command_func, command_config: Dict):
        self.ubuntu_commander.register_command(command_name, command_func, command_config)
        self._update_command_prompt()
