"""Simple in-memory response cache with TTL.

Used by handlers to avoid re-fetching 2000+ large OTEL payloads on every request.
First call for a given (org_id, start_date, end_date) is slow (DB fetch + parse).
All subsequent calls within TTL return instantly from the dict.
"""

from __future__ import annotations

import time
import threading
from typing import Any

_store: dict[str, dict] = {}
_lock = threading.Lock()

TTL_SECONDS = 300  # 5 minutes


def _key(handler_name: str, params: dict) -> str:
    return f"{handler_name}:{params['org_id']}:{params['start_date']}:{params['end_date']}"


def get(handler_name: str, params: dict) -> Any | None:
    k = _key(handler_name, params)
    with _lock:
        entry = _store.get(k)
    if entry and (time.time() - entry["ts"]) < TTL_SECONDS:
        return entry["data"]
    return None


def set(handler_name: str, params: dict, data: Any) -> None:
    k = _key(handler_name, params)
    with _lock:
        _store[k] = {"ts": time.time(), "data": data}
