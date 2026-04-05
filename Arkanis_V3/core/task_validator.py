from typing import Any
from collections.abc import Mapping

REQUIRED_TASK_FIELDS = frozenset(("id", "action", "params"))

class InvalidTaskError(Exception):
    """Raised when a task fails schema validation."""
    pass

def validate_task_schema(task: Any) -> bool:
    if not isinstance(task, Mapping):
        raise InvalidTaskError(f"Task must be a mapping/dict, got {type(task).__name__}")
    
    missing = REQUIRED_TASK_FIELDS - task.keys()
    if missing:
        raise InvalidTaskError(f"Missing required fields: {', '.join(sorted(missing))}")
        
    return True