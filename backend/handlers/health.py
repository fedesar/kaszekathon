"""Health check handler — verifies DB connectivity and returns service status."""

from __future__ import annotations

import time

from services import mysql_db


def handle() -> dict:
    start = time.time()
    mysql_db.db_get("SELECT 1")
    elapsed_ms = round((time.time() - start) * 1000, 2)

    return {"status": "ok", "db_ping_ms": elapsed_ms}
