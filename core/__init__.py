""" Core components of ARKANIS.
Includes the Logical Bus, Goal Manager, System Config, and Model Strategy.

Version: 3.1 | Module: core
"""

import sys
from typing import TYPE_CHECKING, Any

# Version Control
__version__ = "3.1"
__all__ = [
    "agent_bus",
    "goal_manager",
    "config_manager",
    "LLMClient",
    "strategy_engine",
    "logger",
    "__version__",
]

# Lazy import for performance
if TYPE_CHECKING:
    from typing import TYPE_CHECKING
else:
    try:
        from .agent_bus import agent_bus
        from .goal_manager import goal_manager
        from .config_manager import config_manager
        from .llm_client import LLMClient
        from .model_strategy import strategy_engine
        from .logger import logger
    except ImportError as e:
        error_msg = f"Falha ao importar módulo core: {e}"
        print(f"[ARKANIS ERROR] {error_msg}", file=sys.stderr)
        raise

# Optional type hints for export clarity
#
potential_type_hints = {
    "agent_bus": "AgentBus",
    "goal_manager": "GoalManager",
    "config_manager": "ConfigManager",
    "LLMClient": "Any",
    "strategy_engine": "StrategyEngine",
    "logger": "Logger",
}
