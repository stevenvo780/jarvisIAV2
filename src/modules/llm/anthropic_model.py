"""
Anthropic Claude Model Handler for Jarvis IA V2
Supports Claude-3.5-Sonnet for advanced reasoning
"""

import os
import logging
from typing import Optional, Dict, Any

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("anthropic not available. Install: pip install anthropic")

from .base_model import BaseModel


class AnthropicModel(BaseModel):
    """
    Anthropic Claude API handler
    
    Supported models:
    - claude-3-5-sonnet-20241022 (recommended)
    - claude-3-opus-20240229
    - claude-3-haiku-20240307
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = {
            'model_name': 'claude-3-5-sonnet-20241022',
            'temperature': 0.7,
            'max_tokens': 4096,
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(merged_config)
        
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Install anthropic: pip install anthropic")
        
        # Get API key
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        # Initialize client
        self.client = Anthropic(api_key=self.api_key)
        
        self.logger.info(f"✅ AnthropicModel initialized: {self.config['model_name']}")
    
    def get_response(self, query: str) -> str:
        """
        Get response from Claude
        
        Args:
            query: User query
        
        Returns:
            Model response
        """
        if not isinstance(query, str) or len(query.strip()) < 3:
            return "La consulta debe ser un texto no vacío (>3 caracteres)"
        
        try:
            message = self.client.messages.create(
                model=self.config['model_name'],
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature'],
                messages=[
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            )
            
            # Extract text from response
            if message.content and len(message.content) > 0:
                response_text = message.content[0].text
                return self.sanitize_response(response_text)
            
            return "No se recibió una respuesta válida de Claude"
        
        except Exception as e:
            self.logger.error(f"Error al obtener respuesta de Claude: {e}")
            return "Error al procesar la consulta con Claude"
    
    def get_streaming_response(self, query: str):
        """
        Get streaming response from Claude (generator)
        
        Args:
            query: User query
        
        Yields:
            Response chunks
        """
        try:
            with self.client.messages.stream(
                model=self.config['model_name'],
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature'],
                messages=[{"role": "user", "content": query}]
            ) as stream:
                for text in stream.text_stream:
                    yield text
        
        except Exception as e:
            self.logger.error(f"Error en streaming de Claude: {e}")
            yield "Error al procesar la consulta con Claude"
    
    def __repr__(self):
        return f"<AnthropicModel: {self.config['model_name']}>"
