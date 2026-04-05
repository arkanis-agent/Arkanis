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

Example Usage:
    >>> from Arkanis_V3 import StrategicPlanner
    >>> planner = StrategicPlanner()
    >>> planner.analyze_goals()

Versioning:
    Follows PEP 440 (https://peps.python.org/pep-0440/)
    MAJOR version for incompatible API changes
    MINOR version for added functionality
    PATCH version for backwards-compatible bug fixes
"""

__version__ = "3.1.0"  # Semantic versioning (MAJOR.MINOR.PATCH)
__version_info__ = (3, 1, 0)  # Tuple version for programmatic access
__author__ = "Arkanis AI"
__license__ = "Proprietary"
__status__ = "Development"
__copyright__ = "Copyright 2026 Arkanis Dev Team"

# Explicit imports to expose components defined in __all__
from .StrategicPlanner import StrategicPlanner
from .TaskExecutor import TaskExecutor
from .DecisionAuditor import DecisionAuditor

__all__ = [
    'StrategicPlanner',
    'TaskExecutor',
    'DecisionAuditor',
    '__version__',
    '__version_info__'
]
