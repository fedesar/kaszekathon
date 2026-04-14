# Backend

## Overview

The backend is a serverless Python 3.12 application deployed as a single AWS Lambda function. It exposes a REST API via HTTP API Gateway with four GET endpoints.

**File structure:**

```
backend/
├── lambda_function.py           # Entry point, routing, auth
├── local_server.py              # Local dev server (port 3001)
├── handlers/
│   ├── health.py                # GET /health
│   ├── usage.py                 # GET /api/v1/usage
│   ├── impact.py                # GET /api/v1/impact
│   └── license_efficiency.py    # GET /api/v1/license-efficiency
├── services/
│   ├── mysql_db.py              # RDS connection + IAM auth
│   ├── otlp_parser.py           # OTEL payload parser
│   ├── git_metrics.py           # Git metrics via identity map
│   ├── cache.py                 # In-memory cache with TTL
│   └── logging_utils.py         # Structured JSON logging
├── functions/
│   └── claude_code/
│       └── normalize.py         # Per-actor aggregation and summary
├── template.yaml                # AWS SAM template
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables (local)
```

---

## Entry Point: lambda_function.py

The entry point receives API Gateway events and routes them to the correct handler.

**Flow:**

1. Detect if it is an API Gateway event (`requestContext` present)
2. Extract method and path from `requestContext.http`
3. Handle CORS preflight (`OPTIONS` -> 204)
4. Validate authentication (`X-Api-Key` header)
5. Route to handler:
   - `GET /health` -> `health.handle()`
   - `GET /api/v1/usage` -> `usage.handle(params)`
   - `GET /api/v1/impact` -> `impact.handle(params)`
   - `GET /api/v1/license-efficiency` -> `license_efficiency.handle(params)`
6. Return response with CORS headers

**Parameter validation:**

Parameterized endpoints require:
- `org_id` (integer, required)
- `start_date` (string YYYY-MM-DD, required)
- `end_date` (string YYYY-MM-DD, required)

---

## Handlers

### health.py

Verifies database connectivity by executing `SELECT 1` and measuring latency.

- **No parameters required**
- **Response:** `{"status": "ok", "db_ping_ms": 12.34}`

### usage.py

Returns usage KPIs, daily trends, and per-user breakdown.

**Processing pipeline:**
1. Query `claude_code_otel_ingest` by org and date range
2. Parse OTEL payloads -> normalized records
3. Aggregate by actor -> per-user metrics
4. Enrich with git data (real LOC, commits, PRs)
5. Compute analytics summary

#### How metrics are calculated

**KPIs:**

| KPI | Formula | Source |
|-----|---------|--------|
| `total_sessions` | Sum of `num_sessions` across all actors | OTEL (distinct `session.id` per actor per day) |
| `active_users` | Count of unique actors | OTEL actor count |
| `loc_added` | Sum of `lines_of_code.added` across actors | Git (overwritten by `enrich_actors_with_git`) |
| `prs_by_ai` | OTEL `pull_requests_by_claude_code` OR `fetch_total_prs()` fallback | OTEL + git fallback |
| `ai_commits` | Sum of `commits_by_claude_code` across actors | Git (overwritten by enrichment) |

**Daily trend:**

| Field | Formula | Source |
|-------|---------|--------|
| `active_users` | Count of distinct emails with OTEL activity that day | OTEL log records |
| `tokens_consumed` | Sum of `input + output + cache_creation + cache_read` tokens | OTEL `api_request` events |
| `loc_added` | `SUM(lines_added)` from `repo_commits` grouped by day | Git (`repo_commits` table) |

**Per-user tool acceptance rate:**
```
acceptance_rate = accepted_actions / (accepted_actions + rejected_actions)
```
Where actions are summed across all tools (Edit, Bash, etc.) from OTEL `tool_result` events.

**Per-user tokens consumed:**
```
tokens = SUM(input + output + cache_creation + cache_read) across all models
```

### impact.py

Returns delivery impact metrics: lead time phases, AI share breakdowns, and PR size comparison.

#### How metrics are calculated

