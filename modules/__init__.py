"""
External modules package for ARKANIS OS.

This package provides:
- Memory management configurations
- Custom module loading system

Example usage:
    >>> from modules import memory_manager
    >>> mm = memory_manager.allocate(1024)

For more information, refer to the official documentation at:
https://arkanis-os.com/docs/modules
"""

__all__ = ["memory_config", "network_utils", "security_handlers"]

from . import memory_config
from . import network_utils
from . import security_handlers