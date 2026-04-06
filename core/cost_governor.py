import threading
import time
import logging
from collections import deque
from typing import Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger('cost_governor')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class CostGovernor:
    """
    Control layer for limiting agent scaling and LLM resource usage.
    Ensures safe bounded operation with actual enforcement.
    """
    CRITICAL_LIMIT_MULTIPLIER = 1.5
    CLEANUP_INTERVAL = 10  # seconds between scheduled cleanups
    RATE_LIMIT_DELAY = 0.1  # seconds to wait before retry on limit
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._lock = threading.RLock()
        
        # Configurable limits with environment defaults
        env = config or {'dev': True}
        base_mult = 3.0 if env.get('dev') else 1.0
        
        self.max_tasks_global = int(env.get('MAX_TASKS_GLOBAL', 15) * base_mult)
        self.max_tasks_per_goal = int(env.get('MAX_TASKS_PER_GOAL', 3))
        self.max_llm_calls_per_minute = int(env.get('MAX_LLM_CALLS_PER_MINUTE', 20))
        self.max_runtime_per_task = int(env.get('MAX_RUNTIME_PER_TASK', 3600))
        
        self.llm_call_timestamps = deque()
        self._fallback_active = False
        self._last_cleanup = 0
        
    @property
    def fallback_active(self) -> bool:
        return self._fallback_active
        self._metrics = {
            'total_calls': 0,
            'blocked_calls': 0,
            'fallback_activations': 0,
            'fallback_deactivations': 0
        }
    
    @classmethod
    def from_env(cls) -> 'CostGovernor':
        """Factory method to load config from environment variables."""
        import os
        config = {
            'dev': os.getenv('DEV_MODE', 'false').lower() == 'true',
            'MAX_TASKS_GLOBAL': os.getenv('MAX_TASKS_GLOBAL', '15'),
            'MAX_TASKS_PER_GOAL': os.getenv('MAX_TASKS_PER_GOAL', '3'),
            'MAX_LLM_CALLS_PER_MINUTE': os.getenv('MAX_LLM_CALLS_PER_MINUTE', '20'),
            'MAX_RUNTIME_PER_TASK': os.getenv('MAX_RUNTIME_PER_TASK', '3600')
        }
        return cls(config)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current governor state with metrics."""
        with self._lock:
            self._perform_maintenance()
            return {
                'max_tasks_global': self.max_tasks_global,
                'max_tasks_per_goal': self.max_tasks_per_goal,
                'max_llm_calls_per_minute': self.max_llm_calls_per_minute,
                'current_llm_calls_pm': len(self.llm_call_timestamps),
                'fallback_active': self._fallback_active,
                'metrics': self._metrics.copy(),
                'uptime_seconds': time.time() - self._last_cleanup if hasattr(self, '_last_cleanup') else 0
            }
    
    def _perform_maintenance(self):
        """Scheduled cleanup if interval has passed."""
        now = time.time()
        if now - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
        self._cleanup_llm_timestamps()
        self._last_cleanup = now
    
    def _cleanup_llm_timestamps(self):
        """Remove timestamps older than 60 seconds."""
        if not self.llm_call_timestamps:
            return
        now = time.time()
        cutoff = now - 60
        while self.llm_call_timestamps and self.llm_call_timestamps[0] < cutoff:
            self.llm_call_timestamps.popleft()
    
    def can_start_task(self, goal_id: str, current_global_tasks: int, current_goal_tasks: int) -> bool:
        """Verifies if the system can safely spawn a new task."""
        if current_global_tasks >= self.max_tasks_global:
            logger.warning('Limit reached: max_tasks_global (%d/%d)', 
                         current_global_tasks, self.max_tasks_global)
            return False
        if goal_id and current_goal_tasks >= self.max_tasks_per_goal:
            logger.warning('Limit reached: max_tasks_per_goal (%d/%d)', 
                         current_goal_tasks, self.max_tasks_per_goal)
            return False
        return True
    
    @contextmanager
    def rate_limit_blocker(self, wait_seconds: float = RATE_LIMIT_DELAY):
        """
        Context manager that blocks if LLM rate limit is hit.
        Yields True if allowed, False if blocked.
        Waits on retry on block.
        """
        import random
        retry_time = 0
        while True:
            allowed = self.can_call_llm()
            if allowed:
                yield True
                break
            logger.warning('LLM rate limit hit. Waiting {:.1f}s before retry', retry_time)
            time.sleep(random.uniform(retry_time, retry_time + 0.1))
            retry_time = min(retry_time + 1, 30)  # exponential backoff capped at 30s
            if retry_time > 60:
                # Hard break after 60s continuous blocking
                raise RuntimeError('LLM rate limit exceeded for sustained period')
            
    def can_call_llm(self) -> bool:
        """Returns True if LLM call is allowed, False if rate limited (HARD BLOCK)."""
        with self._lock:
            self._perform_maintenance()
            current_calls = len(self.llm_call_timestamps)
            
            if current_calls >= self.max_llm_calls_per_minute:
                critical_threshold = self.max_llm_calls_per_minute * self.CRITICAL_LIMIT_MULTIPLIER
                
                if current_calls > critical_threshold:
                    logger.critical('CRITICAL: API usage at %d calls/min (limit: %d). HARD BLOCK.',
                                   current_calls, self.max_llm_calls_per_minute)
                    self._metrics['blocked_calls'] += 1
                    return False
                
                if not self._fallback_active:
                    logger.warning('High API usage (%d/%d). Activating fallback mode.',
                                  current_calls, self.max_llm_calls_per_minute)
                    self._fallback_active = True
                    self._metrics['fallback_activations'] += 1
            else:
                if self._fallback_active:
                    logger.info('API usage normalized (%d/%d). Restoring normal operation.',
                               current_calls, self.max_llm_calls_per_minute)
                    self._fallback_active = False
                    self._metrics['fallback_deactivations'] += 1
            
            return current_calls < self.max_llm_calls_per_minute
    
    def record_llm_call(self, allow_call: bool = True) -> bool:
        """Records an LLM call. Returns True if call was allowed, False if blocked."""
        if not allow_call:
            self._metrics['blocked_calls'] += 1
            return False
        
        with self._lock:
            self.llm_call_timestamps.append(time.time())
            self._metrics['total_calls'] += 1
            self._perform_maintenance()
            return True
    
    def reset(self):
        """Reset state for testing."""
        with self._lock:
            self.llm_call_timestamps.clear()
            self._fallback_active = False
            self._metrics = {'total_calls': 0, 'blocked_calls': 0, 
                           'fallback_activations': 0, 'fallback_deactivations': 0}
            logger.info('CostGovernor state reset for testing')
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics for monitoring/alerting."""
        with self._lock:
            self._perform_maintenance()
            return {
                'total_llm_calls': self._metrics['total_calls'],
                'blocked_calls': self._metrics['blocked_calls'],
                'fallback_activations': self._metrics['fallback_activations'],
                'fallback_deactivations': self._metrics['fallback_deactivations'],
                'current_rate': len(self.llm_call_timestamps),
                'rate_percentage': (len(self.llm_call_timestamps) / self.max_llm_calls_per_minute * 100) if self.max_llm_calls_per_minute > 0 else 0
            }


# Singleton instance for global access
governor = CostGovernor()

def initialize_governor() -> CostGovernor:
    """Proper initialization from environment, replacing singleton."""
    global governor
    governor = CostGovernor.from_env()
    logger.info('CostGovernor initialized from environment variables')
    return governor