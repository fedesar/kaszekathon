"""AI Impact handler — lead time comparison, share breakdowns, and correlations.

Lead time and delivery metrics are computed from repo_merge_requests / repo_commits
(actual PR lifecycle data). Share breakdowns use OTLP data enriched with git metrics.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from services import mysql_db
from services.otlp_parser import parse_rows_to_records
from services.git_metrics import (
    fetch_by_email,
    fetch_total_prs,
    fetch_total_commits,
    fetch_total_loc,
    fetch_pr_lifecycle,
    fetch_ai_author_emails,
    enrich_actors_with_git,
)
from functions.claude_code.normalize import build_actor_usage, build_analytics_summary


def _hours_between(start: datetime, end: datetime) -> float | None:
    """Return hours between two datetimes, or None if either is missing."""
    if not start or not end:
        return None
    secs = (end - start).total_seconds()
    return max(0.0, secs / 3600) if secs >= 0 else None


def _avg(values: list) -> float:
    filtered = [v for v in values if v is not None]
    return round(sum(filtered) / len(filtered), 1) if filtered else 0


def _build_lead_time_timeline(
    prs: List[Dict[str, Any]], ai_emails: set
) -> List[Dict[str, Any]]:
    """Group merged PRs by ISO week and compute AI vs non-AI lead time phases (hours)."""

    week_buckets: Dict[str, Dict[str, list]] = defaultdict(
        lambda: {"ai": [], "non_ai": []}
    )

    for pr in prs:
        merged_at = pr.get("merged_at")
        creation_date = pr.get("creation_date")
        if not merged_at or not creation_date:
            continue

        week = merged_at.strftime("%G-W%V")
        email = (pr.get("author_email") or "").strip().lower()
        bucket = "ai" if email in ai_emails else "non_ai"

        first_approval = pr.get("first_approval_at")
        first_commit = pr.get("first_commit_at")

        week_buckets[week][bucket].append(
            {
                "lead_time": _hours_between(creation_date, merged_at),
                "coding": _hours_between(first_commit, creation_date),
                "waiting_for_review": _hours_between(creation_date, first_approval),
                "in_review": _hours_between(first_approval, merged_at),
            }
        )

    timeline = []
    for week in sorted(week_buckets.keys()):
        entry = {"week": week}
        for prefix in ("ai", "non_ai"):
            items = week_buckets[week][prefix]
            entry[f"{prefix}_lead_time"] = _avg([i["lead_time"] for i in items])
            entry[f"{prefix}_coding"] = _avg([i["coding"] for i in items])
            entry[f"{prefix}_waiting_for_review"] = _avg(
                [i["waiting_for_review"] for i in items]
            )
            entry[f"{prefix}_in_review"] = _avg([i["in_review"] for i in items])
            entry[f"{prefix}_ready_to_deploy"] = 0
        timeline.append(entry)

    return timeline


def _compute_pr_size(prs: List[Dict[str, Any]], ai_emails: set) -> Dict[str, int]:
    """Compute average LOC per PR for AI and non-AI authors."""
    ai_loc, ai_count = 0, 0
    non_ai_loc, non_ai_count = 0, 0

    for pr in prs:
        loc = int(pr.get("lines_added") or 0) + int(pr.get("lines_deleted") or 0)
        email = (pr.get("author_email") or "").strip().lower()
        if email in ai_emails:
            ai_loc += loc
            ai_count += 1
        else:
            non_ai_loc += loc
            non_ai_count += 1

    return {
        "ai_avg_loc_per_pr": round(ai_loc / ai_count) if ai_count > 0 else 0,
        "non_ai_avg_loc_per_pr": round(non_ai_loc / non_ai_count) if non_ai_count > 0 else 0,
    }


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

    # PR lifecycle data from git tables
    pr_rows = fetch_pr_lifecycle(start_date, end_date)
    ai_emails = fetch_ai_author_emails(org_id, by_actor)

    ai_commits = int(totals.get("commits_by_claude_code") or 0)
    ai_prs = int(totals.get("pull_requests_by_claude_code") or 0) or fetch_total_prs(start_date, end_date)
    ai_loc = int(loc.get("added") or 0)

    total_prs = max(ai_prs, fetch_total_prs(start_date, end_date))
    total_commits = max(ai_commits, fetch_total_commits(start_date, end_date))
    total_loc = max(ai_loc, fetch_total_loc(start_date, end_date))

    ai_commits_pct = round((ai_commits / total_commits * 100), 1) if total_commits > 0 else 0.0
    ai_prs_pct = round((ai_prs / total_prs * 100), 1) if total_prs > 0 else 0.0
    ai_loc_pct = round((ai_loc / total_loc * 100), 1) if total_loc > 0 else 0.0

    return {
        "from": start_date,
        "to": end_date,
        "lead_time_timeline": _build_lead_time_timeline(pr_rows, ai_emails),
        "ai_pr_breakdown": {
            "ai_prs": ai_prs,
            "total_prs": total_prs,
            "ai_pct": ai_prs_pct,
        },
        "ai_commits_breakdown": {
            "ai_commits": ai_commits,
            "total_commits": total_commits,
            "ai_pct": ai_commits_pct,
        },
        "loc_breakdown": {
            "ai_loc": ai_loc,
            "total_loc": total_loc,
            "ai_pct": ai_loc_pct,
        },
        "pr_size_comparison": _compute_pr_size(pr_rows, ai_emails),
    }
