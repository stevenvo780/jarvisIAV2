"""
DeepSeek API Model Handler for Jarvis IA V2
Uses official DeepSeek API for math and reasoning tasks
"""

import os
import logging
from typing import Optional, Dict, Any

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai not available")

from .base_model import BaseModel


class DeepSeekModel(BaseModel):
    """
    DeepSeek API handler (OpenAI-compatible)
    
    Supported models:
    - deepseek-chat (recommended for general use)
    - deepseek-reasoner (for complex reasoning)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = {
            'model_name': 'deepseek-chat',
            'temperature': 0.7,
            'max_tokens': 4096,
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(merged_config)
        
        if not OPENAI_AVAILABLE:
            raise ImportError("Install openai: pip install openai")
        
        # Get API key
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        
        # Initialize client (OpenAI-compatible)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
            timeout=30.0,
            max_retries=3
        )
        
        self.logger.info(f"✅ DeepSeekModel initialized: {self.config['model_name']}")
    
    def get_response(self, query: str) -> str:
        """
        Get response from DeepSeek
        
        Args:
            query: User query
        
        Returns:
            Model response
        """
        if not isinstance(query, str) or len(query.strip()) < 3:
            return "La consulta debe ser un texto no vacío (>3 caracteres)"
        
        try:
            response = self.client.chat.completions.create(
                model=self.config['model_name'],
                messages=[{'role': 'user', 'content': query}],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            
            if response.choices and response.choices[0].message:
                return self.sanitize_response(response.choices[0].message.content)
            
            return "No se recibió una respuesta válida de DeepSeek"
        
        except Exception as e:
            self.logger.error(f"Error al obtener respuesta de DeepSeek: {e}")
            return "Error al procesar la consulta con DeepSeek"
    
    def __repr__(self):
        return f"<DeepSeekModel: {self.config['model_name']}>"


# Legacy compatibility
class DeepInfraModel(DeepSeekModel):
    """Legacy name for backward compatibility"""
    pass
