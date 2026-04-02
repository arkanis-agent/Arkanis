import threading
import time
from typing import Dict, Any

class CostGovernor:
    """
    Control layer for limiting agent scaling and LLM resource usage.
    Ensures safe bounded operation.
    """
    def __init__(self):
        self._lock = threading.Lock()
        
        # Modifiable Limits
        self.max_tasks_global = 15
        self.max_tasks_per_goal = 3
        self.max_llm_calls_per_minute = 20
        self.max_runtime_per_task = 3600 # seconds default (1 hour)
        
        # State tracking
        self.llm_call_timestamps = []
        self.fallback_active = False

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            self._cleanup_llm_timestamps()
            return {
                "max_tasks_global": self.max_tasks_global,
                "max_tasks_per_goal": self.max_tasks_per_goal,
                "max_llm_calls_per_minute": self.max_llm_calls_per_minute,
                "current_llm_calls_pm": len(self.llm_call_timestamps),
                "fallback_active": self.fallback_active
            }

    def _cleanup_llm_timestamps(self):
        now = time.time()
        # Keep only timestamps within the last 60 seconds
        self.llm_call_timestamps = [t for t in self.llm_call_timestamps if now - t <= 60]

    def can_start_task(self, goal_id: str, current_global_tasks: int, current_goal_tasks: int) -> bool:
        """Verifies if the system can safely spawn a new task, preventing overload."""
        if current_global_tasks >= self.max_tasks_global:
            print("[Governor] Limit reached: max_tasks_global")
            return False
        
        if goal_id and current_goal_tasks >= self.max_tasks_per_goal:
            print("[Governor] Limit reached: max_tasks_per_goal")
            return False
            
        return True

    def record_llm_call(self):
        with self._lock:
            self.llm_call_timestamps.append(time.time())

    def can_call_llm(self) -> bool:
        """Returns False if strict blocking is needed, True if ok."""
        with self._lock:
            self._cleanup_llm_timestamps()
            if len(self.llm_call_timestamps) >= self.max_llm_calls_per_minute:
                if not self.fallback_active:
                    print("[Governor] High API usage. Switching to fallback models or limiting calls.")
                    self.fallback_active = True
                
                # If we are drastically over limit, hard block
                if len(self.llm_call_timestamps) > self.max_llm_calls_per_minute * 1.5:
                    print("[Governor] Critical Limit reached: Hard blocking LLM call.")
                    return False
            else:
                if self.fallback_active:
                    print("[Governor] API usage normalized. Restoring normal operation.")
                    self.fallback_active = False
            return True

governor = CostGovernor()
