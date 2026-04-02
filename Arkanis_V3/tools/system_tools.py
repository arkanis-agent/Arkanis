import os
import datetime
import json
from typing import Dict, Any, List
from tools.base_tool import BaseTool
from tools.registry import registry
from core.agent_bus import agent_bus
from core.goal_manager import goal_manager
from modules.memory.long_term import long_term_memory

def is_safe_path(path: str) -> bool:
    """Basic security check to prevent access to sensitive system files."""
    if ".." in path:
        return False
    # Block sensitive system paths
    blocked = ["/etc", "/proc", "/sys", "/root", "/var/shadow", "/boot"]
    resolved = os.path.abspath(path)
    for b in blocked:
        if resolved.startswith(b):
            return False
    return True

class GetCurrentDateTimeTool(BaseTool):
    """A tool to get the current system date and time."""
    @property
    def name(self) -> str: return "get_current_datetime"
    @property
    def description(self) -> str: return "Returns the current system date and time."
    @property
    def arguments(self) -> Dict[str, str]: return {}
    def execute(self, **kwargs) -> str:
        now = datetime.datetime.now()
        return json.dumps({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "datetime": now.strftime("%Y-%m-%d %H:%M")
        })

class ListFilesTool(BaseTool):
    """A tool to list files in a directory."""
    @property
    def name(self) -> str: return "list_files"
    @property
    def description(self) -> str:
        return "List all files and directories in a given path. Use path='/home/diego/Área de trabalho' for the Ubuntu Desktop, or path='.' for the agent's current directory."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Directory path to list. Defaults to current directory if not provided."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", ".")
        if not is_safe_path(path):
            return "Error: Access to this path is not permitted."
        try:
            files = os.listdir(path)
            return json.dumps(files)
        except Exception as e:
            return f"Error listing files: {str(e)}"

class ReadFileTool(BaseTool):
    """A tool to read the contents of a file."""
    @property
    def name(self) -> str: return "read_file"
    @property
    def description(self) -> str: return "Read and return the content of a specific file."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "The path to the file to read."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        if not path: return "Error: Missing file path."
        if not is_safe_path(path): return "Error: Path traversal or absolute path violation detected."
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

class FileExistsTool(BaseTool):
    """A tool to check if a file or directory exists."""
    @property
    def name(self) -> str: return "file_exists"
    @property
    def description(self) -> str: return "Checks if a specific file path exists."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "The path to check existence for."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        if not path: return "Error: Missing file path."
        if not is_safe_path(path): return "Error: Path traversal or absolute path violation detected."
        exists = os.path.exists(path)
        return "true" if exists else "false"

class WriteFileTool(BaseTool):
    """A tool to write content to a file (creates or OVERWRITES existing code/files). Designed for dev_agent."""
    @property
    def name(self) -> str: return "write_file"
    @property
    def description(self) -> str: return "PRIMARY TOOL for building apps and systems. Creates or OVERWRITES a file with the provided code, HTML, or text."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "The path to the file.", "content": "The string content to write."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        content = kwargs.get("content")
        if not path or content is None: return "Error: Missing parameters."
        if not is_safe_path(path): return "Error: Path traversal or absolute path violation detected. Only write inside your CWD."
        
        try:
            # Create subdirs if they don't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            agent_bus.broadcast_message("system", f"[SECURITY LOG] dev_agent modified file: {path}")
            return f"Successfully wrote to {path}."
        except Exception as e:
            return f"Error writing file: {str(e)}"

class CreateDirectoryTool(BaseTool):
    """A tool to create a directory/folder."""
    @property
    def name(self) -> str: return "create_directory"
    @property
    def description(self) -> str: return "Creates a new directory/folder. USE THIS to organize project structures (src, css, js) before writing files."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "The path to the new directory."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        if not path: return "Error: Missing directory path."
        if not is_safe_path(path): return "Error: Path violation."
        try:
            os.makedirs(path, exist_ok=True)
            return f"Successfully created directory: {path}"
        except Exception as e:
            return f"Error creating directory: {str(e)}"

class DeleteItemTool(BaseTool):
    """A tool to delete a file or directory."""
    @property
    def name(self) -> str: return "delete_item"
    @property
    def description(self) -> str: return "Deletes a file or directory (recursively if it is a directory)."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "The path to delete."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        if not path: return "Error: Missing path."
        if not is_safe_path(path): return "Error: Path violation."
        if not os.path.exists(path): return f"Error: {path} does not exist."
        try:
            import shutil
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return f"Successfully deleted {path}."
        except Exception as e:
            return f"Error deleting {path}: {str(e)}"

