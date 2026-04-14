"""Fetch git-sourced metrics (LOC, commits, PRs) via user_identity_map.

Bridges OTLP auth tokens to git identities:
  claude_code_otel_ingest.authorization_token_sha256
      → user_identity_map.auth_token_sha256
      → user_identity_map.git_email / id_user
      → repo_commits / repo_merge_requests
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from services import mysql_db

log = logging.getLogger(__name__)


def fetch_by_email(org_id: int, start_date: str, end_date: str) -> Dict[str, Dict[str, int]]:
    """Return {email_lower: {loc_added, loc_removed, commits, prs}} for the date range.

    Merges two sources:
    1. user_identity_map — org-scoped, handles different git/Claude emails.
    2. Direct repo_commits.author_email — covers users not yet in identity map.

    Identity map results take precedence when both sources have data for the same email.
    """
    direct = _fetch_direct(start_date, end_date)
    mapped = _fetch_via_identity_map(org_id, start_date, end_date)

    # Merge taking the max of each metric to avoid overwriting good data with zeros
    all_emails = set(list(direct.keys()) + list(mapped.keys()))
    empty = {"loc_added": 0, "loc_removed": 0, "commits": 0, "prs": 0}
    result = {}
    for email in all_emails:
        d = direct.get(email, empty)
        m = mapped.get(email, empty)
        result[email] = {
            "loc_added": max(d["loc_added"], m["loc_added"]),
            "loc_removed": max(d["loc_removed"], m["loc_removed"]),
            "commits": max(d["commits"], m["commits"]),
            "prs": max(d["prs"], m["prs"]),
        }

    # Add OTLP email aliases so enrich can match by either email
    otel_map = _build_otel_to_git_map()
    for otel_email, git_email in otel_map.items():
        if git_email in result and otel_email not in result:
            result[otel_email] = result[git_email]

    return result


def _fetch_via_identity_map(
    org_id: int, start_date: str, end_date: str
) -> Dict[str, Dict[str, int]]:
    commit_rows = mysql_db.db_fetch(
        """
        SELECT uim.git_email,
               COALESCE(SUM(rc.lines_added),  0) AS loc_added,
               COALESCE(SUM(rc.lines_deleted), 0) AS loc_removed,
               COUNT(DISTINCT rc.id_commit)       AS commits
        FROM user_identity_map uim
        JOIN repo_commits rc ON rc.author_email = uim.git_email
        WHERE uim.auth_token_sha256 IN (
            SELECT DISTINCT authorization_token_sha256
            FROM claude_code_otel_ingest
            WHERE id_organization = %s
        )
          AND DATE(rc.commit_creation_date) BETWEEN %s AND %s
        GROUP BY uim.git_email
        """,
        (org_id, start_date, end_date),
    )

    pr_rows = mysql_db.db_fetch(
        """
        SELECT uim.git_email,
               COUNT(DISTINCT rmr.id_merge_request) AS prs
        FROM user_identity_map uim
        JOIN repo_commits rc ON rc.author_email = uim.git_email
        JOIN repo_merge_requests rmr ON rmr.author_app_id = rc.author_app_id
        WHERE uim.auth_token_sha256 IN (
            SELECT DISTINCT authorization_token_sha256
            FROM claude_code_otel_ingest
            WHERE id_organization = %s
        )
          AND DATE(rmr.creation_date) BETWEEN %s AND %s
        GROUP BY uim.git_email
        """,
        (org_id, start_date, end_date),
    )

    return _build_result(commit_rows, pr_rows, email_key="git_email")


def _fetch_direct(start_date: str, end_date: str) -> Dict[str, Dict[str, int]]:
    """Fallback: match directly by repo_commits.author_email when identity map is empty."""
    commit_rows = mysql_db.db_fetch(
        """
        SELECT author_email                           AS git_email,
               COALESCE(SUM(lines_added),  0)         AS loc_added,
               COALESCE(SUM(lines_deleted), 0)        AS loc_removed,
               COUNT(DISTINCT id_commit)              AS commits
        FROM repo_commits
        WHERE author_email IS NOT NULL
          AND DATE(commit_creation_date) BETWEEN %s AND %s
        GROUP BY author_email
        """,
        (start_date, end_date),
    )

    pr_rows = mysql_db.db_fetch(
        """
        SELECT rc.author_email                       AS git_email,
               COUNT(DISTINCT rmr.id_merge_request)  AS prs
        FROM repo_merge_requests rmr
        JOIN repo_commits rc ON rc.author_app_id = rmr.author_app_id
        WHERE rc.author_email IS NOT NULL
          AND DATE(rmr.creation_date) BETWEEN %s AND %s
        GROUP BY rc.author_email
        """,
        (start_date, end_date),
    )

    return _build_result(commit_rows, pr_rows, email_key="git_email")


def _fetch_prs_safe(sql: str, params: tuple) -> list:
    """Execute a PR query that depends on author_email. Returns [] if the column is missing."""
    try:
        return mysql_db.db_fetch(sql, params)
    except Exception as exc:
        if "author_email" in str(exc).lower() or "unknown column" in str(exc).lower():
            log.warning("repo_merge_requests.author_email not found — run ALTER TABLE to add it")
            return []
        raise


def _build_result(
    commit_rows: list,
    pr_rows: list,
    email_key: str,
) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}

    for row in commit_rows:
        email = (row.get(email_key) or "").strip().lower()
        if not email:
            continue
        result[email] = {
            "loc_added": int(row.get("loc_added") or 0),
            "loc_removed": int(row.get("loc_removed") or 0),
            "commits": int(row.get("commits") or 0),
            "prs": 0,
        }

    for row in pr_rows:
        email = (row.get(email_key) or "").strip().lower()
        if not email:
            continue
        entry = result.setdefault(
            email, {"loc_added": 0, "loc_removed": 0, "commits": 0, "prs": 0}
        )
        entry["prs"] = int(row.get("prs") or 0)

    return result


def fetch_pr_lifecycle(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Fetch merged PRs with lifecycle timestamps for lead time calculations.

    Returns one row per merged PR with creation_date, merged_at,
    first_approval_at, author_email (from commits), LOC, and earliest commit date.
    repo_merge_requests does not have author_email; we derive it from repo_commits.
    """
    return mysql_db.db_fetch(
        """
        SELECT rmr.id_merge_request,
               rmr.creation_date,
               rmr.merged_at,
               rmr.first_approval_at,
               rmr.lines_added,
               rmr.lines_deleted,
               rmr.state,
               MIN(rc.commit_creation_date) AS first_commit_at,
               MIN(rc.author_email)         AS author_email
        FROM repo_merge_requests rmr
        LEFT JOIN repo_commits rc ON rc.author_app_id = rmr.author_app_id
        WHERE rmr.merged_at IS NOT NULL
          AND DATE(rmr.merged_at) BETWEEN %s AND %s
        GROUP BY rmr.id_merge_request
        ORDER BY rmr.merged_at
        """,
        (start_date, end_date),
    )


