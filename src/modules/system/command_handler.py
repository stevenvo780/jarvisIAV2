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
        self.modules = {}
        self._register_default_modules()
        self._update_command_prompt()
        self.calendar_manager = CalendarManager(model_manager)

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
            f"Triggers: {', '.join(cmd['triggers'])}\n"  # Añadido triggers
            for cmd in commands
        ])
        
        self.command_prompt_template = f"""
        Eres un asistente experto en entender comandos e intenciones del usuario.
        Tu tarea es analizar la entrada y mapearla al comando exacto correspondiente.

        Comandos disponibles:
        {commands_text}

        Reglas ESTRICTAS:
        1. Para comandos del sistema (SYSTEM):
           - Si la entrada menciona abrir/ejecutar/iniciar aplicaciones -> SYSTEM_NOMBRE
           - Mapeos específicos:
             * Cualquier mención a calculadora -> SYSTEM_CALCULATOR
             * Cualquier mención a navegador/internet -> SYSTEM_BROWSER
             * Cualquier mención a música/reproducir -> SYSTEM_MUSIC
             * Cualquier mención a terminal/consola -> SYSTEM_TERMINAL
             * Cualquier mención a configuración/ajustes -> SYSTEM_SETTINGS

        2. Para eventos del calendario (CALENDAR):
           - Menciones a recordar/agendar/evento -> CALENDAR_CREATE:título
           - Consultas de agenda -> CALENDAR_LIST

        3. Si no hay coincidencia clara -> QUERY

        IMPORTANTE: 
        - Responde SOLO con el comando exacto (ej: SYSTEM_CALCULATOR, CALENDAR_CREATE:Título)
        - No agregues explicaciones ni texto adicional
        - Si detectas palabra clave de un comando, DEBES retornar ese comando

        Analiza esta entrada: "{{input}}"
        """

    def process_input(self, user_input: str) -> Tuple[str, str]:
        try:
            result = self._analyze_with_ai(user_input)
            logger.info(f"AI analysis result: {result}")
            
            if not result or result == "QUERY":
                # Intentar fallback antes de ir a query
                fallback_result = self._fallback_trigger_check(user_input)
                if fallback_result:
                    result = fallback_result
                else:
                    return None, "query"

            try:
                if '_' in result:
                    prefix, remainder = result.split('_', 1)
                    command = remainder.split(':', 1)[0].upper()
                    additional_info = remainder.split(':', 1)[1] if ':' in remainder else ""
                    
                    prefix = prefix.upper()
                    logger.debug(f"Processing command - Prefix: {prefix}, Command: {command}")
                    
                    if prefix in self.modules:
                        module = self.modules[prefix]
                        kwargs = {}
                        
                        if prefix == "CALENDAR":
                            kwargs = {
                                "text": user_input,
                                "title": additional_info
                            }
                        
                        response, success = module.execute_command(command, **kwargs)
                        logger.info(f"Command executed: {prefix}_{command} -> {success}")
                        return response, "command" if success else "error"
            except Exception as e:
                logger.error(f"Error executing command: {e}", exc_info=True)
                return f"Error ejecutando comando: {str(e)}", "error"
            
            return None, "query"
            
        except Exception as e:
            logger.error(f"Error en process_input: {e}")
            return f"Error procesando entrada: {str(e)}", "error"

    def _analyze_with_ai(self, user_input: str) -> Optional[str]:
        try:
            result = self.model_manager.models['google'].analyze_command(
                user_input, 
                self.command_prompt_template
            )
            if result:
                result = result.strip().upper()
                logger.info(f"AI command analysis: {result}")
                return result
            return self._fallback_trigger_check(user_input)
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return self._fallback_trigger_check(user_input)

    def _fallback_trigger_check(self, user_input: str) -> Optional[str]:
        lower_input = user_input.lower()
        
        # Primero verificar palabras clave comunes
        common_actions = {
            'abrir': True,
            'ejecutar': True,
            'iniciar': True,
            'mostrar': True,
            'reproducir': True
        }
        
        has_action = any(action in lower_input for action in common_actions)
        
        for prefix, module in self.modules.items():
            for cmd_name, cmd_info in module.commands.items():
                # Para comandos del sistema, requerir una acción
                if prefix == "SYSTEM" and not has_action:
                    continue
                    
                if any(trigger.lower() in lower_input for trigger in cmd_info.get('triggers', [])):
                    if prefix == "CALENDAR" and cmd_name == "CREATE":
                        if not any(time_indicator in lower_input for time_indicator in 
                                 ['mañana', 'hoy', ' am', ' pm', 'a las']):
                            continue
                    logger.info(f"Trigger match found: {prefix}_{cmd_name}")
                    return f"{prefix}_{cmd_name}"
        return None

    def register_command(self, command_name: str, command_func, command_config: Dict):
        if 'SYSTEM' in self.modules:
            self.modules['SYSTEM'].register_command(command_name, command_func, command_config)
            self._update_command_prompt()
