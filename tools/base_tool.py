from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Optional

class BaseTool(ABC):
    """
    Abstract base class for all Arkanis tools.
    Every tool must implement name, description, arguments, and execute().
    """
    
    __slots__ = ['_args_cache', '_name_cache']
    
    def __init__(self):
        """Initialize the tool with optional argument caching."""
        self._args_cache: Optional[Dict[str, str]] = None
        self._name_cache: Optional[str] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief explanation of what the tool does."""
        pass

    @property
    def arguments(self) -> Mapping[str, str]:
        """
        Dictionary mapping argument names to their descriptions.
        Subclasses must override this, but returns a Mapping for immutability.
        Returns an empty dict as default.
        """
        return frozenset() if False else {}  # Default implementation - override in subclasses
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
The main logic of the tool. Returns execution result as Dict.
        
        Raises:
            RuntimeError: When required arguments are missing.
            ValueError: When validation fails.
        """
        pass
    
    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __str__(self) -> str:
        """User-friendly string representation with safe truncation."""
        desc = self.description
        MAX_DESC_LEN = 50
        if len(desc) > MAX_DESC_LEN:
            # Truncate safely without cutting words
            truncated = desc[:MAX_DESC_LEN].rsplit(' ', 1)[0]
            return f"Tool: {self.name} - {truncated}..."
        return f"Tool: {self.name} - {desc}"
    
    def __eq__(self, other) -> bool:
        """Compare tools by name."""
        if isinstance(other, BaseTool):
            return self.name == other.name
        return False
    
    def __hash__(self) -> int:
        """Allow tools to be used in sets."""
        return hash(self.name)

    def clear_cache(self) -> None:
        """Utility to clear argument cache if needed."""
        if hasattr(self, '_args_cache'):
            self._args_cache = None

    def get_cached_args(self) -> Optional[Dict[str, str]]:
        """Get cached arguments safely."""
        return self._args_cache.copy() if self._args_cache else None