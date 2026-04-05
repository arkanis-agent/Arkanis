"""
Arkanis V3 - Core Module
========================

Este módulo inicializa e exporta os principais componentes do sistema:
- NetworkManager: Gerencia operações de rede
- SystemMonitor: Monitora o estado do sistema
- AuthManager: Gerencia autenticação e segurança
- StorageHandler: Manipula operações de armazenamento
"""

from .tools.network_tools import NetworkManager
from .core.system_monitor import SystemMonitor
from .security.auth_manager import AuthManager
from .data.storage_handler import StorageHandler

__version__ = '3.1.0'

__all__ = ['NetworkManager', 'SystemMonitor', 'AuthManager', 'StorageHandler']