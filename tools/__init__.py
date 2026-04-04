from core.logger import logger
from tools.registry import registry

def safe_import_tool(module_name):
    try:
        import importlib
        importlib.import_module(module_name)
    except ImportError as e:
        logger.error(f"Erro ao importar ferramenta [{module_name}]: {e}", symbol="⚠️")
        # Registra no logger para o Sentinel ver depois

modules = [
    "tools.standard",
    "tools.ai_tools",
    "tools.audio_tools",
    "tools.browser_tools",
    "tools.network_tools",
    "tools.system_tools",
    "tools.monitoring_tools",
    "tools.dev_tools",
    "tools.telegram_tools",
    "tools.research_tools",
    "tools.swarm_tool"
]

for mod in modules:
    safe_import_tool(mod)

__all__ = ["registry"]
