from dataclasses import dataclass
from typing import Any

@dataclass
class ShortTermMemory:
    data: dict
    timestamp: float
    expiration: float

    def store(self, key: str, value: Any, ttl: float) -> None:
        self.data[key] = {
            'value': value,
            'timestamp': self.timestamp,
            'expiration': self.timestamp + ttl
        }

    def retrieve(self, key: str) -> Any:
        item = self.data.get(key)
        if item and item['expiration'] > self.timestamp:
            return item['value']
        return None

    def purge_expired(self) -> None:
        current_time = self.timestamp
        self.data = {k: v for k, v in self.data.items() if v['expiration'] > current_time}