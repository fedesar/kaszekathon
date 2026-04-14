"""Fetch git-sourced metrics (LOC, commits, PRs) via user_identity_map.

Bridges OTLP auth tokens to git identities:
  claude_code_otel_ingest.authorization_token_sha256
      → user_identity_map.auth_token_sha256
      → user_identity_map.git_email / id_user
      → repo_commits / repo_merge_requests
"""

from __future__ import annotations

from typing import Any, Dict, List

from services import mysql_db


def fetch_by_email(org_id: int, start_date: str, end_date: str) -> Dict[str, Dict[str, int]]:
    """Return {email_lower: {loc_added, loc_removed, commits, prs}} for the date range.

    Strategy:
    1. Primary — join via user_identity_map (org-scoped, handles different git/Claude emails).
    2. Fallback — direct repo_commits.author_email match when user_identity_map is empty.
    """
    result = _fetch_via_identity_map(org_id, start_date, end_date)
    if not result:
        result = _fetch_direct(start_date, end_date)
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
        JOIN repo_merge_requests rmr ON rmr.author_internal_id = uim.id_user
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
        SELECT rmr.author_name                            AS git_email,
               COUNT(DISTINCT rmr.id_merge_request)      AS prs
        FROM repo_merge_requests rmr
        WHERE DATE(rmr.creation_date) BETWEEN %s AND %s
        GROUP BY rmr.author_name
        """,
        (start_date, end_date),
    )

    return _build_result(commit_rows, pr_rows, email_key="git_email")


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


def enrich_actors_with_git(
    by_actor: List[Dict[str, Any]],
    git_data: Dict[str, Dict[str, int]],
) -> None:
    """Mutate by_actor in place, overwriting LOC/commits/PRs with git-sourced values.

    Matches actors by email_address against git_email (both lowercased).
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


__all__ = ["fetch_by_email", "enrich_actors_with_git"]
