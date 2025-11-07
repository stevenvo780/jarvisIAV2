import logging
from typing import Tuple, Optional, Dict
from sympy import re
from modules.system.base_commander import BaseCommander
from modules.system.calendar_commander import CalendarCommander
from src.modules.system.ubuntu_commander import UbuntuCommander
from src.modules.system.multimedia_commander import MultimediaCommander
from src.modules.system.calendar_commander import CalendarCommander
from src.modules.system.math_commander import MathCommander

logger = logging.getLogger(__name__)

class CommandManager:
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.modules = {}
        self._register_default_modules()
        self._update_command_prompt()

    def _register_default_modules(self):
        self.register_module('SYSTEM', UbuntuCommander())
        #self.register_module('CALENDAR', CalendarCommander(self.model_manager))
        self.register_module('MEDIA', MultimediaCommander(self.model_manager))
        self.register_module('MATH', MathCommander())

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
            f"Triggers: {', '.join(cmd['triggers'])}\n"
            for cmd in commands
        ])

        self.command_prompt_template = f"""
        Tu tarea es identificar comandos exactos y extraer información relevante de la entrada del usuario.
        
        Comandos disponibles:
        {commands_text}

        Reglas CRÍTICAS:
        1. Para CALENDAR_CREATE: SIEMPRE incluye el título después de ':' 
           Ejemplo: "recordar comprar pan" -> CALENDAR_CREATE:comprar pan
           Ejemplo: "recuerdame sacar la basura" -> CALENDAR_CREATE:sacar la basura
        2. Para otros comandos: usa el formato MODULO_COMANDO
           Ejemplo: "abrir calculadora" -> SYSTEM_CALCULATOR
        3. Si no hay coincidencia clara -> QUERY
        4. NO agregues explicaciones, SOLO el comando

        Ejemplos adicionales:
        "recordar mañana ir al dentista" -> CALENDAR_CREATE:ir al dentista
        "recuerdame llamar a mamá" -> CALENDAR_CREATE:llamar a mamá
        "mostrar eventos" -> CALENDAR_LIST
        "hola como estás" -> QUERY

        Analiza esta entrada: "{{input}}"
        """

    def process_input(self, user_input: str) -> Tuple[str, str]:
        try:
            for module in self.modules.values():
                if module.should_handle_command(user_input):
                    command, additional_info = module.extract_command_info(user_input)
                    if command:
                        prefix = module.command_prefix
                        logger.debug(f"Direct command match: {prefix}_{command}")
                        kwargs = module.process_command_parameters(command, user_input, additional_info)
                        response, success = module.execute_command(command, **kwargs)
                        return response, "command" if success else "error"

            result = self._analyze_with_ai(user_input)
            logger.info(f"AI analysis result: {result}")
            
            if not result or result == "QUERY":
                return None, "query"

            if '_' in result:
                prefix, remainder = result.split('_', 1)
                command = remainder.split(':', 1)[0].upper()
                additional_info = remainder.split(':', 1)[1] if ':' in remainder else ""
                
                prefix = prefix.upper()
                if prefix in self.modules:
                    module = self.modules[prefix]
                    kwargs = module.process_command_parameters(command, user_input, additional_info)
                    response, success = module.execute_command(command, **kwargs)
                    return response, "command" if success else "error"
            
            return None, "query"
            
        except Exception as e:
            logger.error(f"Error en process_input: {e}")
            return f"Error procesando entrada: {str(e)}", "error"

    def _analyze_with_ai(self, user_input: str) -> Optional[str]:
        try:
            # TODO: Adapt this to work with ModelOrchestrator
            # For now, skip AI analysis and use fallback
            logger.info(f"AI analysis result: Skipped (using fallback)")
            return self._fallback_trigger_check(user_input)
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return self._fallback_trigger_check(user_input)

    def _fallback_trigger_check(self, user_input: str) -> Optional[str]:
        for module in self.modules.values():
            if module.should_handle_command(user_input):
                command, additional_info = module.extract_command_info(user_input)
                if command:
                    return module.format_command_response(command, additional_info)
        return None

    def register_command(self, command_name: str, command_func, command_config: Dict):
        if 'SYSTEM' in self.modules:
            self.modules['SYSTEM'].register_command(command_name, command_func, command_config)
            self._update_command_prompt()

    def _extract_title_from_input(self, user_input: str) -> str:
        words_to_remove = ['recordar', 'recuerdame', 'agendar', 'crear evento', 'mañana', 'hoy']
        time_patterns = [
            r'a las \d{1,2}(?::\d{2})?(?:\s*[ap]m)?',
            r'para las \d{1,2}(?::\d{2})?(?:\s*[ap]m)?',
            r'(\d{1,2})(?::\d{2})?(?:\s*[ap]m)?'
        ]
        
        text = user_input.lower()
        
        for word in words_to_remove:
            text = text.replace(word, '')
            
        for pattern in time_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        title = text.strip()
        if title:
            title = title[0].upper() + title[1:]
            
        return title if title else "Recordatorio"
