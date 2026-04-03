from typing import Dict, Optional, Type
from .base_tool import BaseTool

class ToolRegistry:
    """
    A singleton class to manage the registration and discovery of tools.
    """
    _instance = None
    _tools: Dict[str, BaseTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, tool: BaseTool):
        """Register a tool instance."""
        self._tools[tool.name] = tool
        print(f"[Registry] Tool registered: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        """Return a dictionary of tool names and their descriptions."""
        return {name: tool.description for name, tool in self._tools.items()}

    def get_all_tools(self):
        """Return a list of all registered tool instances."""
        return list(self._tools.values())

# Global registry instance
registry = ToolRegistry()
