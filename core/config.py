import os
import logging

# Configuração básica de logging para arquivos de configuração
logger = logging.getLogger("Arkanis.Config")


def load_config_int(env_var: str, default_value: int) -> int:
    """Carrega um inteiro do ambiente com fallback seguro."""
    value = os.getenv(env_var)
    if value is None:
        return default_value
    
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Configuração {env_var} inválida. Usando valor padrão: {default_value}")
        return default_value

MAX_REQUESTS: int = load_config_int("MAX_REQUESTS", 1000)