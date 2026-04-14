"""
github_client.py – Thin wrapper over GitHub REST API v3 with auto-pagination.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Iterator

import requests

logger = logging.getLogger(__name__)

BASE = "https://api.github.com"
PER_PAGE = 100


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    return s


def _paginate(session: requests.Session, url: str, params: dict = None) -> Iterator[dict]:
    """Yield every item across all pages."""
    params = dict(params or {})
    params.setdefault("per_page", PER_PAGE)
    while url:
        resp = session.get(url, params=params)
        resp.raise_for_status()
        yield from resp.json()
        url = resp.links.get("next", {}).get("url")
        params = {}  # params are already baked into the 'next' URL


# ── Repos ───────────────────────────────────────────────────

def list_repos(owner: str, repo_filter: list[str] | None = None) -> list[dict]:
    """Return repo metadata. If repo_filter is set, only those repos."""
    session = _session()

    if repo_filter:
        repos = []
        for name in repo_filter:
            resp = session.get(f"{BASE}/repos/{owner}/{name}")
            resp.raise_for_status()
            repos.append(resp.json())
        return repos

    # Try as org first, fall back to user
    try:
        return list(_paginate(session, f"{BASE}/orgs/{owner}/repos", {"type": "all"}))
    except requests.HTTPError:
        return list(_paginate(session, f"{BASE}/users/{owner}/repos", {"type": "all"}))


def normalize_repo(raw: dict) -> dict:
    return {
        "repository_app_id":        str(raw["id"]),
        "repository_name":          raw["full_name"],
        "owner":                    raw["owner"]["login"],
        "description":              (raw.get("description") or "")[:1024],
        "path":                     raw["html_url"],
        "default_branch":           raw.get("default_branch"),
        "last_updated":             _parse_dt(raw.get("pushed_at")),
        "active":                   0 if raw.get("archived") else 1,
        "repository_creation_date": _parse_dt(raw.get("created_at")),
    }


# ── Pull Requests ───────────────────────────────────────────

def list_pull_requests(owner: str, repo: str, since: str | None = None) -> list[dict]:
    """Fetch PRs (all states). `since` is ISO-8601 — GitHub doesn't support it
    natively on /pulls, so we sort by updated desc and stop early."""
    session = _session()
    prs: list[dict] = []
    since_dt = datetime.fromisoformat(since) if since else None

    for pr in _paginate(
        session,
        f"{BASE}/repos/{owner}/{repo}/pulls",
        {"state": "all", "sort": "updated", "direction": "desc"},
    ):
        if since_dt and _parse_dt(pr.get("updated_at")) and _parse_dt(pr["updated_at"]) < since_dt:
            break
        prs.append(pr)

    # Enrich with review + diff stats (needs extra calls)
    for pr in prs:
        number = pr["number"]
        # First approval
        try:
            reviews = list(
                _paginate(session, f"{BASE}/repos/{owner}/{repo}/pulls/{number}/reviews")
            )
            approved = [r for r in reviews if r["state"] == "APPROVED"]
            if approved:
                approved.sort(key=lambda r: r["submitted_at"])
                pr["_first_approval_at"] = approved[0]["submitted_at"]
                pr["_first_approval_by"] = approved[0]["user"]["login"]
            else:
                pr["_first_approval_at"] = None
                pr["_first_approval_by"] = None
        except Exception:
            pr["_first_approval_at"] = None
            pr["_first_approval_by"] = None

        # Lines added / deleted
        try:
            detail = session.get(f"{BASE}/repos/{owner}/{repo}/pulls/{number}")
            detail.raise_for_status()
            d = detail.json()
            pr["_additions"] = d.get("additions", 0)
            pr["_deletions"] = d.get("deletions", 0)
            pr["_comments"]  = d.get("comments", 0) + d.get("review_comments", 0)
        except Exception:
            pr["_additions"] = 0
            pr["_deletions"] = 0
            pr["_comments"]  = 0

    return prs


def normalize_pr(raw: dict, id_repository: int) -> dict:
    state = raw["state"]  # open / closed
    if raw.get("merged_at"):
        state = "merged"

    return {
        "id_repository":          id_repository,
        "merge_request_app_id":   str(raw["id"]),
        "title":                  (raw.get("title") or "")[:512],
        "description":            raw.get("body") or "",
        "url":                    raw.get("html_url") or "",
        "state":                  state,
        "creation_date":          _parse_dt(raw.get("created_at")),
        "merged_at":              _parse_dt(raw.get("merged_at")),
        "first_approval_at":      _parse_dt(raw.get("_first_approval_at")),
        "first_approval_by":      raw.get("_first_approval_by"),
        "closed_at":              _parse_dt(raw.get("closed_at")),
        "source_branch":          raw.get("head", {}).get("ref"),
        "target_branch":          raw.get("base", {}).get("ref"),
        "comments_count":         raw.get("_comments", 0),
        "lines_added":            raw.get("_additions", 0),
        "lines_deleted":          raw.get("_deletions", 0),
        "author_app_id":          str(raw["user"]["id"]) if raw.get("user") else None,
        "author_name":            raw["user"]["login"] if raw.get("user") else None,
    }


# ── Commits ─────────────────────────────────────────────────

def list_commits(owner: str, repo: str, since: str | None = None) -> list[dict]:
    session = _session()
    params = {}
    if since:
        params["since"] = since

    commits = list(_paginate(session, f"{BASE}/repos/{owner}/{repo}/commits", params))

    # Enrich with diff stats
    for c in commits:
        try:
            detail = session.get(f"{BASE}/repos/{owner}/{repo}/commits/{c['sha']}")
            detail.raise_for_status()
            stats = detail.json().get("stats", {})
            c["_additions"] = stats.get("additions", 0)
            c["_deletions"] = stats.get("deletions", 0)
        except Exception:
            c["_additions"] = 0
            c["_deletions"] = 0

    return commits


def list_pr_commits(owner: str, repo: str, pr_number: int) -> list[dict]:
    """Commits belonging to a specific PR."""
    session = _session()
    return list(
        _paginate(session, f"{BASE}/repos/{owner}/{repo}/pulls/{pr_number}/commits")
    )


def normalize_commit(raw: dict, id_repository: int, merge_request_id: int | None = None) -> dict:
    commit_data = raw.get("commit", {})
    author = commit_data.get("author", {})
    message = commit_data.get("message", "")
    first_line = message.split("\n", 1)[0] if message else ""

    return {
        "id_repository":        id_repository,
        "merge_request_id":     merge_request_id,
        "commit_app_id":        raw["sha"],
        "title":                first_line[:512],
        "message":              message,
        "author_app_id":        str(raw["author"]["id"]) if raw.get("author") else None,
        "author_name":          raw["author"]["login"] if raw.get("author") else (author.get("name")),
        "author_email":         author.get("email"),
        "commit_creation_date": _parse_dt(author.get("date")),
        "lines_added":          raw.get("_additions", 0),
        "lines_deleted":        raw.get("_deletions", 0),
    }


# ── Helpers ─────────────────────────────────────────────────

def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None
