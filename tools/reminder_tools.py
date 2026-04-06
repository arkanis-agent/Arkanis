import os
import json
import uuid
import datetime
import fcntl
import shutil
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

MAX_BACKUP_COUNT = 5
MAX_BACKUP_SIZE_MB = 100

class LockManager:
    """Singleton-safe File Lock Manager to prevent race conditions."""
    _instance = None
    _lock_path = REMINDERS_LOCK

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # Create lock file atomically
        if not os.path.exists(self._lock_path):
            os.mknod(self._lock_path) if hasattr(os, 'mknod') else open(self._lock_path, 'w').close()
        self._lock_file = None

    def acquire_read_lock(self):
        """Acquire shared read lock (prevents TOCTOU)."""
        self._lock_file = open(self._lock_path, 'r+b')
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_SH)

    def acquire_write_lock(self):
        """Acquire exclusive write lock."""
        self._lock_file = open(self._lock_path, 'r+b')
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)

    def release_lock(self):
        if self._lock_file:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None


def _clean_old_backups():
    """Keep only last MAX_BACKUP_COUNT backups with size limit."""
    if not os.path.exists(REMINDERS_BACKUP):
        return
    
    try:
        backups = sorted(
            [f for f in os.listdir('data') if f.startswith('reminders.json.bak')],
            reverse=True
        )
        
        while len(backups) > MAX_BACKUP_COUNT:
            oldest = os.path.join('data', backups[-1])
            os.remove(oldest)
            
        # Cleanup too large backup
        import psutil
        total_size = sum(
            os.path.getsize(os.path.join('data', f))
            for f in os.listdir('data')
            if f.startswith('reminders.json.bak')
        )
        
        if total_size > MAX_BACKUP_SIZE_MB * 1024 * 1024 and len(backups) > 1:
            os.remove(os.path.join('data', backups[-1]))
    except Exception as e:
        logger.warning(f"Backup cleanup failed: {e}")


def _get_sanitized_description(description: str) -> str:
    """Sanitize description to prevent injection and remove dangerous characters."""
    if not description:
        return ""
    safe = description.replace("\\", "\\\\").replace("\n", " ").replace("\r", " ")
    return safe.strip()[:200]

def _create_backup() -> bool:
    """Create a backup of the reminders file before modification."""
    try:
        if os.path.exists(REMINDERS_FILE):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{REMINDERS_BACKUP}.{timestamp}"
            shutil.copy2(REMINDERS_FILE, backup_name)
            _clean_old_backups()
        return True
    except Exception as e:
        logger.warning(f"Backup creation failed: {e}")
        return False

def _recover_from_backup() -> bool:
    """Attempt to recover from backup if current file is corrupted."""
    try:
        # Find most recent backup
        backups = sorted(
            [f for f in os.listdir('data') if f.startswith('reminders.json.bak')],
            reverse=True
        )
        
        if backups:
            backup_path = os.path.join('data', backups[0])
            shutil.copy2(backup_path, REMINDERS_FILE)
            logger.info(f"Recovered reminders from backup: {backups[0]}")
            return True
            
        logger.error("No backup available for recovery")
        return False
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        return False

def _load_reminders() -> Dict[str, Any]:
    """Load reminders with atomic file lock and recovery mechanism."""
    lock_manager = LockManager()
    lock_manager.acquire_read_lock()

    data = {}
    
    if not os.path.exists(REMINDERS_FILE):
        lock_manager.release_lock()
        return data
    
    try:
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            logger.error("Reminders JSON corrupted, attempting recovery...")
            if not _recover_from_backup():
                lock_manager.release_lock()
                return {}
        except Exception as e:
            logger.error(f"Failed to load reminders: {e}")
            lock_manager.release_lock()
            return {}
    finally:
        lock_manager.release_lock()
    
    return data if isinstance(data, dict) else {}

