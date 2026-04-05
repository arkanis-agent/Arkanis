import os
import json
import uuid
import datetime
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

REMINDERS_FILE = os.path.join("data", "reminders.json")

def _load_reminders() -> Dict[str, Any]:
    if not os.path.exists(REMINDERS_FILE):
        return {}
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load reminders: {e}")
        return {}

def _save_reminders(data: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save reminders: {e}")
        return False


class CreateReminderTool(BaseTool):
    @property
    def name(self) -> str: return "create_reminder"
    
    @property
    def description(self) -> str: 
        return "Schedules a reminder to send a notification to the user in the future."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "description": "What to remind the user about (e.g. 'Tomar o remédio de pressão').",
            "trigger_time": "When to trigger the reminder. EXACT FORMAT REQUIRED: 'YYYY-MM-DD HH:MM:SS' in local time (e.g., '2026-04-05 20:30:00')."
        }
        
    def execute(self, **kwargs) -> str:
        description = kwargs.get("description", "").strip()
        time_str = kwargs.get("trigger_time", "").strip()
        
        if not description or not time_str:
            return "Error: description and trigger_time are required."
            
        try:
            # Validate timestamp format
            dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            
            if dt <= now:
                return f"Error: trigger_time '{time_str}' is in the past! Current time is {now.strftime('%Y-%m-%d %H:%M:%S')}."
            
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
                return f"Success! Reminder '{description}' scheduled for {time_str} (ID: {r_id})."
            else:
                return "Failed to save the reminder in the database."
                
        except ValueError:
            return "Error: trigger_time must be exactly in 'YYYY-MM-DD HH:MM:SS' format."
        except Exception as e:
            return f"Error setting reminder: {str(e)}"


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
            return "There are no pending reminders scheduled."
            
        # Sort by trigger_time
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
        return {"reminder_id": "The ID of the reminder to delete."}
        
    def execute(self, **kwargs) -> str:
        r_id = kwargs.get("reminder_id", "").strip()
        if not r_id:
            return "Error: reminder_id is required."
            
        reminders = _load_reminders()
        if r_id in reminders:
            del reminders[r_id]
            if _save_reminders(reminders):
                return f"Reminder {r_id} was successfully canceled."
            return "Failed to save database after deletion."
        
        return f"Error: No reminder found with ID '{r_id}'."

# Register tools
try:
    if "create_reminder" in registry._tools:
        del registry._tools["create_reminder"]
    if "list_reminders" in registry._tools:
        del registry._tools["list_reminders"]
    if "delete_reminder" in registry._tools:
        del registry._tools["delete_reminder"]
except Exception:
    pass

registry.register(CreateReminderTool())
registry.register(ListRemindersTool())
registry.register(DeleteReminderTool())
