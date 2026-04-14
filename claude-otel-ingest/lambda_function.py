"""AWS Lambda / CLI entry point for CLAUDE-CODE-EXTRACTOR.

Single-organization Claude Code usage extractor.
Reads the Anthropic Admin API key from the environment and fetches
analytics, users, and invites for the organization bound to that key.

Invocation:
  Lambda  -> {"op": "extract", "date_from": "2026-04-01", "date_to": "2026-04-13"}
  CLI     -> python lambda_function.py          (reads .env)
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

from functions.claude_code.normalize import (
    build_actor_usage,
    build_analytics_summary,
    build_seat_usage,
)
from services.claude_code_client import ClaudeCodeReportsClient, ClaudeCodeReportsError
from services.logging_utils import log_json, set_invocation_context

UTC = timezone.utc


def _yesterday() -> str:
    return (datetime.now(UTC) - timedelta(days=1)).date().isoformat()


def _resolve_dates(event: Dict[str, Any]) -> tuple[str, str]:
    date_from = (
        event.get("date_from")
        or event.get("since")
        or os.environ.get("CLAUDE_DATE_FROM")
    )
    date_to = (
        event.get("date_to")
        or event.get("until")
        or os.environ.get("CLAUDE_DATE_TO")
    )

    if not date_from and not date_to:
        yesterday = _yesterday()
        return yesterday, yesterday
    if date_from and not date_to:
        return str(date_from), str(date_from)
    if date_to and not date_from:
        return str(date_to), str(date_to)
    return str(date_from), str(date_to)


def _extract(event: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_ADMIN_API_KEY")
    if not api_key:
        return {"status": "error", "message": "ANTHROPIC_ADMIN_API_KEY not set in environment"}

    date_from, date_to = _resolve_dates(event)
    client = ClaudeCodeReportsClient(api_key)

    log_json(
        "info",
        "extractor",
        "Starting single-org extraction",
        status="started",
        extra={"date_from": date_from, "date_to": date_to},
    )

    start_time = time.time()
    errors = []

    # 1. Organization info
    org_info: Dict[str, Any] = {}
    try:
        _, org_info = client.fetch_current_organization()
    except ClaudeCodeReportsError as exc:
        errors.append({"step": "organization", "error": str(exc), "status_code": exc.status_code})
        log_json("warning", "extractor", "Failed to fetch organization info", status="failed", traceback=str(exc))

    org_id = org_info.get("id") or "unknown"
    org_name = org_info.get("name") or "unknown"

    # 2. Claude Code analytics (usage per user/day)
    analytics_records = []
    try:
        _, analytics_records = client.fetch_claude_code_analytics(starting_at=date_from)
    except ClaudeCodeReportsError as exc:
        errors.append({"step": "analytics", "error": str(exc), "status_code": exc.status_code})
        log_json("warning", "extractor", "Failed to fetch analytics", status="failed", traceback=str(exc))

    # 3. Organization users
    users = []
    try:
        _, users = client.fetch_organization_users()
    except ClaudeCodeReportsError as exc:
        errors.append({"step": "users", "error": str(exc), "status_code": exc.status_code})
        log_json("warning", "extractor", "Failed to fetch users", status="failed", traceback=str(exc))

    # 4. Organization invites
    invites = []
    try:
        _, invites = client.fetch_organization_invites()
    except ClaudeCodeReportsError as exc:
        errors.append({"step": "invites", "error": str(exc), "status_code": exc.status_code})
        log_json("warning", "extractor", "Failed to fetch invites", status="failed", traceback=str(exc))

    # 5. Normalize
    by_actor = build_actor_usage(analytics_records)
    summary = build_analytics_summary(analytics_records, by_actor)
    seats = build_seat_usage(users, by_actor)

    duration_ms = round((time.time() - start_time) * 1000, 1)

    log_json(
        "info",
        "extractor",
        "Extraction completed",
        status="success",
        duration_ms=duration_ms,
        extra={
            "org_id": org_id,
            "org_name": org_name,
            "analytics_records": len(analytics_records),
            "users": len(users),
            "invites": len(invites),
            "actors": len(by_actor),
        },
    )

    return {
        "status": "success",
        "organization": {
            "id": org_id,
            "name": org_name,
        },
        "date_from": date_from,
        "date_to": date_to,
        "duration_ms": duration_ms,
        "raw_counts": {
            "analytics_records": len(analytics_records),
            "users": len(users),
            "invites": len(invites),
        },
        "actor_usage": by_actor,
        "analytics_summary": summary,
        "seat_usage": seats,
        "invites": invites,
        "errors": errors or None,
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    set_invocation_context(context=context, event=event)
    op = (event or {}).get("op")
    if op in (None, "", False, "extract"):
        return _extract(event or {})
    return {"status": "unsupported", "operation": op}


if __name__ == "__main__":
    result = lambda_handler({}, {})
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
