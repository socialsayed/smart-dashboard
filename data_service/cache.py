import time
from typing import Any, Dict


class TTLCache:
    """
    Simple in-memory TTL cache.
    Shared across all users via backend process.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None

        if time.time() - item["ts"] > item["ttl"]:
            self._store.pop(key, None)
            return None

        return item["value"]

    def set(self, key: str, value: Any, ttl: int):
        self._store[key] = {
            "value": value,
            "ts": time.time(),
            "ttl": ttl,
        }