"""Short-lived in-memory media for Expo playback and local demo curls."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


@dataclass
class MediaItem:
    data: bytes
    content_type: str
    created_at: float


class MediaStore:
    def __init__(self, ttl_seconds: float = 3600.0) -> None:
        self._items: dict[str, MediaItem] = {}
        self.ttl_seconds = ttl_seconds

    def put(self, data: bytes, content_type: str = "audio/mpeg") -> str:
        self._purge()
        token = secrets.token_urlsafe(16)
        self._items[token] = MediaItem(data=data, content_type=content_type, created_at=time.time())
        return token

    def get(self, token: str) -> MediaItem | None:
        self._purge()
        return self._items.get(token)

    def _purge(self) -> None:
        now = time.time()
        expired = [k for k, v in self._items.items() if now - v.created_at > self.ttl_seconds]
        for key in expired:
            self._items.pop(key, None)


media_store = MediaStore()