**Lead time timeline (hours):**

Computed from `repo_merge_requests` lifecycle timestamps, grouped by ISO week and split by AI vs non-AI author.

| Phase | Formula |
|-------|---------|
| `lead_time` | `(merged_at - creation_date)` in hours |
| `coding` | `(creation_date - first_commit_at)` in hours |
| `waiting_for_review` | `(first_approval_at - creation_date)` in hours |
| `in_review` | `(merged_at - first_approval_at)` in hours |
| `ready_to_deploy` | `0` (not yet available) |

Each phase is averaged across all PRs in that week for the AI or non-AI bucket.

**AI author classification:** An author is classified as "AI" if their email appears in:
1. OTEL actor emails (from `build_actor_usage`)
2. Git emails resolved via `user_identity_map` for the org

**AI share breakdowns:**

| Metric | Formula |
|--------|---------|
| `ai_prs_pct` | `(ai_prs / total_prs) * 100` |
| `ai_commits_pct` | `(ai_commits / total_commits) * 100` |
| `ai_loc_pct` | `(ai_loc / total_loc) * 100` |

Where:
- `ai_*` values come from OTEL data enriched with git metrics
- `total_*` values use `max(otel_value, git_query_result)` to ensure the total is never less than the AI portion. Git queries (`fetch_total_prs`, `fetch_total_commits`, `fetch_total_loc`) count all records regardless of AI attribution.

**PR size comparison:**
```
ai_avg_loc_per_pr     = SUM(lines_added + lines_deleted) / COUNT(prs)  -- for AI authors
non_ai_avg_loc_per_pr = SUM(lines_added + lines_deleted) / COUNT(prs)  -- for non-AI authors
```
Computed from `repo_merge_requests` merged PRs with author email resolved from `repo_commits`.

### license_efficiency.py

Returns investment summary, adoption segmentation, and delivery output.

#### How metrics are calculated

**License efficiency summary:**

| Metric | Formula |
|--------|---------|
| `total_investment_usd` | `cost_by_currency["USD"] / 1,000,000` (micro-USD to USD) |
| `cost_per_pr` | `total_investment_usd / total_prs` |
| `license_efficiency_pct` | `((total_investment_usd / total_monthly_seat_cost) * 100) - 100` |

Where:
- `total_investment_usd` is the sum of all Claude API costs from OTEL `api_request` events
- `total_prs` comes from OTEL or `fetch_total_prs()` fallback
- `total_monthly_seat_cost` is `SUM(price_per_seat * seats)` across all tools

A positive `license_efficiency_pct` means API usage cost exceeded seat costs (heavy usage). A negative value means seats are underutilized.

**Adoption segments:**

```
ratio = active_days / period_days
```

| Segment | Criteria |
|---------|----------|
| `new_users` | First activity date >= today (recently joined) |
| `power_users` | `ratio > 0.40` (active more than 40% of days) |
| `casual_users` | `ratio > 0.10` (active 10-40% of days) |
| `idle_users` | `ratio <= 0.10` (active less than 10% of days) |

**Seat utilization per tool:**
```
utilization_pct = min(active_users, seats) / seats * 100
```
Capped at 100%. Tool pricing is configurable via env vars (defaults: Claude Code $25, Copilot $19, Cursor $20).

**Cost vs delivery:** Daily count of merged PRs from `repo_merge_requests` (direct SQL query, not OTEL).

**Weekly active users:** Distinct actor keys per ISO week from OTEL activity dates.

---

## Shared Services

### mysql_db.py

Handles MySQL/RDS connections with IAM authentication support.

**Features:**
- **Thread-local connections:** Uses `threading.local()` to reuse connections across invocations in the same Lambda container.
- **Token lifecycle:** IAM token is regenerated every 14 minutes (token expires at 15).
- **Password fallback:** If `LEANMOTE_DB_PASSWORD` is defined, uses direct password instead of IAM.
- **SSL enabled:** All connections use SSL.
- **DictCursor:** Results returned as Python dictionaries.

