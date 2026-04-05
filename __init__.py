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

__version__ = "3.1.0"  # Follows semantic versioning (MAJOR.MINOR.PATCH)
__author__ = "Arkanis AI"
__license__ = "Proprietary"
__status__ = "Development"

# Explicit imports to expose components defined in __all__
# Ajuste os caminhos relativos (.modulo) conforme a estrutura real do projeto
from .StrategicPlanner import StrategicPlanner
from .TaskExecutor import TaskExecutor
from .DecisionAuditor import DecisionAuditor

__all__ = ['StrategicPlanner', 'TaskExecutor', 'DecisionAuditor']