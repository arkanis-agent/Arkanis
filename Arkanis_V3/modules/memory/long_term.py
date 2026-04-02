import os
import json
import threading
from typing import Dict, List, Any

MEM_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data", "long_term_memory.json")

class LongTermMemory:
    """
    Persistent long-term memory storage for ARKANIS V3.
    Stores and retrieves user preferences, important facts, and recurring tasks.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.data: Dict[str, List[str]] = {
            "preferences": [],
            "facts": [],
            "recurrent_tasks": []
        }
        self.max_items_per_category = 20
        self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(MEM_FILE), exist_ok=True)

    def _load(self):
        with self._lock:
            if os.path.exists(MEM_FILE):
                try:
                    with open(MEM_FILE, "r", encoding="utf-8") as f:
                        loaded_data = json.load(f)
                        # Merge to ensure keys exist
                        for k in self.data.keys():
                            if k in loaded_data:
                                self.data[k] = loaded_data[k]
                except Exception as e:
                    print(f"[Memory] Failed to load long term memory: {e}")

    def _save(self):
        self._ensure_dir()
        with self._lock:
            try:
                with open(MEM_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[Memory] Failed to save long term memory: {e}")

    def add_memory(self, category: str, content: str) -> bool:
        """Add a new memory to a category, preventing exact duplicates."""
        if category not in self.data:
            return False
            
        content_clean = content.strip()
        with self._lock:
            # Prevent exact duplicate
            if content_clean in self.data[category]:
                return True
                
            self.data[category].append(content_clean)
            # Enforce size limit by popping oldest
            if len(self.data[category]) > self.max_items_per_category:
                self.data[category].pop(0)
                
        self._save()
        return True

    def get_formatted_memory(self) -> str:
        """Returns the long-term memory formatted for the LLM context."""
        with self._lock:
            out = []
            if self.data["preferences"]:
                out.append("[PREFERÊNCIAS DO USUÁRIO]")
                out.extend([f"- {p}" for p in self.data["preferences"]])
            if self.data["facts"]:
                out.append("[FATOS IMPORTANTES]")
                out.extend([f"- {f}" for f in self.data["facts"]])
            if self.data["recurrent_tasks"]:
                out.append("[TAREFAS RECORRENTES]")
                out.extend([f"- {t}" for t in self.data["recurrent_tasks"]])
                
            if not out:
                return ""
            return "\n".join(out)

# Global singleton
long_term_memory = LongTermMemory()
