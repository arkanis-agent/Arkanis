import os
import shutil
import json
from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

# Security settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB default
SAFE_WORK_DIR = os.path.expanduser("~")  # Default safe directory

def _validate_path(path: str, for_writing: bool = False) -> Optional[str]:
    """Securely validate and normalize a file path."""
    if not path or not isinstance(path, str):
        return None
    
    path = os.path.expanduser(path)
    
    # Prevent path traversal
    normalized = os.path.normpath(path)
    if normalized.startswith('..') or normalized.startswith('/'):
        return None
    
    # For writing, ensure path is within home directory
    if for_writing:
        real_path = os.path.realpath(normalized)
        if not real_path.startswith(SAFE_WORK_DIR):
            return None
    
    return normalized

def get_desktop_path() -> str:
    user_home = os.path.expanduser("~")
    config_path = os.path.join(user_home, ".config", "user-dirs.dirs")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("XDG_DESKTOP_DIR="):
                        path = line.split("=", 1)[1].strip().strip('"')
                        return path.replace("$HOME", user_home)
        except Exception as e:
            logger.warning(f"Failed to read desktop config: {e}")
            pass
    
    fallbacks = ["Área de trabalho", "Desktop", "Área de Trabalho", "Escritorio"]
    for cand in fallbacks:
        p = os.path.join(user_home, *cand.split("/"))
        if os.path.exists(p) and os.path.isdir(p):
            return p
    
    desktop_path = os.path.join(user_home, "Desktop")
    logger.debug(f"Using fallback desktop path: {desktop_path}")
    return desktop_path


class GetDesktopDirectoryTool(BaseTool):
    @property
    def name(self) -> str: return "get_desktop_directory"
    @property
    def description(self) -> str: return "Returns the absolute path to the current user's Desktop / Área de Trabalho directory."
    @property
    def arguments(self) -> Dict[str, str]: return {}
    def execute(self, **kwargs) -> str:
        try:
            return get_desktop_path()
        except Exception as e:
            logger.error(f"get_desktop_directory failed: {e}")
            return f"Error retrieving desktop path: {str(e)}"


class ListDirectoryTool(BaseTool):
    @property
    def name(self) -> str: return "list_directory"
    @property
    def description(self) -> str: return "Lists all files and folders in a specified directory. Use 'DESKTOP' as path to list the desktop."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Directory path to list."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", "")
        try:
            if path and path.upper() == "DESKTOP":
                path = get_desktop_path()
            else:
                validated = _validate_path(path)
                if not validated:
                    return "Error: Invalid or unsafe path provided."
                path = validated
        except Exception as e:
            logger.error(f"Directory listing error: {e}")
            return f"Error processing path: {str(e)}"
            
        expanded_path = os.path.expanduser(path)
        if not os.path.exists(expanded_path):
            return f"Error: Path '{expanded_path}' does not exist."
        if not os.path.isdir(expanded_path):
            return f"Error: Path '{expanded_path}' is not a directory."
            
        items = []
        try:
            for item in os.listdir(expanded_path):
                full_path = os.path.join(expanded_path, item)
                item_type = "DIR" if os.path.isdir(full_path) else ("FILE" if os.path.isfile(full_path) else "OTHER")
                size = os.path.getsize(full_path) if item_type == "FILE" else 0
                items.append({"name": item, "type": item_type, "size_bytes": size})
            return json.dumps(items, ensure_ascii=False)
        except PermissionError:
            return "Error: Access denied to directory."
        except Exception as e:
            logger.error(f"ListDirectoryTool failed: {e}")
            return f"Error reading directory: {str(e)}"


class CreateDirectoryTool(BaseTool):
    @property
    def name(self) -> str: return "create_directory"
    @property
    def description(self) -> str: return "Creates a new directory (and intermediate directories if necessary)."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Directory path to create. Use ~ for home."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", "")
        validated = _validate_path(path, for_writing=True)
        if not validated:
            return "Error: Invalid or unsafe path provided."
        try:
            os.makedirs(validated, exist_ok=True)
            return f"Directory '{validated}' ensured to exist."
        except PermissionError:
            return f"Failed: Permission denied for path: {validated}."
        except Exception as e:
            logger.error(f"CreateDirectoryTool failed: {e}")
            return f"Failed to create directory: {str(e)}"


