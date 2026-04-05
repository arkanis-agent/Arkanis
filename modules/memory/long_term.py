import os
import json
import threading
from typing import Dict, List, Any
from datetime import datetime

MEM_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data", "long_term_memory.json")
MEM_FILE_BACKUP = os.path.join(os.path.dirname(MEM_FILE), "long_term_memory_backup_{}.json".format(datetime.now().strftime("%Y%m%d_%H%M%S")))

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
                        if isinstance(loaded_data, dict):
                            # Merge to ensure keys exist
                            for k in self.data.keys():
                                if k in loaded_data and isinstance(loaded_data[k], list):
                                    self.data[k] = loaded_data[k]
                except (json.JSONDecodeError, TypeError) as e:
                    # Try loading from backup if main file is corrupted
                    print(f"[Memory] Failed to load long term memory: {e}. Attempting backup...")
                    self._load_backup()

    def _load_backup(self):
        """Attempt to load from the most recent backup"""
        backup_files = sorted([f for f in os.listdir(os.path.dirname(MEM_FILE)) 
                             if f.startswith("long_term_memory_backup_")],
                            reverse=True)
        for backup_file in backup_files:
            try:
                with open(os.path.join(os.path.dirname(MEM_FILE), backup_file), 
                         "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        # Merge to ensure keys exist
                        for k in self.data.keys():
                            if k in loaded_data and isinstance(loaded_data[k], list):
                                self.data[k] = loaded_data[k]
                        print(f"[Memory] Successfully loaded from backup: {backup_file}")
                        return
            except Exception as e:
                print(f"[Memory] Failed to load backup {backup_file}: {e}")
        print("[Memory] No valid backups found. Using fresh memory.")

    def _save(self):
        self._ensure_dir()
        with self._lock:
            try:
                # Create backup before saving
                if os.path.exists(MEM_FILE):
                    os.rename(MEM_FILE, MEM_FILE_BACKUP)
                
                # Save new file
                with open(MEM_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[Memory] Failed to save long term memory: {e}")
                # Try to restore backup if save failed
                if os.path.exists(MEM_FILE_BACKUP):
                    try:
                        os.rename(MEM_FILE_BACKUP, MEM_FILE)
                        print("[Memory] Restored previous backup due to save failure")
                    except Exception as e:
                        print(f"[Memory] Failed to restore backup: {e}")

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

    def update_memory(self, category: str, index: int, new_content: str) -> bool:
        """Update an existing memory at a specific index."""
        if category not in self.data or index < 0 or index >= len(self.data[category]):
            return False
        
        content_clean = new_content.strip()
        if not content_clean:
            return self.delete_memory(category, index)
            
        with self._lock:
            self.data[category][index] = content_clean
            
        self._save()
        return True

    def delete_memory(self, category: str, index: int) -> bool:
        """Delete a memory at a specific index."""
        if category not in self.data or index < 0 or index >= len(self.data[category]):
            return False
            
        with self._lock:
            self.data[category].pop(index)
            
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
