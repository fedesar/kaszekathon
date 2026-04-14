# Database

## Overview

The system uses MySQL 8.0 on AWS RDS with five tables organized in three domains:

1. **OTEL Telemetry** — Raw Claude Code payloads
2. **Git Data** — Repositories, commits, and pull requests
3. **Identity** — Bridge between OTEL auth tokens and git emails

**Engine:** InnoDB
**Character set:** utf8mb4 (full Unicode support)
**Schema file:** `db/db.sql`

---

## Relationship Diagram

```
claude_code_otel_ingest
    │ authorization_token_sha256
    ▼
user_identity_map
    │ git_email / id_user
    ▼
repo_commits ◄──── repo_merge_requests
    │                    │
    └────────────────────┘
             │ id_repository
             ▼
        repositories
```

---

## Tables

### claude_code_otel_ingest

Stores raw OTEL payloads as sent by Claude Code. This is the source of truth for AI usage metrics.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT UNSIGNED, PK, AUTO_INCREMENT | Unique identifier |
| `created_at` | TIMESTAMP, NOT NULL, DEFAULT CURRENT_TIMESTAMP | Ingestion timestamp |
| `id_organization` | INT UNSIGNED, NOT NULL | Organization ID (multi-tenancy) |
| `signal_type` | VARCHAR(16), NOT NULL | OTEL signal type: `logs` or `metrics` |
| `http_method` | VARCHAR(8), NOT NULL | HTTP method of the OTEL request |
| `request_path` | VARCHAR(255), NOT NULL | OTEL endpoint path |
| `request_id` | VARCHAR(128), NULL | Trace ID for correlation |
| `content_type` | VARCHAR(255), NULL | Payload MIME type |
| `source_ip` | VARCHAR(64), NULL | Client IP address |
| `user_agent` | VARCHAR(512), NULL | Client user agent |
| `authorization_scheme` | VARCHAR(32), NULL | Auth scheme (Bearer, etc.) |
| `authorization_token_sha256` | CHAR(64), NOT NULL | SHA-256 hash of auth token |
| `authorization_token_hint` | VARCHAR(32), NOT NULL | Human-readable token label |
| `body_sha256` | CHAR(64), NOT NULL | Payload hash for deduplication |
| `body_size_bytes` | INT UNSIGNED, NOT NULL | Payload size in bytes |
| `payload_encoding` | VARCHAR(16), NOT NULL | Encoding format |
| `payload_text` | LONGTEXT, NOT NULL | Full OTEL JSON payload |
| `headers_json` | LONGTEXT, NOT NULL | HTTP headers as JSON |
| `query_json` | LONGTEXT, NOT NULL | Query parameters as JSON |

**Indexes:**
- `PRIMARY KEY (id)`
- `idx_id_organization (id_organization)` — Filter by organization
- `idx_signal_type (signal_type)` — Filter by signal type
- `idx_request_id (request_id)` — Trace lookup
- `idx_authorization_token_sha256 (authorization_token_sha256)` — Join with identity map

---

### user_identity_map

Bridge table connecting Claude Code auth tokens to git identities. Enables attributing OTEL activity to real commits and PRs.

| Column | Type | Description |
|--------|------|-------------|
| `id_user` | INT UNSIGNED, PK, AUTO_INCREMENT | User ID |
| `display_name` | VARCHAR(255), NOT NULL | User display name |
| `git_email` | VARCHAR(255), NOT NULL, UNIQUE | Git email (for joins with commits) |
| `auth_token_sha256` | CHAR(64), NOT NULL, UNIQUE | Claude Code token hash |
| `created_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP | Creation date |
| `updated_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP ON UPDATE | Last update date |

**Indexes:**
- `PRIMARY KEY (id_user)`
- `UNIQUE uq_auth_token (auth_token_sha256)`
- `UNIQUE uq_git_email (git_email)`

**Usage in queries:**
```sql
-- Resolve OTEL token → git email
SELECT uim.git_email
FROM user_identity_map uim
WHERE uim.auth_token_sha256 IN (
    SELECT DISTINCT authorization_token_sha256
    FROM claude_code_otel_ingest
    WHERE id_organization = ?
)
```

---

### repositories

Metadata for synced git repositories.

| Column | Type | Description |
|--------|------|-------------|
| `id_repository` | INT UNSIGNED, PK, AUTO_INCREMENT | Internal ID |
| `repository_app_id` | VARCHAR(255), NOT NULL | External ID (GitHub/GitLab) |
| `repository_name` | VARCHAR(255), NOT NULL | Repository name |
| `owner` | VARCHAR(255), NULL | Owner/organization |
| `description` | VARCHAR(1024), NULL | Description |
| `path` | VARCHAR(512), NULL | Full path |
| `default_branch` | VARCHAR(255), NULL | Main branch |
| `last_updated` | DATETIME, NULL | Last sync date |
| `active` | TINYINT(1), DEFAULT 1 | Active/inactive flag |
| `repository_creation_date` | DATETIME, NULL | Repository creation date |
| `created_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP | Created in DB |
| `updated_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP ON UPDATE | Updated in DB |

