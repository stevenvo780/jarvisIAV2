"""
Model Registry - Factory Pattern Implementation

This module provides a centralized registry for LLM model classes.
Models can self-register, making the system extensible without modifying core code.
"""

import logging
from typing import Dict, Type, Optional
from src.modules.llm.base_model import BaseModel


class ModelRegistry:
    """
    Registry for LLM model classes following Factory Pattern.

    Allows dynamic model registration and instantiation without tight coupling.
    """

    _instance = None
    _models: Dict[str, Type[BaseModel]] = {}

    def __new__(cls):
        """Singleton pattern to ensure single registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str, model_class: Type[BaseModel]) -> None:
        """
        Register a model class with a given name.

        Args:
            name: Unique identifier for the model (e.g., 'google', 'openai')
            model_class: The model class (must inherit from BaseModel)

        Raises:
            ValueError: If model_class doesn't inherit from BaseModel
        """
        if not issubclass(model_class, BaseModel):
            raise ValueError(f"{model_class.__name__} must inherit from BaseModel")

        cls._models[name] = model_class
        logging.debug(f"Modelo '{name}' registrado: {model_class.__name__}")

    @classmethod
    def create(cls, name: str, **kwargs) -> Optional[BaseModel]:
        """
        Create an instance of a registered model.

        Args:
            name: The model identifier
            **kwargs: Arguments to pass to the model constructor

        Returns:
            Instance of the requested model, or None if not found

        Raises:
            KeyError: If model name is not registered
            Exception: If model instantiation fails
        """
        if name not in cls._models:
            available = ', '.join(cls._models.keys())
            raise KeyError(
                f"Model '{name}' not registered. "
                f"Available models: {available}"
            )

        model_class = cls._models[name]
        try:
            instance = model_class(**kwargs)
            logging.info(f"Modelo '{name}' instanciado correctamente")
            return instance
        except Exception as e:
            logging.error(f"Error instanciando modelo '{name}': {e}")
            raise

    @classmethod
    def list_models(cls) -> list:
        """Return list of all registered model names."""
        return list(cls._models.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a model is registered."""
        return name in cls._models

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a model (mainly for testing purposes).

        Args:
            name: The model identifier to unregister
        """
        if name in cls._models:
            del cls._models[name]
            logging.debug(f"Modelo '{name}' eliminado del registro")


# Convenience function for registration
def register_model(name: str):
    """
    Decorator for auto-registering model classes.

    Usage:
        @register_model('mymodel')
        class MyModel(BaseModel):
            pass
    """
    def decorator(cls):
        ModelRegistry.register(name, cls)
        return cls
    return decorator
