import json
import os
from typing import Dict, Any, Optional

class PromptBuilder:
    def __init__(self, context_path: str = None):
        if context_path is None:
            context_path = os.path.join(os.path.dirname(__file__), '../data/jarvis_context.json')
        
        with open(context_path, 'r', encoding='utf-8') as f:
            self.context = json.load(f)

    def get_system_prompt(self, model_type: str) -> str:
        """Obtiene el prompt del sistema para un tipo específico de modelo."""
        try:
            return self.context['prompts']['system_context'][model_type]['template']
        except KeyError:
            return self.context['prompts']['system_base'].format(
                name=self.context['assistant_profile']['name']
            )

    def build_prompt(self, query: str, model_type: str) -> Dict[str, Any]:
        """Construye el prompt completo según el tipo de modelo."""
        system_prompt = self.get_system_prompt(model_type)
        format_type = self.context['prompts']['system_context'][model_type].get('format', 'text')

        if format_type == 'chat':
            return {
                'messages': [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ]
            }
        else:
            return {
                'prompt': f"{system_prompt}\n\nUsuario: {query}\n{self.context['assistant_profile']['name']}:"
            }

    def get_error_message(self, error_key: str, **kwargs) -> str:
        """Obtiene un mensaje de error formateado."""
        template = self.context['prompts']['templates'].get('error', 'Error: {message}')
        return template.format(**kwargs)

    def get_thinking_message(self) -> str:
        """Obtiene el mensaje de 'pensando'."""
        return self.context['prompts']['templates'].get('thinking', 'Procesando solicitud...')
