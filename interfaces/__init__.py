"""Módulo de Interfaces do Sistema Arkanis V3

Este pacote define todas as interfaces públicas do sistema,
incluindo contratos de serviço, protocolos e APIs.

:version: 3.1.0
"""

import logging
from typing import List

__all__: List[str] = []

__version__: str = '3.1.0'

# Configuração de logging
logger: logging.Logger = logging.getLogger(__name__)


def initialize_interfaces() -> None:
    """Inicializa as interfaces do sistema Arkanis."""
    try:
        logger.info('Inicializando interfaces Arkanis V3...')
        # Importações adicionais podem ser feitas aqui quando necessário
    except Exception as e:
        logger.error('Erro durante inicialização das interfaces: %s', e, exc_info=True)
        raise
