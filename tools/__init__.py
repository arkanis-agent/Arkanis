from core.logger import logger
from tools.registry import registry

def safe_import_tool(module_name):
    try:
        import importlib
        importlib.import_module(module_name)
    except ImportError as e:
        logger.error(f"Erro ao importar ferramenta [{module_name}]: {e}", symbol="⚠️")
        # Registra no logger para o Sentinel ver depois

# Basic tools that should be available by default for the kernel
safe_import_tool("tools.standard")
safe_import_tool("tools.file_tools")

__all__ = ["registry"]