def _save_reminders(data: Dict[str, Any]) -> bool:
    """Save reminders with file lock, backup, and atomic write."""
    lock_manager = LockManager()
    lock_manager.acquire_write_lock()
    
    temp_file = REMINDERS_FILE + ".tmp"
    
    try:
        # Check validity of data first
        if not isinstance(data, dict):
            return False
            
        # Create backup before saving (only when data differs significantly)
        if os.path.exists(REMINDERS_FILE):
            _create_backup()
        
        # Write to temp file first (atomic operation)
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False, default=str)
        
        # Rename temp to actual file (atomic on most filesystems)
        os.replace(temp_file, REMINDERS_FILE)
        return True
        
    except Exception as e:
        logger.error(f"Failed to save reminders: {e}")
        # Cleanup temp file on failure
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
    finally:
        lock_manager.release_lock()

class CreateReminderTool(BaseTool):
    @property
    def name(self) -> str: return "create_reminder"
    
    @property
    def description(self) -> str: 
        return "Schedules a reminder to send a notification to the user in the future."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "description": "O que deve ser lembrado (máx 200 caracteres, sem quebras de linha).",
            "trigger_time": "Quando ativar o lembrete. FORMATO OBRIGATÓRIO: 'YYYY-MM-DD HH:MM:SS' (ex: '2026-04-05 20:30:00')."
        }
        
    def execute(self, **kwargs) -> str:
        description = kwargs.get("description", "").strip()
        description = _get_sanitized_description(description)
        time_str = kwargs.get("trigger_time", "").strip()
        
        if not description or not time_str:
            return "Request failed: description e trigger_time são campos obrigatórios."
            
        try:
            dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            
            if dt <= now:
                return "Request failed: trigger_time deve ser no futuro."
            
            reminders = _load_reminders()
            
            r_id = str(uuid.uuid4())[:8]
            reminders[r_id] = {
                "id": r_id,
                "description": description,
                "trigger_time": time_str,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pending"
            }
            
            if _save_reminders(reminders):
                return f"Success! Reminder scheduled for {time_str} (ID: {r_id})."
            return "Request failed: could not save reminder."
                
        except ValueError:
            return "Request failed: trigger_time deve estar no formato 'YYYY-MM-DD HH:MM:SS'."
        except Exception:
            return "Request failed: an unexpected error occurred."

class ListRemindersTool(BaseTool):
    @property
    def name(self) -> str: return "list_reminders"
    
    @property
    def description(self) -> str: 
        return "Lists all pending reminders and their scheduled times."
        
    @property
    def arguments(self) -> Dict[str, str]: return {}
        
    def execute(self, **kwargs) -> str:
        reminders = _load_reminders()
        pending = [r for r in reminders.values() if r.get("status") == "pending"]
        
        if not pending:
            return "No pending reminders scheduled."
            
        pending.sort(key=lambda x: x.get("trigger_time", ""))
        
        result = "AGENDA & REMINDERS:\n"
        for r in pending:
            result += f"- [{r['id']}] {r['trigger_time']} => {r['description']}\n"
            
        return result

class DeleteReminderTool(BaseTool):
    @property
    def name(self) -> str: return "delete_reminder"
    
    @property
    def description(self) -> str: 
        return "Deletes an existing scheduled reminder by its ID."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {"reminder_id": "O ID do lembrete a ser deletado."}
        
    def execute(self, **kwargs) -> str:
        r_id = kwargs.get("reminder_id", "").strip()
        if not r_id:
            return "Request failed: reminder_id is required."
            
        reminders = _load_reminders()
        if r_id in reminders:
            del reminders[r_id]
            if _save_reminders(reminders):
                return "Reminder successfully canceled."
            return "Request failed: could not save database after deletion."
        
        return "Request failed: No reminder found with that ID."

# Register tools
registry.register(CreateReminderTool())
registry.register(ListRemindersTool())
registry.register(DeleteReminderTool())

import atexit
atexit.register(LockManager().release_lock)