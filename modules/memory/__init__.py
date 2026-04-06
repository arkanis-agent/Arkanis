"""
Arkanis Memory Subsystem - Version 3.1

This module provides the core memory management system for Arkanis, including:
- Short-term/Session Memory: Temporary state management
- Long-term/Persistent Memory: Permanent data storage
- Vector Memory: High-dimensional data processing
- Semantic Cache: Contextual understanding layer

Usage:
    >>> from modules.memory import session_memory, long_term_memory
    >>> session_memory.store('key', 'value')
"""

# Public API definition
__all__ = [
    'session_memory',
    'long_term_memory',
    'VectorMemory',
    'chronos_memory',
    'semantic_cache'
]

# Local imports
from .short_term import session_memory
from .long_term import long_term_memory
from .vector import VectorMemory, chronos_memory

# Core imports
from core.semantic_cache import semantic_cache