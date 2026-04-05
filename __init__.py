"""
ARKANIS V3.1 - Autonomous Intelligence System
Core system package initialization and exports.

Copyright (c) 2026 Arkanis Dev Team. All Rights Reserved.

Core Components:
- StrategicPlanner: Handles long-term goal planning and strategy formulation
- TaskExecutor: Manages task execution pipeline with priority queuing
- DecisionAuditor: Validates and audits all system decisions in real-time

Architecture Overview:
- Event-driven core with modular, pluggable components
- Multi-layer decision validation system
- Self-improving knowledge graph backend with continuous learning
- Real-time performance monitoring and self-optimization

Usage Example:
    from arkanis_v3 import StrategicPlanner, TaskExecutor
    planner = StrategicPlanner()
    executor = TaskExecutor()
"""

__version__ = "3.1.0"  # Semantic versioning (MAJOR.MINOR.PATCH)
__author__ = "Arkanis AI"
__license__ = "Proprietary"
__status__ = "Development"

# Core component imports - maintain alphabetical order
from .DecisionAuditor import DecisionAuditor
from .StrategicPlanner import StrategicPlanner
from .TaskExecutor import TaskExecutor

__all__ = [
    'DecisionAuditor',
    'StrategicPlanner',
    'TaskExecutor'
]  # Maintain alphabetical order for consistency