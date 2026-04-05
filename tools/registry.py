from typing import Dict, Optional, List
import importlib
from .base_tool import BaseTool

class ToolRegistry:
    """
    ARKANIS V3.1 - Managed Tool Registry (Lazy Loading)
    A singleton class to manage the registration and discovery of tools.
    Supports lazy loading to reduce boot-up time and memory footprint.
    """
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    
    # Mapping of tool names to their containing modules for lazy loading
    _LAZY_MAP = {
        "autonomous_browser": "tools.browser_tools",
        "deep_researcher": "tools.research_tools",
        "quick_web_search": "tools.research_tools",
        "llm_code_executor": "tools.ai_tools",
        "audio_recorder": "tools.audio_tools",
        "transcriber": "tools.audio_tools",
        "network_scanner": "tools.network_tools",
        "port_scanner": "tools.network_tools",
        "system_monitor": "tools.system_tools",
        "process_killer": "tools.system_tools",
        "task_manager": "tools.monitoring_tools",
        "terminal_access": "tools.standard",
        "swarm_coordinator": "tools.swarm_tool",
        "file_op": "tools.file_tools",
        "read_file": "tools.file_tools",
        "write_file": "tools.file_tools",
        "list_files": "tools.file_tools",
        "dev_suggestion_tool": "tools.dev_tools",
        "telegram_notifier": "tools.telegram_tools",
        "save_credential": "tools.vault_tools",
        "get_credential": "tools.vault_tools",
        "create_reminder": "tools.reminder_tools",
        "list_reminders": "tools.reminder_tools",
        "delete_reminder": "tools.reminder_tools"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, tool: BaseTool):
        """Register a tool instance."""
        self._tools[tool.name] = tool
        # print(f"[Registry] Plugin Active: {tool.name}") # Silent for performance

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name, loading it lazily if necessary."""
        # 1. Check if already loaded
        if name in self._tools:
            return self._tools[name]
        
        # 2. Check if we know where it is
        module_path = self._LAZY_MAP.get(name)
        if module_path:
            try:
                # print(f"[Registry] Lazy loading plugin: {module_path}...")
                importlib.import_module(module_path)
                return self._tools.get(name)
            except Exception as e:
                from core.logger import logger
                logger.error(f"Failed to lazy load tool '{name}': {str(e)}")
        
        return None

    def list_tools(self) -> Dict[str, str]:
        """Return a dictionary of tool names and their descriptions."""
        # Note: In lazy mode, descriptions might not be available until loaded.
        # But for the Router, we usually need the names first.
        # We ensure standard tools are pre-loaded or use the names from the map.
        tools_list = {name: "Plugin (Pendente carregar)" for name in self._LAZY_MAP.keys()}
        # Update with actual descriptions for loaded tools
        for name, tool in self._tools.items():
            tools_list[name] = tool.description
        return tools_list

    def get_all_tools(self) -> List[BaseTool]:
        """Forces loading of all known tools and returns them."""
        for name, mod in self._LAZY_MAP.items():
            if name not in self._tools:
                self.get_tool(name)
        return list(self._tools.values())

# Global registry instance
registry = ToolRegistry()
