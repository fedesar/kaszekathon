"""AI Usage handler — returns KPI metrics, daily trend, and per-user breakdown."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from services import mysql_db
from services.otlp_parser import parse_rows_to_records
from services.git_metrics import fetch_by_email, fetch_total_prs, enrich_actors_with_git
from functions.claude_code.normalize import build_actor_usage, build_analytics_summary


def _build_daily_trend(
    records: List[Dict[str, Any]], start_date: str, end_date: str
) -> List[Dict[str, Any]]:
    day_actors: Dict[str, set] = defaultdict(set)
    day_tokens: Dict[str, int] = defaultdict(int)

    for r in records:
        date = r.get("date")
        if not date:
            continue

        actor = r.get("actor") or {}
        email = actor.get("email_address") or actor.get("api_key_name") or "unknown"
        day_actors[date].add(email)

        for m in r.get("model_breakdown", []):
            if not isinstance(m, dict):
                continue
            tokens = m.get("tokens") if isinstance(m.get("tokens"), dict) else {}
            day_tokens[date] += sum(
                int(tokens.get(k) or 0) for k in ("input", "output", "cache_creation", "cache_read")
            )

    # LOC from repo_commits (OTLP doesn't carry LOC data)
    day_loc: Dict[str, int] = defaultdict(int)
    loc_rows = mysql_db.db_fetch(
        """
        SELECT DATE(commit_creation_date) AS d, COALESCE(SUM(lines_added), 0) AS loc
        FROM repo_commits
        WHERE DATE(commit_creation_date) BETWEEN %s AND %s
        GROUP BY DATE(commit_creation_date)
        """,
        (start_date, end_date),
    )
    for row in loc_rows:
        d = str(row.get("d") or "")
        day_loc[d] += int(row.get("loc") or 0)

    all_dates = sorted(set(list(day_actors.keys()) + list(day_tokens.keys()) + list(day_loc.keys())))
    return [
        {
            "date": d,
            "active_users": len(day_actors.get(d, set())),
            "tokens_consumed": day_tokens.get(d, 0),
            "loc_added": day_loc.get(d, 0),
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

        tokens_consumed = sum(
            sum(m.get("tokens", {}).get(k, 0) for k in ("input", "output", "cache_creation", "cache_read"))
            for m in actor.get("model_breakdown", [])
            if isinstance(m, dict)
        )

        users.append(
            {
                "email": actor.get("email_address") or actor.get("actor_label") or "",
                "active_days": actor.get("active_days", 0),
                "sessions": int(core.get("num_sessions") or 0),
                "loc_added": int(loc.get("added") or 0),
                "prs": int(core.get("pull_requests_by_claude_code") or 0),
                "commits": int(core.get("commits_by_claude_code") or 0),
                "tokens_consumed": tokens_consumed,
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
        SELECT signal_type, payload_text
        FROM claude_code_otel_ingest
        WHERE id_organization = %s
          AND DATE(created_at) BETWEEN %s AND %s
        ORDER BY created_at
        """,
        (org_id, start_date, end_date),
    )

    records = parse_rows_to_records(rows)
    by_actor = build_actor_usage(records)
    enrich_actors_with_git(by_actor, fetch_by_email(org_id, start_date, end_date))
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
            "prs_by_ai": int(totals.get("pull_requests_by_claude_code") or 0) or fetch_total_prs(start_date, end_date),
            "ai_commits": int(totals.get("commits_by_claude_code") or 0),
        },
        "daily_trend": _build_daily_trend(records, start_date, end_date),
        "user_list": _build_user_list(by_actor),
    }
