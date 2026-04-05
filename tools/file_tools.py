import os
import shutil
import json
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

def get_desktop_path() -> str:
    user_home = os.path.expanduser("~")
    # try reading ~/.config/user-dirs.dirs for locale-aware desktop path
    config_path = os.path.join(user_home, ".config", "user-dirs.dirs")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("XDG_DESKTOP_DIR="):
                        path = line.split("=")[1].strip().strip('"')
                        return path.replace("$HOME", user_home)
        except Exception:
            pass
    
    # Fallbacks in case config doesn't exist
    for cand in ["Área de trabalho", "Desktop", "Área de Trabalho", "Escritorio", 
                 "OneDrive/Desktop", "OneDrive/Área de trabalho", 
                 "OneDrive/Área de Trabalho", "OneDrive/Escritorio"]:
        p = os.path.join(user_home, *cand.split("/"))
        if os.path.exists(p):
            return p
    return os.path.join(user_home, "Desktop")


class GetDesktopDirectoryTool(BaseTool):
    @property
    def name(self) -> str: return "get_desktop_directory"
    @property
    def description(self) -> str: return "Returns the absolute path to the current user's Desktop / Área de Trabalho directory."
    @property
    def arguments(self) -> Dict[str, str]: return {}
    def execute(self, **kwargs) -> str:
        return get_desktop_path()


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
        if path.upper() == "DESKTOP":
            path = get_desktop_path()
        else:
            path = os.path.expanduser(path)
            
        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."
        if not os.path.isdir(path):
            return f"Error: Path '{path}' is not a directory."
            
        items = []
        try:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                item_type = "DIR" if os.path.isdir(full_path) else ("FILE" if os.path.isfile(full_path) else "OTHER")
                size = os.path.getsize(full_path) if item_type == "FILE" else 0
                items.append({"name": item, "type": item_type, "size_bytes": size})
            return json.dumps(items, ensure_ascii=False)
        except Exception as e:
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
        path = os.path.expanduser(kwargs.get("path", ""))
        path = path.replace("Área de Trabalho", "Área de trabalho").replace("Desktop", "Área de trabalho")
        try:
            os.makedirs(path, exist_ok=True)
            return f"Directory '{path}' ensured to exist."
        except Exception as e:
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
        path = os.path.expanduser(kwargs.get("path", ""))
        if not os.path.exists(path):
            return "Error: Path does not exist."
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            return f"Successfully deleted '{path}'."
        except Exception as e:
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
        path = os.path.expanduser(kwargs.get("path", ""))
        target = kwargs.get("target", "")
        replacement = kwargs.get("replacement", "")
        
        if not os.path.exists(path):
            return "Error: File does not exist."
        if not os.path.isfile(path):
            return "Error: Path is not a file."
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if target not in content:
                return "Error: Target text not found in the file! String matching must be exact."
            new_content = content.replace(target, replacement)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully replaced occurrences of the text in '{path}'."
        except Exception as e:
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
        path = os.path.expanduser(kwargs.get("path", ""))
        path = path.replace("Área de Trabalho", "Área de trabalho").replace("Desktop", "Área de trabalho")
        content = kwargs.get("content", "")
        
        try:
            # Ensure folder exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to '{path}'."
        except Exception as e:
            return f"Failed to write to file: {str(e)}"

# Register all tools
registry.register(GetDesktopDirectoryTool())
registry.register(ListDirectoryTool())
registry.register(CreateDirectoryTool())
registry.register(RemoveItemTool())
registry.register(ReplaceFileContentTool())
registry.register(WriteFileTool())
