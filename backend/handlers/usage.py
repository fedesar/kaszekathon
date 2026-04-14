"""AI Usage handler — returns KPI metrics, daily trend, and per-user breakdown."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List

from services import mysql_db
from functions.claude_code.normalize import build_actor_usage, build_analytics_summary


def _parse_records(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    for row in rows:
        payload_text = row.get("payload_text") or ""
        try:
            data = json.loads(payload_text)
        except (json.JSONDecodeError, TypeError):
            continue

        # payload_text may be a single record dict or a list of records
        if isinstance(data, list):
            records.extend(r for r in data if isinstance(r, dict))
        elif isinstance(data, dict):
            records.append(data)

    return records


def _build_daily_trend(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    day_sessions: Dict[str, int] = defaultdict(int)
    day_actors: Dict[str, set] = defaultdict(set)

    for r in records:
        date = r.get("date")
        if not date:
            continue
        core = r.get("core_metrics") or {}
        sessions = int(core.get("num_sessions") or 0)
        day_sessions[date] += sessions

        actor = r.get("actor") or {}
        email = actor.get("email_address") or actor.get("api_key_name") or "unknown"
        day_actors[date].add(email)

    all_dates = sorted(set(list(day_sessions.keys()) + list(day_actors.keys())))
    return [
        {
            "date": d,
            "sessions": day_sessions.get(d, 0),
            "active_users": len(day_actors.get(d, set())),
        }
        for d in all_dates
    ]


def _build_user_list(by_actor: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    users = []
    for actor in by_actor:
        if actor.get("actor_type") != "user_actor":
            continue

        core = actor.get("core_metrics") or {}
        loc = core.get("lines_of_code") or {}
        tool_actions = actor.get("tool_actions") or {}

        total_accepted = sum(v.get("accepted", 0) for v in tool_actions.values())
        total_rejected = sum(v.get("rejected", 0) for v in tool_actions.values())
        total_actions = total_accepted + total_rejected
        acceptance_rate = round(total_accepted / total_actions, 4) if total_actions > 0 else 0.0

        users.append(
            {
                "email": actor.get("email_address") or actor.get("actor_label") or "",
                "active_days": actor.get("active_days", 0),
                "sessions": int(core.get("num_sessions") or 0),
                "loc_added": int(loc.get("added") or 0),
                "prs": int(core.get("pull_requests_by_claude_code") or 0),
                "commits": int(core.get("commits_by_claude_code") or 0),
                "tool_acceptance_rate": acceptance_rate,
            }
        )

    return users


def handle(params: Dict[str, Any]) -> dict:
    org_id = params["org_id"]
    start_date = params["start_date"]
    end_date = params["end_date"]

    rows = mysql_db.db_fetch(
        """
        SELECT payload_text
        FROM claude_code_otel_ingest
        WHERE id_organization = %s
          AND DATE(created_at) BETWEEN %s AND %s
          AND signal_type = 'logs'
        ORDER BY created_at
        """,
        (org_id, start_date, end_date),
    )

    records = _parse_records(rows)
    by_actor = build_actor_usage(records)
    summary = build_analytics_summary(records, by_actor)
    totals = summary.get("totals") or {}
    loc = totals.get("lines_of_code") or {}

    return {
        "from": start_date,
        "to": end_date,
        "kpis": {
            "total_sessions": int(totals.get("num_sessions") or 0),
            "active_users": summary.get("actor_count", 0),
            "loc_added": int(loc.get("added") or 0),
            "prs_by_ai": int(totals.get("pull_requests_by_claude_code") or 0),
            "ai_commits": int(totals.get("commits_by_claude_code") or 0),
        },
        "daily_trend": _build_daily_trend(records),
        "user_list": _build_user_list(by_actor),
    }