**Indexes:**
- `PRIMARY KEY (id_repository)`
- `idx_repository_app_id (repository_app_id)`

---

### repo_merge_requests

Pull requests from git repositories.

| Column | Type | Description |
|--------|------|-------------|
| `id_merge_request` | INT UNSIGNED, PK, AUTO_INCREMENT | Internal ID |
| `id_repository` | INT UNSIGNED, FK → repositories | Parent repository |
| `merge_request_app_id` | VARCHAR(255), NOT NULL | External ID (GitHub PR #) |
| `title` | VARCHAR(512), NULL | PR title |
| `description` | TEXT, NULL | PR description |
| `url` | VARCHAR(1024), NULL | PR URL |
| `state` | VARCHAR(32), NOT NULL | State: `merged`, `open`, `closed` |
| `creation_date` | DATETIME, NULL | PR creation date |
| `merged_at` | DATETIME, NULL | Merge date |
| `first_approval_at` | DATETIME, NULL | First approval date |
| `first_approval_by` | VARCHAR(255), NULL | Approver |
| `closed_at` | DATETIME, NULL | Close date |
| `source_branch` | VARCHAR(255), NULL | Source branch |
| `target_branch` | VARCHAR(255), NULL | Target branch |
| `comments_count` | INT UNSIGNED, DEFAULT 0 | Number of comments |
| `lines_added` | INT UNSIGNED, DEFAULT 0 | Lines added |
| `lines_deleted` | INT UNSIGNED, DEFAULT 0 | Lines deleted |
| `author_internal_id` | INT UNSIGNED, NULL | Internal author ID |
| `author_app_id` | VARCHAR(255), NULL | External author ID |
| `author_name` | VARCHAR(255), NULL | Author name |
| `created_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP | Created in DB |
| `updated_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP ON UPDATE | Updated in DB |

**Indexes:**
- `PRIMARY KEY (id_merge_request)`
- `idx_id_repository (id_repository)`
- `idx_merge_request_app_id (merge_request_app_id)`
- `idx_state (state)`

**Foreign Key:** `fk_mr_repository → repositories(id_repository)`

---

### repo_commits

Commits from git repositories.

| Column | Type | Description |
|--------|------|-------------|
| `id_commit` | INT UNSIGNED, PK, AUTO_INCREMENT | Internal ID |
| `id_repository` | INT UNSIGNED, FK → repositories | Parent repository |
| `merge_request_id` | INT UNSIGNED, FK → repo_merge_requests, NULL | Associated PR (optional) |
| `commit_app_id` | VARCHAR(255), NOT NULL | Commit SHA |
| `title` | VARCHAR(512), NULL | Commit title |
| `message` | TEXT, NULL | Full message |
| `author_internal_id` | INT UNSIGNED, NULL | Internal author ID |
| `author_app_id` | VARCHAR(255), NULL | External author ID |
| `author_name` | VARCHAR(255), NULL | Author name |
| `author_email` | VARCHAR(255), NULL | Author email |
| `commit_creation_date` | DATETIME, NULL | Commit date |
| `lines_added` | INT UNSIGNED, DEFAULT 0 | Lines added |
| `lines_deleted` | INT UNSIGNED, DEFAULT 0 | Lines deleted |
| `created_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP | Created in DB |
| `updated_at` | DATETIME, DEFAULT CURRENT_TIMESTAMP ON UPDATE | Updated in DB |

**Indexes:**
- `PRIMARY KEY (id_commit)`
- `idx_id_repository (id_repository)`
- `idx_merge_request_id (merge_request_id)`
- `idx_commit_app_id (commit_app_id)`

**Foreign Keys:**
- `fk_commit_repository → repositories(id_repository)`
- `fk_commit_merge_request → repo_merge_requests(id_merge_request)`

---

## Key Queries

### Fetch OTEL payloads by org and date range

```sql
SELECT signal_type, payload_text
FROM claude_code_otel_ingest
WHERE id_organization = %s
  AND DATE(created_at) BETWEEN %s AND %s
ORDER BY created_at
```

### Fetch git metrics via identity map

```sql
-- Commits
SELECT uim.git_email,
       COALESCE(SUM(rc.lines_added), 0) AS loc_added,
       COALESCE(SUM(rc.lines_deleted), 0) AS loc_removed,
       COUNT(DISTINCT rc.id_commit) AS commits
FROM user_identity_map uim
JOIN repo_commits rc ON rc.author_email = uim.git_email
WHERE uim.auth_token_sha256 IN (
    SELECT DISTINCT authorization_token_sha256
    FROM claude_code_otel_ingest
    WHERE id_organization = %s
)
  AND DATE(rc.commit_creation_date) BETWEEN %s AND %s
GROUP BY uim.git_email

-- Pull Requests
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
```

---

## Considerations

- **Multi-tenancy:** All queries filter by `id_organization` for data isolation.
- **Deduplication:** The `body_sha256` field allows detecting duplicate OTEL payloads.
- **Token security:** Auth tokens are stored as hashes (SHA-256), never in plain text.
- **Parameterized queries:** All parameters use `%s` placeholders for SQL injection prevention.