def fetch_ai_author_emails(org_id: int, by_actor: List[Dict[str, Any]]) -> set:
    """Return lowercased emails of Claude Code users for this org.

    Combines OTLP actor emails with git emails resolved via user_identity_map.
    """
    emails = set()
    for actor in by_actor:
        email = (actor.get("email_address") or "").strip().lower()
        if email:
            emails.add(email)

    rows = mysql_db.db_fetch(
        """
        SELECT DISTINCT uim.git_email
        FROM user_identity_map uim
        WHERE uim.auth_token_sha256 IN (
            SELECT DISTINCT authorization_token_sha256
            FROM claude_code_otel_ingest
            WHERE id_organization = %s
        )
        """,
        (org_id,),
    )
    for r in rows:
        email = (r.get("git_email") or "").strip().lower()
        if email:
            emails.add(email)

    return emails


def fetch_total_prs(start_date: str, end_date: str) -> int:
    """Count all PRs in the date range regardless of author attribution."""
    row = mysql_db.db_get(
        """
        SELECT COUNT(DISTINCT id_merge_request) AS total
        FROM repo_merge_requests
        WHERE DATE(creation_date) BETWEEN %s AND %s
        """,
        (start_date, end_date),
    )
    return int((row or {}).get("total") or 0)


def _build_otel_to_git_map() -> Dict[str, str]:
    """Build {otel_email_lower: git_email_lower} from user_identity_map + OTLP payloads.

    Uses auth_token_sha256 to bridge the two identities.
    Parses OTLP JSON in Python (same as otlp_parser.py) to avoid JSON_TABLE issues.
    Returns empty dict when user_identity_map is empty.
    """
    import json as _json

    uim_rows = mysql_db.db_fetch(
        "SELECT git_email, auth_token_sha256 FROM user_identity_map", ()
    )
    if not uim_rows:
        return {}

    result: Dict[str, str] = {}
    for uim in uim_rows:
        git_email = (uim.get("git_email") or "").strip().lower()
        token = uim.get("auth_token_sha256") or ""
        if not git_email or not token:
            continue

        otel_row = mysql_db.db_get(
            "SELECT payload_text FROM claude_code_otel_ingest "
            "WHERE authorization_token_sha256 = %s "
            "AND payload_text LIKE '%%user.email%%' LIMIT 1",
            (token,),
        )
        if not otel_row:
            continue

        try:
            payload = _json.loads(otel_row.get("payload_text") or "")
        except (ValueError, TypeError):
            continue

        otel_email = None
        for rl in payload.get("resourceLogs", []):
            for sl in rl.get("scopeLogs", []):
                for lr in sl.get("logRecords", []):
                    for attr in lr.get("attributes", []):
                        if attr.get("key") == "user.email":
                            otel_email = (attr.get("value", {}).get("stringValue") or "").strip().lower()
                            break
                    if otel_email:
                        break
                if otel_email:
                    break
            if otel_email:
                break

        if otel_email and otel_email != git_email:
            result[otel_email] = git_email

    return result


def enrich_actors_with_git(
    by_actor: List[Dict[str, Any]],
    git_data: Dict[str, Dict[str, int]],
) -> None:
    """Mutate by_actor in place, overwriting LOC/commits/PRs with git-sourced values.

    git_data is keyed by both git emails and OTLP email aliases (added by fetch_by_email),
    so a simple lookup by actor email_address is enough.
    No-op when git_data is empty.
    """
    if not git_data:
        return

    for actor in by_actor:
        email = (actor.get("email_address") or "").strip().lower()
        git = git_data.get(email)
        if not git:
            continue
        loc = actor["core_metrics"]["lines_of_code"]
        loc["added"] = git["loc_added"]
        loc["removed"] = git["loc_removed"]
        actor["core_metrics"]["commits_by_claude_code"] = git["commits"]
        actor["core_metrics"]["pull_requests_by_claude_code"] = git["prs"]


__all__ = [
    "fetch_by_email",
    "fetch_pr_lifecycle",
    "fetch_ai_author_emails",
    "fetch_total_prs",
    "enrich_actors_with_git",
]
