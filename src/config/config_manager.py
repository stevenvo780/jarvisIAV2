"""
Centralized Configuration Manager
Singleton pattern for managing all application configuration
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class GPUConfig:
    """GPU configuration"""
    gpu_id: int
    name: str
    vram_total: int
    vram_reserved: int
    primary_use: str


@dataclass
class SystemConfig:
    """System-wide configuration"""
    max_errors: int = 5
    vram_buffer_mb: int = 500
    history_size: int = 10
    log_level: str = "INFO"
    enable_gpu_monitoring: bool = True


class ConfigManager:
    """
    Singleton configuration manager
    
    Usage:
        config = ConfigManager.get_instance()
        api_key = config.get_api_key("OPENAI_API_KEY")
    """
    
    _instance: Optional['ConfigManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logger = logging.getLogger("ConfigManager")
        self.project_root = Path(__file__).parent.parent.parent
        
        # Load environment variables
        load_dotenv(self.project_root / ".env")
        
        # Load configuration files
        self.models_config = self._load_json("src/config/models_v2.json")
        self.audio_config = self._load_json("src/config/audio_config.json")
        self.commands_config = self._load_json("src/config/commands_config.json")
        self.app_config = self._load_json("src/config/config.json")
        
        # Parse system config
        self.system_config = self._parse_system_config()
        
        self._initialized = True
        self.logger.info("✅ ConfigManager initialized")
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance
    
    def _load_json(self, relative_path: str) -> Dict[str, Any]:
        """Load JSON configuration file"""
        file_path = self.project_root / relative_path
        
        if not file_path.exists():
            self.logger.warning(f"Config file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            return {}
    
    def _parse_system_config(self) -> SystemConfig:
        """Parse system configuration"""
        system_data = self.models_config.get("system", {})
        
        return SystemConfig(
            max_errors=system_data.get("max_errors", 5),
            vram_buffer_mb=system_data.get("vram_buffer_mb", 500),
            history_size=system_data.get("history_size", 10),
            log_level=system_data.get("log_level", "INFO"),
            enable_gpu_monitoring=system_data.get("enable_gpu_monitoring", True)
        )
    
    def get_api_key(self, key_name: str, required: bool = True) -> Optional[str]:
        """
        Get API key from environment variables
        
        Args:
            key_name: Name of the environment variable
            required: If True, raise error if not found
        
        Returns:
            API key value or None
        
        Raises:
            ConfigError: If required key is missing
        """
        from src.utils.error_handler import ConfigError
        
        value = os.getenv(key_name)
        
        if required and not value:
            raise ConfigError(
                f"Required API key '{key_name}' not found in environment variables",
                details={"key_name": key_name}
            )
        
        return value
    
    def get_gpu_config(self, gpu_id: int) -> Optional[GPUConfig]:
        """Get GPU configuration by ID"""
        gpu_data = self.models_config.get("gpu_config", {}).get(f"gpu_{gpu_id}")
        
        if not gpu_data:
            return None
        
        return GPUConfig(
            gpu_id=gpu_id,
            name=gpu_data.get("name", f"GPU_{gpu_id}"),
            vram_total=gpu_data.get("vram_total", 0),
            vram_reserved=gpu_data.get("vram_reserved", 0),
            primary_use=gpu_data.get("primary_use", "General")
        )
    
    def get_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model configuration by ID"""
        return self.models_config.get("models", {}).get(model_id)
    
    def get_all_model_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all model configurations"""
        return self.models_config.get("models", {})
    
    def get_api_models(self) -> Dict[str, Dict[str, Any]]:
        """Get all API model configurations"""
        return self.models_config.get("api_models", {})
    
    def validate_config(self) -> bool:
        """
        Validate all configuration
        
        Returns:
            True if valid, False otherwise
        """
        errors = []
        
        # Check required API keys (optional for local-only mode)
        required_keys = []  # Made optional
        for key in required_keys:
            if not os.getenv(key):
                errors.append(f"Missing environment variable: {key}")
        
        # Validate models config
        if not self.models_config.get("models"):
            errors.append("No models configured in models_v2.json")
        
        # Validate GPU config
        gpu_config = self.models_config.get("gpu_config", {})
        if not gpu_config:
            self.logger.warning("No GPU configuration found")
        
        if errors:
            for error in errors:
                self.logger.error(f"Config validation error: {error}")
            return False
        
        self.logger.info("✅ Configuration validation passed")
        return True
    
    def get_path(self, relative_path: str) -> Path:
        """Get absolute path from relative path"""
        return self.project_root / relative_path
    
    def reload(self):
        """Reload all configurations"""
        self._initialized = False
        self.__init__()
