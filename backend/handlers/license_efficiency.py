"""License Efficiency handler — investment summary, adoption segments, and delivery output."""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, date
from typing import Any, Dict, List

from services import mysql_db
from services.otlp_parser import parse_rows_to_records, MICRO_USD
from services.git_metrics import fetch_total_prs
from functions.claude_code.normalize import build_actor_usage, build_analytics_summary


def _period_days(start_date: str, end_date: str) -> int:
    try:
        d0 = datetime.strptime(start_date, "%Y-%m-%d").date()
        d1 = datetime.strptime(end_date, "%Y-%m-%d").date()
        return max(1, (d1 - d0).days + 1)
    except ValueError:
        return 30


def _segment_actors(by_actor: List[Dict[str, Any]], period_days: int) -> Dict[str, int]:
    power = casual = idle = new = 0
    today = date.today().isoformat()

    for actor in by_actor:
        active_days = actor.get("active_days", 0)
        dates = actor.get("dates", [])
        ratio = active_days / period_days if period_days > 0 else 0

        # "new" if the first date seen is within the period
        if dates and min(dates) >= today[:len(min(dates))]:
            new += 1
        elif ratio > 0.40:
            power += 1
        elif ratio > 0.10:
            casual += 1
        else:
            idle += 1

    return {"power_users": power, "casual_users": casual, "idle_users": idle, "new_users": new}


def _build_cost_vs_delivery(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Daily merged PRs from repo_merge_requests (OTLP doesn't carry PR data)."""
    rows = mysql_db.db_fetch(
        """
        SELECT DATE(merged_at) AS d, COUNT(DISTINCT id_merge_request) AS prs_merged
        FROM repo_merge_requests
        WHERE merged_at IS NOT NULL
          AND DATE(merged_at) BETWEEN %s AND %s
        GROUP BY DATE(merged_at)
        ORDER BY d
        """,
        (start_date, end_date),
    )
    return [{"date": str(r["d"]), "prs_merged": int(r["prs_merged"])} for r in rows]


def _build_weekly_active_users(by_actor: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    week_actors: Dict[str, set] = defaultdict(set)
    for actor in by_actor:
        key = actor.get("actor_key", "")
        for d in actor.get("dates", []):
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                week = dt.strftime("%G-W%V")
                week_actors[week].add(key)
            except ValueError:
                pass

    return [
        {"week": w, "active_users": len(actors)}
        for w, actors in sorted(week_actors.items())
    ]


def _default_seats_summary(active_users: int) -> List[Dict[str, Any]]:
    """Returns hardcoded tool seat data. Costs can be overridden via env vars."""
    tools = [
        {
            "tool": "claude_code",
            "tool_label": "Claude Code",
            "logo": "claude-code.svg",
            "price_per_seat": float(os.environ.get("CLAUDE_CODE_PRICE_PER_SEAT", "25")),
            "seats": int(os.environ.get("CLAUDE_CODE_SEATS", "0")) or active_users,
        },
        {
            "tool": "github_copilot",
            "tool_label": "GitHub Copilot",
            "logo": "github-copilot-logo.png",
            "price_per_seat": float(os.environ.get("COPILOT_PRICE_PER_SEAT", "19")),
            "seats": int(os.environ.get("COPILOT_SEATS", "0")),
        },
        {
            "tool": "cursor_ai",
            "tool_label": "Cursor",
            "logo": "cursor-ai.png",
            "price_per_seat": float(os.environ.get("CURSOR_PRICE_PER_SEAT", "20")),
            "seats": int(os.environ.get("CURSOR_SEATS", "0")),
        },
    ]

    result = []
    for t in tools:
        monthly_cost = round(t["price_per_seat"] * t["seats"], 2)
        utilization = round((active_users / t["seats"] * 100), 1) if t["seats"] > 0 else 0.0
        result.append(
            {
                "tool": t["tool"],
                "tool_label": t["tool_label"],
                "logo": t["logo"],
                "seats": t["seats"],
                "active_users": min(active_users, t["seats"]),
                "monthly_cost": monthly_cost,
                "price_per_seat": t["price_per_seat"],
                "utilization_pct": min(utilization, 100.0),
            }
        )
    return result


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
    summary = build_analytics_summary(records, by_actor)

    totals = summary.get("totals") or {}
    cost_by_currency = summary.get("cost_by_currency") or {}
    # Costs are stored as micro-USD integers; convert back to dollars
    total_investment = float(cost_by_currency.get("USD") or 0.0) / MICRO_USD
    total_prs = int(totals.get("pull_requests_by_claude_code") or 0) or fetch_total_prs(start_date, end_date)
    cost_per_pr = round(total_investment / total_prs, 2) if total_prs > 0 else 0.0

    active_users = summary.get("actor_count", 0)
    period_days = _period_days(start_date, end_date)
    adoption = _segment_actors(by_actor, period_days)
    seats_summary = _default_seats_summary(active_users)
    total_monthly_cost = sum(t["monthly_cost"] for t in seats_summary)
    license_efficiency_pct = round((total_investment / total_monthly_cost * 100) - 100, 1) if total_monthly_cost > 0 else 0.0

    return {
        "from": start_date,
        "to": end_date,
        "license_efficiency_summary": {
            "total_investment_usd": round(total_investment, 2),
            "cost_per_pr": cost_per_pr,
            "license_efficiency_pct": license_efficiency_pct,
        },
        "seats_summary": seats_summary,
        "adoption_segments": adoption,
        "cost_vs_delivery": _build_cost_vs_delivery(start_date, end_date),
        "weekly_active_users": _build_weekly_active_users(by_actor),
    }
