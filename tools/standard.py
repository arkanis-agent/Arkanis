from typing import Any, Dict, Optional
from tools.base_tool import BaseTool
import json
import os
import logging
from pathlib import Path

# Configuração segura de diretório
SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWED_BASE_DIR = (SCRIPT_DIR.parent / "safe_workspace").resolve()
logger = logging.getLogger(__name__)

# Limite seguro para conteúdo escrito (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

def is_safe_path(path: str) -> bool:
    """Valida se o path está dentro do diretório permitido para evitar path traversal."""
    try:
        absolute_path = Path(path).resolve()
        base_path = Path(ALLOWED_BASE_DIR).resolve()
        
        # Verifica se o path base é subdiretório do permitido
        try:
            return str(absolute_path).startswith(str(base_path) + str(os.sep)) or absolute_path == base_path
        except (ValueError, TypeError):
            return False
            
        return absolute_path.is_relative_to(base_path) if hasattr(absolute_path, 'is_relative_to') else True
        
    except (OSError, ValueError) as e:
        logger.warning(f"is_safe_path error for '{path}': {e}")
        return False

class WriteFileTool(BaseTool):
    """A tool to write text to a file."""
    
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write code, HTML, CSS or text to a file. USE THIS to build systems, pages and apps."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "path": "The destination file path.",
            "content": "The string content to write (max 5MB)."
        }

    def execute(self, **kwargs) -> str:
        path = kwargs.get("path") or kwargs.get("file_path")
        content = kwargs.get("content", "")
        
        if not path:
            return "Error: Missing file path parameter."
        
        if not is_safe_path(path):
            return "Error: Path outside allowed directory."
        
        # Valida tamanho do conteúdo
        if content and len(content) > MAX_FILE_SIZE:
            return f"Error: Content size exceeds {MAX_FILE_SIZE // 1024 // 1024}MB limit."
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"File written successfully: {path}")
            return f"Successfully wrote to {path}."
        except PermissionError:
            logger.error(f"Permission denied writing to {path}")
            return "Error: Permission denied. Cannot write to this location."
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return f"Error writing file: {str(e)}"


class ReadFileTool(BaseTool):
    """A tool to read text from a file."""
    
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the content of a text file."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "path": "The path of the file to read."
        }

    def execute(self, **kwargs) -> str:
        path = kwargs.get("path") or kwargs.get("file_path")
        if not path:
            return "Error: Missing file path parameter."
        
        if not is_safe_path(path):
            return "Error: Path outside allowed directory."
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"File read successfully: {path}")
            return content
        except PermissionError:
            return "Error: Permission denied. Cannot read this file."
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return f"Error reading file: {str(e)}"


class FileExistsTool(BaseTool):
    """A tool to check if a file exists."""
    
    @property
    def name(self) -> str:
        return "file_exists"

    @property
    def description(self) -> str:
        return "Check if a file or directory exists at the given path."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "path": "The path to check."
        }

    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        if not path:
            return "false"
        
        if not is_safe_path(path):
            return "false"
        
        exists = os.path.exists(path)
        return "true" if exists else "false"


class ListFilesTool(BaseTool):
    """A tool to list files in a directory."""
    
    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files and directories in a path (default: current directory)."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "path": "The directory path (default: ').'")
        }

    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", ".")
        
        if not is_safe_path(path):
            return "Error: Path outside allowed directory."
        
        try:
            if not os.path.isdir(path):
                return "Error: Path is not a valid directory."
            items = sorted(os.listdir(path))
            result = json.dumps(items, indent=2)
            logger.info(f"Listed {len(items)} items in {path}")
            return result
        except PermissionError:
            return "Error: Permission denied. Cannot list directory."
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return f"Error listing files: {str(e)}"


class PrintTool(BaseTool):
    """A tool to display a message."""
    
    @property
    def name(self) -> str:
        return "print_message"

    @property
    def description(self) -> str:
        return "Display a message in the console."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "message": "The message to display."
        }

    def execute(self, **kwargs) -> str:
        message = kwargs.get("message", "No message provided.")
        print(f"\n[Agent Output] {message}")
        logger.debug(f"Print message: {message}")
        return f"Message displayed: {message}"


# Registration logic
from tools.registry import registry
registry.register(WriteFileTool())
registry.register(ReadFileTool())
registry.register(FileExistsTool())
registry.register(ListFilesTool())
registry.register(PrintTool())