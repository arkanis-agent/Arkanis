import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class ShortTermMemory:
    data: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, init=False)

    def store(self, key: str, value: Any, ttl: float) -> None:
        current_time = time.time()
        with self._lock:
            self.data[key] = {
                'value': value,
                'stored_at': current_time,
                'expires_at': current_time + ttl
            }

    def retrieve(self, key: str) -> Optional[Any]:
        current_time = time.time()
        with self._lock:
            item = self.data.get(key)
            if item and item['expires_at'] > current_time:
                return item['value']
        return None

    def purge_expired(self) -> None:
        current_time = time.time()
        with self._lock:
            self.data = {k: v for k, v in self.data.items() if v['expires_at'] > current_time}

    @property
    def size(self) -> int:
        with self._lock:
            return len(self.data)