**Public functions:**
- `db_fetch(sql, params)` -> `List[Dict]` (multiple rows)
- `db_get(sql, params)` -> `Dict | None` (single row)
- `db_execute(sql, params)` -> `int` (last inserted ID)
- `get_connection()` -> `pymysql.Connection`

### otlp_parser.py

Converts raw OTEL payloads from the DB into normalized records.

**Input:** Rows from `claude_code_otel_ingest` with `signal_type` and `payload_text`.

**Processing:**
1. Only processes rows with `signal_type = 'logs'` (metrics are skipped)
2. Navigates the OTEL structure: `resourceLogs -> scopeLogs -> logRecords[]`
3. Extracts attributes from each log record
4. Groups by `(email, date)`
5. Dispatches to handlers based on `event.name`:
   - `api_request` -> costs, tokens, model
   - `tool_result` / `tool_use_result` -> accepted/rejected per tool
   - `git_commit` -> commit counter
   - `pr_create` -> PR counter
   - `lines_of_code` -> LOC added/removed

**Cost encoding (MICRO_USD):**

Claude API costs are small floats (e.g., `0.0166836 USD`). To avoid truncation when converting to integers, they are multiplied by `1,000,000`:

```
0.0166836 USD -> 16,683 micro-USD (stored as int)
```

Handlers that return USD to the frontend divide by `MICRO_USD` (1,000,000).

### git_metrics.py

Fetches real git metrics (LOC, commits, PRs) by cross-referencing OTEL tokens with git identities.

**Identity resolution flow:**
```
claude_code_otel_ingest.authorization_token_sha256
    -> user_identity_map.auth_token_sha256
    -> user_identity_map.git_email
    -> repo_commits.author_email / repo_merge_requests.author_app_id
```

**Public functions:**

| Function | Description |
|----------|-------------|
| `fetch_by_email(org_id, start, end)` | Per-user LOC, commits, PRs. Merges identity map + direct match, max of each metric |
| `enrich_actors_with_git(by_actor, git_data)` | Overwrites OTEL metrics with git values in-place |
| `fetch_pr_lifecycle(start, end)` | Merged PRs with lifecycle timestamps for lead time |
| `fetch_ai_author_emails(org_id, by_actor)` | Set of emails for Claude Code users (OTEL + identity map) |
| `fetch_total_prs(start, end)` | Total PR count (all authors) |
| `fetch_total_commits(start, end)` | Total commit count (all authors) |
| `fetch_total_loc(start, end)` | Total lines added (all authors) |

**OTEL-to-git email mapping:** `_build_otel_to_git_map()` bridges OTEL emails (from telemetry) to git emails (from identity map) via `auth_token_sha256`. This handles cases where a developer uses different emails for Claude Code and git.

### cache.py

Simple in-memory cache with TTL to avoid re-parsing OTEL payloads on consecutive requests.

- **TTL:** 300 seconds (5 minutes)
- **Key:** `{handler_name}:{org_id}:{start_date}:{end_date}`
- **Thread-safe:** Uses `threading.Lock()`

### logging_utils.py

Structured JSON logging compatible with CloudWatch Insights.

---

## Normalize (functions/claude_code/normalize.py)

Core data aggregation module.

### build_actor_usage(records)

Aggregates normalized records by actor (user or API key).

**Input:** List of records from `otlp_parser.py`.

**Output:** List of actors with:
- `actor_key`, `actor_type`, `email_address`
- `active_days`, `dates`
- `core_metrics` (sessions, commits, LOC, PRs)
- `tool_actions` (accepted/rejected per tool)
- `model_breakdown` (cost and tokens per model)

**Sort order:** By LOC added (desc), then by sessions (desc).

### build_analytics_summary(records, by_actor)

Generates a global summary by aggregating all actors.

**Output:**
- `record_count`, `actor_count`
- `totals` (global core metrics)
- `cost_by_currency` (total cost in micro-USD by currency)
- `model_breakdown` (global cost and tokens by model)

### build_seat_usage(users, by_actor)

Cross-references a user list (seats) with usage data by actor. Identifies active seats, inactive seats, and unmatched actors.
