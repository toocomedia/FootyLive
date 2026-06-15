from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            entry = self._entries.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                del self._entries[key]
                return None
            return entry.value

    def get_stale(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            return entry.value if entry else None

    def set(self, key: str, value: Any) -> Any:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at=expires_at)
        return value
