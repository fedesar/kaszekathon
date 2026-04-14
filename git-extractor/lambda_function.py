"""
lambda_function.py – AWS Lambda entry-point for GitHub → ai_governance extraction.

Env vars required: see .env.example

Can also be invoked locally:
    python lambda_function.py
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone

# Load .env for local dev (no-op in Lambda if file missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from github_client import (
    list_repos,
    normalize_repo,
    list_pull_requests,
    normalize_pr,
    list_commits,
    list_pr_commits,
    normalize_commit,
)
from db import (
    get_connection,
    ensure_unique_indexes,
    upsert_repository,
    upsert_merge_request,
    upsert_commit,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _build_time_window() -> tuple[str | None, str | None]:
    """Return (since, until) ISO strings from env or default last 24h."""
    since = os.environ.get("SINCE") or None
    until = os.environ.get("UNTIL") or None
    if not since:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return since, until


def lambda_handler(event=None, context=None) -> dict:
    owner = os.environ["GITHUB_OWNER"]
    repo_filter_raw = os.environ.get("GITHUB_REPOS", "").strip()
    repo_filter = [r.strip() for r in repo_filter_raw.split(",") if r.strip()] or None
    since, _until = _build_time_window()

    logger.info("Starting extraction | owner=%s repos=%s since=%s", owner, repo_filter, since)

    conn = get_connection()
    stats = {"repos": 0, "prs": 0, "commits": 0}

    try:
        # One-time: ensure unique indexes exist for idempotent upserts
        ensure_unique_indexes(conn)

        # ── 1. Repositories ──────────────────────────────────
        raw_repos = list_repos(owner, repo_filter)
        logger.info("Fetched %d repositories from GitHub", len(raw_repos))

        for raw in raw_repos:
            repo = normalize_repo(raw)
            id_repo = upsert_repository(conn, repo)
            stats["repos"] += 1

            repo_name = raw["name"]
            logger.info("Processing repo: %s (id_repository=%d)", repo_name, id_repo)

            # ── 2. Pull Requests ─────────────────────────────
            raw_prs = list_pull_requests(owner, repo_name, since=since)
            logger.info("  PRs fetched: %d", len(raw_prs))

            pr_id_map: dict[int, int] = {}  # pr_number → id_merge_request

            for raw_pr in raw_prs:
                mr = normalize_pr(raw_pr, id_repo)
                id_mr = upsert_merge_request(conn, mr)
                pr_id_map[raw_pr["number"]] = id_mr
                stats["prs"] += 1

                # Commits inside this PR
                try:
                    pr_commits = list_pr_commits(owner, repo_name, raw_pr["number"])
                    for raw_c in pr_commits:
                        c = normalize_commit(raw_c, id_repo, merge_request_id=id_mr)
                        upsert_commit(conn, c)
                        stats["commits"] += 1
                except Exception as exc:
                    logger.warning("  Error fetching PR #%d commits: %s", raw_pr["number"], exc)

            # ── 3. Repo-level commits (catch orphans) ────────
            raw_commits = list_commits(owner, repo_name, since=since)
            logger.info("  Repo commits fetched: %d", len(raw_commits))

            for raw_c in raw_commits:
                c = normalize_commit(raw_c, id_repo, merge_request_id=None)
                upsert_commit(conn, c)
                stats["commits"] += 1

        conn.commit()
        logger.info("Extraction complete: %s", stats)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "ok", "stats": stats}),
        }

    except Exception as exc:
        conn.rollback()
        logger.exception("Extraction failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }
    finally:
        conn.close()


# ── Local execution ─────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    result = lambda_handler()
    print(json.dumps(json.loads(result["body"]), indent=2))
