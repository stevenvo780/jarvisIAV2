import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

class StorageManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.context_file = self.data_dir / "jarvis_context.json"
        self.history_file = self.data_dir / "conversation_history.json"
        self.context = self._load_context()
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        self.data_dir.mkdir(exist_ok=True)

    def _load_context(self) -> Dict:
        if self.context_file.exists():
            try:
                return json.loads(self.context_file.read_text(encoding='utf-8'))
            except Exception as e:
                logging.error(f"Error loading context: {e}")
        return self._create_default_context()

    def get_context(self) -> Dict:
        return self.context

    def get_recent_history(self, limit: int = 3) -> List[Dict]:
        try:
            if self.history_file.exists():
                data = json.loads(self.history_file.read_text(encoding='utf-8'))
                return data.get("conversations", [])[-limit:]
            return []
        except Exception as e:
            logging.error(f"Error loading history: {e}")
            return []

    def add_interaction(self, interaction: Dict):
        try:
            # Actualizar estadísticas
            self.context["interaction_stats"]["total_interactions"] += 1
            self.context["interaction_stats"]["last_interaction"] = datetime.now().isoformat()
            
            topic = interaction["query"].split()[0].lower()
            self.context["interaction_stats"]["frequent_topics"][topic] = \
                self.context["interaction_stats"]["frequent_topics"].get(topic, 0) + 1

            # Guardar contexto actualizado
            self.context_file.write_text(
                json.dumps(self.context, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )

            # Añadir a historial
            history = self.get_recent_history(100)  # Limitar a últimas 100 interacciones
            history.append({
                "timestamp": datetime.now().isoformat(),
                **interaction
            })
            
            self.history_file.write_text(
                json.dumps({"conversations": history}, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )

        except Exception as e:
            logging.error(f"Error saving interaction: {e}")

    def get_relevant_memories(self, limit: int = 5) -> str:
        memories = self.context.get("context_memory", [])[-limit:]
        return "\n".join(memories) if memories else "Sin contexto adicional"

    def clear_history(self) -> bool:
        try:
            if self.history_file.exists():
                self.history_file.unlink()
            return True
        except Exception as e:
            logging.error(f"Error clearing history: {e}")
            return False