class MoveItemTool(BaseTool):
    """A tool to rename or move a file or directory."""
    @property
    def name(self) -> str: return "move_item"
    @property
    def description(self) -> str: return "Renames or moves a file or directory."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"source": "The current path.", "destination": "The new path."}
    def execute(self, **kwargs) -> str:
        src = kwargs.get("source")
        dst = kwargs.get("destination")
        if not src or not dst: return "Error: Missing source or destination."
        if not is_safe_path(src) or not is_safe_path(dst): return "Error: Path violation."
        try:
            import shutil
            shutil.move(src, dst)
            return f"Successfully moved/renamed {src} to {dst}."
        except Exception as e:
            return f"Error moving {src}: {str(e)}"

class SendMessageTool(BaseTool):
    """Envia uma mensagem direta para outro agente pelo ID."""
    @property
    def name(self) -> str: return "send_message"
    @property
    def description(self) -> str: return "Send a direct message to a specific agent to collaborate."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"from_agent": "Your agent ID or name.", "to_agent": "The target agent ID.", "content": "Message content"}
    def execute(self, **kwargs) -> str:
        frm = kwargs.get("from_agent", "unknown")
        to = kwargs.get("to_agent")
        content = kwargs.get("content")
        if not to or not content: return "Error: Missing parameters."
        success = agent_bus.send_message(frm, to, content)
        return f"Message sent to {to}." if success else f"Error: Agent {to} not found."

class BroadcastMessageTool(BaseTool):
    """Envia uma mensagem para todos os agentes ativos no bus."""
    @property
    def name(self) -> str: return "broadcast_message"
    @property
    def description(self) -> str: return "Broadcast a message to all active agents."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"from_agent": "Your agent ID or name.", "content": "Message content"}
    def execute(self, **kwargs) -> str:
        frm = kwargs.get("from_agent", "unknown")
        content = kwargs.get("content")
        if not content: return "Error: Missing content."
        agent_bus.broadcast_message(frm, content)
        return "Broadcast message sent to all agents."

class SaveMemoryTool(BaseTool):
    """Salva informações importantes na memória de longo prazo do sistema (compartilhada)."""
    @property
    def name(self) -> str: return "save_memory"
    @property
    def description(self) -> str: return "Saves important facts, user preferences, or recurrent tasks to the long-term memory."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"category": "One of: 'preferences', 'facts', 'recurrent_tasks'", "content": "The information to save."}
    def execute(self, **kwargs) -> str:
        cat = kwargs.get("category")
        content = kwargs.get("content")
        if not cat or not content: return "Error: Missing parameters."
        if cat not in ["preferences", "facts", "recurrent_tasks"]:
            return "Error: Invalid memory category. Must be 'preferences', 'facts', or 'recurrent_tasks'."
        long_term_memory.add_memory(cat, content)
        return f"Successfully saved to {cat}."

class UpdateGoalProgressTool(BaseTool):
    """Atualiza o progresso de um objetivo global no sistema."""
    @property
    def name(self) -> str: return "update_goal_progress"
    @property
    def description(self) -> str: return "Updates the progress of a given global goal_id your agent is attached to."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"goal_id": "The target goal ID.", "progress": "Integer from 0 to 100", "note": "Status note"}
    def execute(self, **kwargs) -> str:
        gid = kwargs.get("goal_id")
        prog = kwargs.get("progress")
        note = kwargs.get("note", "")
        if not gid or prog is None: return "Error: Missing parameters."
        try:
            goal_manager.update_progress(gid, int(prog), note)
            return f"Goal {gid} progress updated to {prog}%."
        except Exception as e:
            return f"Error updating goal: {e}"

# Auto-registration
registry.register(GetCurrentDateTimeTool())
registry.register(ListFilesTool())
registry.register(ReadFileTool())
registry.register(WriteFileTool())
registry.register(CreateDirectoryTool())
registry.register(DeleteItemTool())
registry.register(MoveItemTool())
registry.register(FileExistsTool())
registry.register(SendMessageTool())
registry.register(BroadcastMessageTool())
registry.register(SaveMemoryTool())
registry.register(UpdateGoalProgressTool())
