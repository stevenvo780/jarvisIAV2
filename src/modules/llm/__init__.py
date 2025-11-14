# modules/llm/__init__.py
from .model_manager import ModelManager
from .model_registry import ModelRegistry
from .base_model import BaseModel

# Import models subpackage to trigger registration
from . import models

# Re-export commonly used models for backward compatibility
from .models import (
    GoogleModel,
    OpenAIModel,
    LocalModel,
    AnthropicModel,
    DeepSeekModel,
    DeepInfraModel
)

__all__ = [
    'ModelManager',
    'ModelRegistry',
    'BaseModel',
    'GoogleModel',
    'OpenAIModel',
    'LocalModel',
    'AnthropicModel',
    'DeepSeekModel',
    'DeepInfraModel',
]
