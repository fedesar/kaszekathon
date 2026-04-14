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
│   └── roi.py                   # GET /api/v1/roi
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
3. Handle CORS preflight (`OPTIONS` → 204)
4. Validate authentication (`X-Api-Key` header)
5. Route to handler:
   - `GET /health` → `health.handle()`
   - `GET /api/v1/usage` → `usage.handle(params)`
   - `GET /api/v1/impact` → `impact.handle(params)`
   - `GET /api/v1/roi` → `roi.handle(params)`
6. Return response with CORS headers

**Parameter validation:**

Parameterized endpoints require:
- `org_id` (integer, required)
- `start_date` (string YYYY-MM-DD, required)
- `end_date` (string YYYY-MM-DD, required)

---

## Handlers

### health.py

Verifies database connectivity by executing `SELECT 1`.

- **No parameters required**
- **Successful response:** `{"status": "ok"}`
- **Error:** HTTP 503

### usage.py

Returns usage KPIs, daily trends, and per-user breakdown.

**Processing pipeline:**
1. Query `claude_code_otel_ingest` by org and date range
2. Parse OTEL payloads → normalized records
3. Aggregate by actor → per-user metrics
4. Enrich with git data (real LOC, commits, PRs)
5. Compute analytics summary

**Response:**
```json
{
  "from": "2024-01-01",
  "to": "2024-12-31",
  "kpis": {
    "total_sessions": 1250,
    "active_users": 15,
    "loc_added": 45000,
    "prs_by_ai": 120,
    "ai_commits": 380
  },
  "daily_trend": [
    {"date": "2024-01-01", "sessions": 25, "active_users": 8}
  ],
  "user_list": [
    {
      "email": "dev@company.com",
      "active_days": 20,
      "sessions": 150,
      "loc_added": 5000,
      "prs": 12,
      "commits": 45,
      "tokens_consumed": 1500000,
      "tool_acceptance_rate": 0.87
    }
  ]
}
```

### impact.py

Returns delivery impact metrics: lead time, AI share, and correlations.

**Computed metrics:**
- **Lead time timeline:** Grouped by ISO week. Cycle time fields are zero-filled because OTEL does not contain PR lifecycle data.
- **AI share:** Percentage of PRs, commits, and LOC attributed to AI vs total.
- **Batch size:** Average LOC per PR (AI vs non-AI).
- **Delivery correlation:** Daily AI intensity vs cycle time, throughput, and bug rate.

**Response:**
```json
{
  "from": "2024-01-01",
  "to": "2024-12-31",
  "lead_time_timeline": [
    {"week": "2024-W01", "ai_lead_time": 0, "non_ai_lead_time": 0, ...}
  ],
  "ai_pr_breakdown": {"ai_prs": 120, "total_prs": 120, "ai_pct": 100.0},
  "ai_commits_breakdown": {"ai_commits": 380, "total_commits": 380, "ai_pct": 100.0},
  "loc_breakdown": {"ai_loc": 45000, "total_loc": 45000, "ai_pct": 100.0},
  "pr_size_comparison": {"ai_avg_loc_per_pr": 375, "non_ai_avg_loc_per_pr": 0},
  "delivery_correlation": [
    {"date": "2024-01-01", "ai_intensity": 0.75, "cycle_time": 0, "throughput": 5, "bug_pct": 0.0}
  ]
}
```

### roi.py

Returns ROI summary, per-tool investment breakdown, and adoption segmentation.

**Computed metrics:**
- **ROI summary:** Total investment (USD), cost per PR, ROI %.
- **Seats summary:** Per tool (Claude Code, Copilot, Cursor) — seats, active users, monthly cost, utilization.
- **Adoption segments:** Power users, casual, idle, new (based on active days / period ratio).
- **Cost vs delivery:** PRs merged per day.
- **Weekly active users:** Active users per ISO week.

**User segmentation logic:**
- `power_users`: active days ratio > 50%
- `casual_users`: ratio > 10%
- `idle_users`: ratio <= 10%
- `new_users`: first activity within the current period

**Response:**
```json
{
  "from": "2024-01-01",
  "to": "2024-12-31",
  "roi_summary": {
    "total_investment_usd": 12500.00,
    "cost_per_pr": 104.17,
    "roi_pct": 25.5
  },
  "seats_summary": [
    {
      "tool": "claude_code",
      "tool_label": "Claude Code",
      "seats": 15,
      "active_users": 12,
      "monthly_cost": 375.00,
      "price_per_seat": 25.0,
      "utilization_pct": 80.0
    }
  ],
  "adoption_segments": {"power_users": 5, "casual_users": 7, "idle_users": 2, "new_users": 1},
  "cost_vs_delivery": [{"date": "2024-01-01", "prs_merged": 3}],
  "weekly_active_users": [{"week": "2024-W01", "active_users": 8}]
}
```

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
- `db_fetch(sql, params)` → `List[Dict]` (multiple rows)
- `db_get(sql, params)` → `Dict | None` (single row)
- `db_execute(sql, params)` → `int` (last inserted ID)
- `get_connection()` → `pymysql.Connection`

### otlp_parser.py

Converts raw OTEL payloads from the DB into normalized records.

**Input:** Rows from `claude_code_otel_ingest` with `signal_type` and `payload_text`.

**Processing:**
1. Only processes rows with `signal_type = 'logs'` (metrics are skipped — logs contain all relevant data)
2. Navigates the OTEL structure: `resourceLogs → scopeLogs → logRecords[]`
3. Extracts attributes from each log record
4. Groups by `(email, date)`
5. Dispatches to handlers based on `event.name`:
   - `api_request` → costs, tokens, model
   - `tool_result` / `tool_use_result` → accepted/rejected per tool
   - `git_commit` → commit counter
   - `pr_create` → PR counter
   - `lines_of_code` → LOC added/removed

**Cost encoding (MICRO_USD):**

Claude API costs are small floats (e.g., `0.0166836 USD`). To avoid truncation when converting to integers, they are multiplied by `1,000,000`:

```
0.0166836 USD → 16,683 micro-USD (stored as int)
```

Handlers that return USD to the frontend divide by `MICRO_USD` (1,000,000).

### git_metrics.py

Fetches real git metrics (LOC, commits, PRs) by cross-referencing OTEL tokens with git identities.

**Identity resolution flow:**
```
claude_code_otel_ingest.authorization_token_sha256
    → user_identity_map.auth_token_sha256
    → user_identity_map.git_email
    → repo_commits.author_email / repo_merge_requests.author_internal_id
```

**Dual strategy:**
1. **Primary:** Join via `user_identity_map` (org-scoped, handles different git/Claude emails)
2. **Fallback:** Direct match by `repo_commits.author_email` when the identity map is empty

**`enrich_actors_with_git()` function:** Overwrites OTEL metrics with real git data (more reliable) in-place on the actor list.

### cache.py

Simple in-memory cache with TTL to avoid re-parsing OTEL payloads on consecutive requests.

- **TTL:** 300 seconds (5 minutes)
- **Key:** `{handler_name}:{org_id}:{start_date}:{end_date}`
- **Thread-safe:** Uses `threading.Lock()`

### logging_utils.py

Structured JSON logging compatible with CloudWatch Insights.

Each log includes: level, timestamp, type, status, request_id, org_id, and extra fields.

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
