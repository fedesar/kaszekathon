"""Convert raw OTLP rows from claude_code_otel_ingest into the intermediate
record format that normalize.build_actor_usage() expects.

Each DB row stores one OTLP HTTP payload exactly as Claude Code sent it.
Signal types:
  'logs'    → resourceLogs → scopeLogs → logRecords[]
  'metrics' → resourceMetrics → scopeMetrics → metrics[] → dataPoints[]

We group log events by (email, date) and produce one record per group,
which matches the shape normalize.py expects:

  {
    actor:        {type, email_address, api_key_name}
    date:         "YYYY-MM-DD"
    terminal_type, organization_id
    core_metrics: {num_sessions, commits_by_claude_code, lines_of_code, pull_requests_by_claude_code}
    tool_actions: {tool_name: {accepted, rejected}}
    model_breakdown: [{model, estimated_cost: {currency, amount_micro_usd}, tokens: {...}}]
  }

COST ENCODING
  normalize.py uses _as_int() on cost amounts, so floating-point USD values
  (e.g. 0.0166836) would be truncated to 0.
  We store amounts as MICRO-USD (multiply by 1_000_000) so that
    0.0166836 → 16_683
  Callers that need real USD must divide by 1_000_000.
  See handlers/roi.py for the corresponding division.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

MICRO_USD = 1_000_000  # cost_usd * MICRO_USD → integer stored in model_breakdown


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _attr(attributes: list, key: str) -> Optional[str]:
    """Return the string value of an OTLP attribute by key, or None."""
    for item in attributes:
        if item.get("key") == key:
            val = item.get("value") or {}
            raw = (
                val.get("stringValue")
                or val.get("intValue")
                or val.get("doubleValue")
                or val.get("boolValue")
            )
            if raw is not None:
                text = str(raw).strip()
                return text or None
    return None


def _float_attr(attributes: list, key: str) -> float:
    raw = _attr(attributes, key)
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def _int_attr(attributes: list, key: str) -> int:
    return int(_float_attr(attributes, key))


def _date_from_iso(ts: Optional[str]) -> Optional[str]:
    """Return 'YYYY-MM-DD' from an ISO-8601 timestamp string."""
    if not ts:
        return None
    return ts[:10] if len(ts) >= 10 else None


# ---------------------------------------------------------------------------
# Per-group accumulator
# ---------------------------------------------------------------------------

def _new_group(email: str, date: str, terminal_type: str, org_id: Optional[str]) -> Dict[str, Any]:
    return {
        "email": email,
        "date": date,
        "terminal_type": terminal_type,
        "organization_id": org_id,
        "sessions": set(),            # distinct session_ids → num_sessions
        "model_costs": {},            # model → {input, output, cache_creation, cache_read, cost_micro_usd}
        "tool_actions": {},           # tool_name → {accepted, rejected}
        "loc_added": 0,
        "loc_removed": 0,
        "commits": 0,
        "prs": 0,
    }


# ---------------------------------------------------------------------------
# Log record handlers per event name
# ---------------------------------------------------------------------------

def _handle_api_request(attrs: list, group: Dict[str, Any]) -> None:
    model = _attr(attrs, "model") or "unknown"
    entry = group["model_costs"].setdefault(
        model,
        {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0, "cost_micro_usd": 0},
    )
    entry["input"] += _int_attr(attrs, "input_tokens")
    entry["output"] += _int_attr(attrs, "output_tokens")
    entry["cache_creation"] += _int_attr(attrs, "cache_creation_tokens")
    entry["cache_read"] += _int_attr(attrs, "cache_read_tokens")
    entry["cost_micro_usd"] += round(_float_attr(attrs, "cost_usd") * MICRO_USD)


def _handle_tool_result(attrs: list, group: Dict[str, Any]) -> None:
    tool = _attr(attrs, "tool.name") or _attr(attrs, "tool_name") or "unknown"
    outcome = (_attr(attrs, "tool.result") or _attr(attrs, "result") or "").lower()
    entry = group["tool_actions"].setdefault(tool, {"accepted": 0, "rejected": 0})
    if outcome in ("accepted", "success", "true", "1"):
        entry["accepted"] += 1
    elif outcome in ("rejected", "error", "false", "0"):
        entry["rejected"] += 1
    else:
        entry["accepted"] += 1  # assume accepted when outcome is unknown


def _handle_commit(attrs: list, group: Dict[str, Any]) -> None:
    group["commits"] += 1


def _handle_pr(attrs: list, group: Dict[str, Any]) -> None:
    group["prs"] += 1


def _handle_loc(attrs: list, group: Dict[str, Any]) -> None:
    group["loc_added"] += _int_attr(attrs, "lines.added") or _int_attr(attrs, "loc_added")
    group["loc_removed"] += _int_attr(attrs, "lines.removed") or _int_attr(attrs, "loc_removed")


_EVENT_HANDLERS = {
    "api_request": _handle_api_request,
    "tool_result": _handle_tool_result,
    "tool_use_result": _handle_tool_result,
    "git_commit": _handle_commit,
    "pr_create": _handle_pr,
    "lines_of_code": _handle_loc,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_rows_to_records(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse raw DB rows into normalized records for build_actor_usage().

    Only 'logs' rows are processed; 'metrics' rows are skipped because all
    relevant data is already captured in the log events.
    """
    groups: Dict[tuple, Dict[str, Any]] = {}

    for row in rows:
        if row.get("signal_type") != "logs":
            continue

        payload_text = row.get("payload_text") or ""
        try:
            payload = json.loads(payload_text)
        except (json.JSONDecodeError, TypeError):
            continue

        for resource_log in payload.get("resourceLogs", []):
            for scope_log in resource_log.get("scopeLogs", []):
                for log_rec in scope_log.get("logRecords", []):
                    attrs = log_rec.get("attributes") or []

                    email = _attr(attrs, "user.email")
                    if not email:
                        continue

                    # Date: prefer event.timestamp, fall back to timeUnixNano
                    ts = _attr(attrs, "event.timestamp")
                    date = _date_from_iso(ts)
                    if not date:
                        nano = log_rec.get("timeUnixNano")
                        if nano:
                            import datetime
                            dt = datetime.datetime.utcfromtimestamp(int(nano) / 1e9)
                            date = dt.strftime("%Y-%m-%d")
                    if not date:
                        continue

                    session_id = _attr(attrs, "session.id") or ""
                    terminal_type = _attr(attrs, "terminal.type") or "unknown"
                    org_id = _attr(attrs, "organization.id")

                    key = (email, date)
                    if key not in groups:
                        groups[key] = _new_group(email, date, terminal_type, org_id)

                    group = groups[key]
                    if session_id:
                        group["sessions"].add(session_id)

                    event_name = _attr(attrs, "event.name") or ""
                    handler = _EVENT_HANDLERS.get(event_name)
                    if handler:
                        handler(attrs, group)

    # Convert groups → normalized records
    records: List[Dict[str, Any]] = []
    for group in groups.values():
        model_breakdown = [
            {
                "model": model,
                "estimated_cost": {"currency": "USD", "amount": data["cost_micro_usd"]},
                "tokens": {
                    "input": data["input"],
                    "output": data["output"],
                    "cache_creation": data["cache_creation"],
                    "cache_read": data["cache_read"],
                },
            }
            for model, data in group["model_costs"].items()
        ]

        records.append(
            {
                "actor": {
                    "type": "user_actor",
                    "email_address": group["email"],
                    "api_key_name": None,
                },
                "date": group["date"],
                "terminal_type": group["terminal_type"],
                "organization_id": group["organization_id"],
                "core_metrics": {
                    "num_sessions": len(group["sessions"]),
                    "commits_by_claude_code": group["commits"],
                    "lines_of_code": {
                        "added": group["loc_added"],
                        "removed": group["loc_removed"],
                    },
                    "pull_requests_by_claude_code": group["prs"],
                },
                "tool_actions": group["tool_actions"],
                "model_breakdown": model_breakdown,
            }
        )

    return records


__all__ = ["parse_rows_to_records", "MICRO_USD"]
