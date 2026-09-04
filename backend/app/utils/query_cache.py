"""Bounded in-process cache for completed investigation responses."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict
from threading import RLock
from time import monotonic
from typing import Any, Callable, Mapping


CachePayload = dict[str, Any]


class QueryResponseCache:
    """Thread-safe TTL cache that stores serialized response payloads only."""

    def __init__(
        self,
        *,
        max_entries: int = 128,
        ttl_seconds: float = 300.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0")

        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, CachePayload]] = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> CachePayload | None:
        """Return a safe copy of a non-expired cached payload, if available."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None

            expires_at, payload = entry
            if self._clock() >= expires_at:
                del self._entries[key]
                return None

            self._entries.move_to_end(key)
            return copy.deepcopy(payload)

    def set(self, key: str, payload: Mapping[str, Any]) -> None:
        """Store a serialized response payload and evict the least-recent entry."""
        with self._lock:
            self._entries[key] = (
                self._clock() + self._ttl_seconds,
                copy.deepcopy(dict(payload)),
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        """Remove all entries. Intended for deterministic test setup and teardown."""
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            now = self._clock()
            expired_keys = [
                key for key, (expires_at, _) in self._entries.items()
                if now >= expires_at
            ]
            for key in expired_keys:
                del self._entries[key]
            return len(self._entries)


def build_query_cache_key(
    *,
    query: str,
    dataset_path: str,
    normal_sample_size: int | None,
    filters: Mapping[str, Any] | None,
) -> str:
    """Build a stable digest from every request input that changes analysis output."""
    cache_inputs = {
        "query": query.strip(),
        "dataset_path": dataset_path,
        "normal_sample_size": normal_sample_size,
        "filters": dict(filters or {}),
    }
    canonical_inputs = json.dumps(
        cache_inputs,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical_inputs.encode("utf-8")).hexdigest()


query_response_cache = QueryResponseCache()
