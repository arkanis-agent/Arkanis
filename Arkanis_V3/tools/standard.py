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
        return "Write content to a specified file path."

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
registry.register(PrintTool())
