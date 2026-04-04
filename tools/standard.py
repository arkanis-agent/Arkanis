from typing import Any, Dict
from tools.base_tool import BaseTool
import json

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
            "content": "The string content to write."
        }

    def execute(self, **kwargs) -> str:
        # LLMs often guess 'file_path' instead of 'path', so we accept both safely.
        path = kwargs.get("path") or kwargs.get("file_path")
        content = kwargs.get("content", "")
        
        if not path:
            return "Error: Missing file path."
        
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {path}."
        except Exception as e:
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
            return "Error: Missing file path."
        
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
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
        return "true" if os.path.exists(path) else "false"


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
            "path": "The directory path (default: '.')"
        }

    def execute(self, **kwargs) -> str:
        path = kwargs.get("path", ".")
        try:
            items = os.listdir(path)
            return json.dumps(items)
        except Exception as e:
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
        return f"Message displayed: {message}"

# Registration logic
from tools.registry import registry
registry.register(WriteFileTool())
registry.register(ReadFileTool())
registry.register(FileExistsTool())
registry.register(ListFilesTool())
registry.register(PrintTool())
