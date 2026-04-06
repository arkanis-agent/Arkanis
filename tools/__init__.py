"""
Módulo principal de ferramentas do sistema Arkanis V3.
Expõe o registry e importa componentes padrão automaticamente.
"""

import importlib
from core.logger import logger
from tools.registry import registry

__all__ = ["logger", "registry", "safe_import_tool"]


def safe_import_tool(module_name: str) -> bool:
    """
    Importa um módulo de ferramenta de forma segura com tratamento de erro.
    
    Args:
        module_name (str): Nome do módulo a ser importado.
        
    Returns:
        bool: True se a importação foi bem-sucedida, False caso contrário.
    """
    try:
        if not module_name or not isinstance(module_name, str):
            logger.warning(
                f"Nome de módulo inválido: '{module_name}'",
                symbol="⚠️"
            )
            return False
            
        importlib.import_module(module_name)
        logger.info(f"Ferramenta '{module_name}' importada com sucesso")
        return True
    except ImportError as e:
        logger.error(
            f"Erro ao importar ferramenta '{module_name}': {e}",
            symbol="⚠️"
        )
        return False


# Basic tools that should be available by default for the kernel
# Wrapped in try-except to prevent initialization failure if dependencies are missing
try:
    safe_import_tool("tools.standard")
    safe_import_tool("tools.file_tools")
except Exception as e:
    logger.error(f"Falha na fase de bootstrap do módulo tools: {e}")
    # System can continue even if some tools fail to load
    logger.warning("Arkanis V3 iniciado com ferramentas limitadas")