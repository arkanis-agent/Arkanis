"""
ARKANIS V3.1 - Autonomous Intelligence System
Copyright (c) 2026 Arkanis Dev Team.

Core Package Structure:
- StrategicPlanner: Handles long-term goal planning
- TaskExecutor: Manages task execution pipeline
- DecisionAuditor: Validates and audits all system decisions

Architecture:
- Event-driven core with modular components
- Real-time decision validation layer
- Self-improving knowledge graph backend
"""

import importlib
import sys
from typing import TYPE_CHECKING

__version__ = "3.1.0"
__author__ = "Arkanis AI"
__license__ = "Proprietary"
__status__ = "Development"

if TYPE_CHECKING:
    from .StrategicPlanner import StrategicPlanner
    from .TaskExecutor import TaskExecutor
    from .DecisionAuditor import DecisionAuditor

__all__ = ["StrategicPlanner", "TaskExecutor", "DecisionAuditor"]

def __getattr__(name: str):
    if name in __all__:
        mod = importlib.import_module(f".{name}", __package__)
        attr = getattr(mod, name)
        globals()[name] = attr
        sys.modules[f"{__name__}.{name}"] = mod
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")