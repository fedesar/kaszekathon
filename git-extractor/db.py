"""
db.py – MySQL helpers (PyMySQL) for ai_governance tables.
"""

import os
import logging
import pymysql

logger = logging.getLogger(__name__)


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


# ── Repositories ────────────────────────────────────────────

UPSERT_REPO = """
INSERT INTO repositories
    (repository_app_id, repository_name, owner, description, path,
     default_branch, last_updated, active, repository_creation_date)
VALUES
    (%(repository_app_id)s, %(repository_name)s, %(owner)s, %(description)s, %(path)s,
     %(default_branch)s, %(last_updated)s, %(active)s, %(repository_creation_date)s)
ON DUPLICATE KEY UPDATE
    repository_name          = VALUES(repository_name),
    owner                    = VALUES(owner),
    description              = VALUES(description),
    path                     = VALUES(path),
    default_branch           = VALUES(default_branch),
    last_updated             = VALUES(last_updated),
    active                   = VALUES(active),
    repository_creation_date = VALUES(repository_creation_date),
    updated_at               = NOW()
"""


def upsert_repository(conn, repo: dict) -> int:
    """Insert or update a repository. Returns id_repository."""
    with conn.cursor() as cur:
        cur.execute(UPSERT_REPO, repo)
        # If inserted, last row id; if updated, fetch by app_id
        if cur.lastrowid:
            return cur.lastrowid
        cur.execute(
            "SELECT id_repository FROM repositories WHERE repository_app_id = %s",
            (repo["repository_app_id"],),
        )
        return cur.fetchone()["id_repository"]


# ── Pull Requests (merge_requests) ──────────────────────────

UPSERT_MR = """
INSERT INTO repo_merge_requests
    (id_repository, merge_request_app_id, title, description, url, state,
     creation_date, merged_at, first_approval_at, first_approval_by,
     closed_at, source_branch, target_branch, comments_count,
     lines_added, lines_deleted, author_app_id, author_name)
VALUES
    (%(id_repository)s, %(merge_request_app_id)s, %(title)s, %(description)s,
     %(url)s, %(state)s, %(creation_date)s, %(merged_at)s,
     %(first_approval_at)s, %(first_approval_by)s, %(closed_at)s,
     %(source_branch)s, %(target_branch)s, %(comments_count)s,
     %(lines_added)s, %(lines_deleted)s, %(author_app_id)s, %(author_name)s)
ON DUPLICATE KEY UPDATE
    title              = VALUES(title),
    description        = VALUES(description),
    url                = VALUES(url),
    state              = VALUES(state),
    merged_at          = VALUES(merged_at),
    first_approval_at  = VALUES(first_approval_at),
    first_approval_by  = VALUES(first_approval_by),
    closed_at          = VALUES(closed_at),
    comments_count     = VALUES(comments_count),
    lines_added        = VALUES(lines_added),
    lines_deleted      = VALUES(lines_deleted),
    updated_at         = NOW()
"""


def upsert_merge_request(conn, mr: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(UPSERT_MR, mr)
        if cur.lastrowid:
            return cur.lastrowid
        cur.execute(
            "SELECT id_merge_request FROM repo_merge_requests "
            "WHERE id_repository = %s AND merge_request_app_id = %s",
            (mr["id_repository"], mr["merge_request_app_id"]),
        )
        return cur.fetchone()["id_merge_request"]


# ── Commits ─────────────────────────────────────────────────

UPSERT_COMMIT = """
INSERT INTO repo_commits
    (id_repository, merge_request_id, commit_app_id, title, message,
     author_app_id, author_name, author_email,
     commit_creation_date, lines_added, lines_deleted)
VALUES
    (%(id_repository)s, %(merge_request_id)s, %(commit_app_id)s,
     %(title)s, %(message)s, %(author_app_id)s, %(author_name)s,
     %(author_email)s, %(commit_creation_date)s,
     %(lines_added)s, %(lines_deleted)s)
ON DUPLICATE KEY UPDATE
    merge_request_id     = VALUES(merge_request_id),
    title                = VALUES(title),
    message              = VALUES(message),
    lines_added          = VALUES(lines_added),
    lines_deleted        = VALUES(lines_deleted),
    updated_at           = NOW()
"""


def upsert_commit(conn, commit: dict):
    with conn.cursor() as cur:
        cur.execute(UPSERT_COMMIT, commit)


# ── Unique-index migration (run once) ──────────────────────

MIGRATION_INDEXES = [
    (
        "repositories",
        "uq_repository_app_id",
        "CREATE UNIQUE INDEX uq_repository_app_id ON repositories (repository_app_id)",
    ),
    (
        "repo_merge_requests",
        "uq_mr_repo_app_id",
        "CREATE UNIQUE INDEX uq_mr_repo_app_id ON repo_merge_requests (id_repository, merge_request_app_id)",
    ),
    (
        "repo_commits",
        "uq_commit_app_id",
        "CREATE UNIQUE INDEX uq_commit_app_id ON repo_commits (commit_app_id)",
    ),
]


def _index_exists(cur, table: str, index_name: str) -> bool:
    cur.execute("SHOW INDEX FROM %s WHERE Key_name = %%s" % table, (index_name,))
    return cur.fetchone() is not None


def ensure_unique_indexes(conn):
    """Create unique indexes needed for ON DUPLICATE KEY UPDATE."""
    with conn.cursor() as cur:
        for table, name, ddl in MIGRATION_INDEXES:
            if _index_exists(cur, table, name):
                logger.info("Index %s already exists, skipping", name)
                continue
            cur.execute(ddl)
            logger.info("Created index %s", name)
    conn.commit()
