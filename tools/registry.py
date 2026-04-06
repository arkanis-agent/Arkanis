from typing import Dict, Optional, List, Callable
import importlib
import threading
from .base_tool import BaseTool
from typing import Final

class ToolRegistry:
    """
    ARKANIS V3.1 - Managed Tool Registry (Lazy Loading)
    Single instance to manage registration and discovery of tools.
    """
    _instance: Optional['ToolRegistry'] = None
    _tools: Dict[str, BaseTool] = {}
    _lock = threading.Lock()
    _lazy_callbacks: Dict[str, List[Callable]] = {}

    _LAZY_MAP: Final[Dict[str, str]] = {
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
        "delete_reminder": "tools.reminder_tools",
        "forge_agent": "tools.forge_agent_tool"
    }

    def __new__(cls) -> 'ToolRegistry':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._init_callbacks = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Registrar uma ferramenta."""
        with self._lock:
            self._tools[tool.name] = tool
            if not self._initialized:
                from core.logger import logger
                logger.info(f"Ferramenta Registrada: {tool.name}")

    def unregister(self, name: str) -> bool:
        """Remover uma ferramenta do registro."""
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                return True
            return False

    def on_lazy_load(self, tool_name: str, callback: Callable) -> None:
        """Register callback for when tool is lazily loaded."""
        with self._lock:
            self._lazy_callbacks.setdefault(tool_name, []).append(callback)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Recuperar ferramenta por nome, carregando se necessário."""
        if name in self._tools:
            return self._tools[name]

        with self._lock:
            if name in self._tools:
                return self._tools[name]

            if name not in self._LAZY_MAP:
                return None

            module_path = self._LAZY_MAP[name]
            try:
                imported_module = importlib.import_module(module_path)
                
                if not hasattr(imported_module, tool_registry_callback_name := "__register_tools__"):
                    raise AttributeError(f"Module {module_path} missing __register_tools__ hook")
                
                imported_module.__register_tools__()  

                if name in self._tools:
                    callback_list = self._lazy_callbacks.get(name, [])
                    for cb in callback_list:
                        try:
                            cb(self._tools[name])
                        except Exception:
                            pass
                    return self._tools[name]
            except Exception as e:
                from core.logger import logger
                logger.error(f"Falha ao carregar ferramenta '{name}': {str(e)}")

        return None

    def list_tools(self) -> Dict[str, str]:
        """Retorna nome e descrição de todas as ferramentas."""
        result: Dict[str, str] = {}
        self._load_all_lazy = True
        with self._lock:
            result = {
                name: "Lazily Loaded" if name in self._LAZY_MAP else "Unknown"
                for name in self._LAZY_MAP
            }
            for name, tool in self._tools.items():
                result[name] = tool.description
            self._load_all_lazy = False
        return result

    def get_all_tools(self) -> List[BaseTool]:
        """Força carregamento de todas as ferramentas conhecidas."""
        with self._lock:
            for name in self._LAZY_MAP.keys():
                self.get_tool(name)
            self._initialized = True
        return list(self._tools.values())

    @classmethod
    def reset_instance(cls) -> None:
        """Reseta singleton para testes."""
        with cls._lock:
            cls._instance = None
            cls._tools = {}
            cls._lazy_callbacks = {}

    @property
    def is_initialized(self) -> bool:
        return getattr(self, '_initialized', False)

registry = ToolRegistry()