class RemoveItemTool(BaseTool):
    @property
    def name(self) -> str: return "remove_item"
    @property
    def description(self) -> str: return "Deletes a file or directory permanently. USE WITH EXTREME CAUTION."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Path to the file or directory to delete."}
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", "")
        validated = _validate_path(path)
        if not validated:
            return "Error: Invalid or unsafe path provided."
            
        expanded_path = os.path.expanduser(path)
        if not os.path.exists(expanded_path):
            return "Error: Path does not exist."
        try:
            if os.path.isfile(expanded_path) or os.path.islink(expanded_path):
                os.remove(expanded_path)
                logger.info(f"Removed file: {expanded_path}")
            elif os.path.isdir(expanded_path):
                shutil.rmtree(expanded_path)
                logger.info(f"Removed directory: {expanded_path}")
            return f"Successfully deleted '{expanded_path}'."
        except PermissionError:
            return f"Error: Permission denied for '{expanded_path}'."
        except Exception as e:
            logger.error(f"RemoveItemTool failed: {e}")
            return f"Failed to delete item: {str(e)}"


class ReplaceFileContentTool(BaseTool):
    @property
    def name(self) -> str: return "replace_file_content"
    @property
    def description(self) -> str: return "Replaces exact occurrences of text inside a file with new text."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "path": "Path to the target file.",
            "target": "The exact current text to be removed/replaced.",
            "replacement": "The new text to insert in its place."
        }
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", "")
        target = kwargs.get("target", "")
        replacement = kwargs.get("replacement", "")
        validated = _validate_path(path)
        
        if not path:
            return "Error: Path is required."
        if not os.path.exists(path):
            return "Error: File does not exist."
        if not os.path.isfile(path):
            return "Error: Path is not a file."
        if not target:
            return "Error: Target text cannot be empty."
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if target not in content:
                return "Error: Target text not found in the file! String matching must be exact."
            new_content = content.replace(target, replacement)
            max_size_check = len(new_content.encode("utf-8")) <= MAX_FILE_SIZE
            if not max_size_check:
                return f"Error: New file content exceeds maximum size limit ({MAX_FILE_SIZE} bytes)."
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully replaced in '{path}'."
        except PermissionError:
            return f"Error: Permission denied for '{path}'."
        except Exception as e:
            logger.error(f"ReplaceFileContentTool failed: {e}")
            return f"Failed to modify file: {str(e)}"


class WriteFileTool(BaseTool):
    @property
    def name(self) -> str: return "write_file_content"
    @property
    def description(self) -> str: return "Overwrites or creates a file with the provided text content."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "path": "Path to the target file.",
            "content": "The full text content to write."
        }
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        validated = _validate_path(path)
        
        if not validated:
            return "Error: Invalid or unsafe path provided."
            
        try:
            dir_path = os.path.dirname(validated)
            if dir_path and dir_path not in ("", "."):
                os.makedirs(dir_path, exist_ok=True)
            file_size = len(content.encode("utf-8"))
            if file_size > MAX_FILE_SIZE:
                return f"Error: Content exceeds maximum size limit ({MAX_FILE_SIZE} bytes)."
            with open(validated, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"WriteFileTool success: {validated} ({file_size} bytes)")
            return f"Successfully wrote {file_size} characters to '{validated}'."
        except PermissionError:
            return f"Error: Permission denied for '{validated}'."
        except Exception as e:
            logger.error(f"WriteFileTool failed: {e}")
            return f"Failed to write to file: {str(e)}"


# Register all tools
registry.register(GetDesktopDirectoryTool())
registry.register(ListDirectoryTool())
registry.register(CreateDirectoryTool())
registry.register(RemoveItemTool())
registry.register(ReplaceFileContentTool())
registry.register(WriteFileTool())
