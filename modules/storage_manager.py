import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

class StorageManager:
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = storage_dir
        self.history_file = os.path.join(storage_dir, "conversation_history.json")
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Asegura que el directorio de almacenamiento existe"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_conversation(self, conversation: List[Dict[str, Any]]) -> bool:
        """Guarda el historial de conversación en archivo JSON"""
        try:
            # Preparar datos para guardar
            data_to_save = {
                "last_updated": datetime.now().isoformat(),
                "conversations": conversation
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error guardando conversación: {e}")
            return False

    def load_conversation(self) -> List[Dict[str, Any]]:
        """Carga el historial de conversación desde archivo JSON"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("conversations", [])
            return []
        except Exception as e:
            logging.error(f"Error cargando conversación: {e}")
            return []

    def clear_history(self) -> bool:
        """Limpia el historial guardado"""
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
            return True
        except Exception as e:
            logging.error(f"Error limpiando historial: {e}")
            return False
