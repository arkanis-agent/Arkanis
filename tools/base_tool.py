from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Abstract base class for all Arkanis tools.
    Every tool must implement name, description, and execute().
    """
    
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
    @abstractmethod
    def arguments(self) -> Dict[str, str]:
        """Dictionary mapping argument names to their descriptions."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """The main logic of the tool."""
        pass
