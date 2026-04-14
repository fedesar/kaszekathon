# Data Pipeline

## Overview

The data pipeline transforms raw OpenTelemetry data emitted by Claude Code into analytics metrics consumed by the frontend. The process is **on-read** (executed per API request) with a 5-minute in-memory cache.

```
Claude Code (OTEL) → DB (raw payload) → Parser → Normalization → Aggregation → API → Frontend
```

---

## Stage 1: Ingestion

Claude Code emits native telemetry via the OpenTelemetry (OTLP) protocol over HTTP.

**Signal types:**
- `logs` — Log records with structured attributes (sessions, commits, PRs, LOC, costs, tools)
- `metrics` — Aggregated metrics (not actively used; logs contain all relevant data)

Each OTEL request is stored in its entirety in `claude_code_otel_ingest`:
- Full JSON payload (`payload_text`)
- HTTP headers (`headers_json`)
- Hashed auth token (`authorization_token_sha256`)
- Metadata: IP, user agent, content type, size

**Zero-friction setup:** A single line of configuration in Claude Code to point telemetry at the collector.

---

## Stage 2: Parsing (otlp_parser.py)

Converts raw OTEL payloads into normalized records.

### OTEL structure processed

```
payload (JSON)
└── resourceLogs[]
    └── scopeLogs[]
        └── logRecords[]
            └── attributes[]  ← Data lives here
                ├── user.email
                ├── session.id
                ├── event.name       ← Event type
                ├── event.timestamp
                ├── model, cost_usd, input_tokens, output_tokens
                ├── tool.name, tool.result
                ├── lines.added, lines.removed
                └── ...
```

### Grouping

Log records are grouped by `(email, date)`. Each group accumulates:

| Metric | Source |
|--------|--------|
| Sessions | Set of unique `session.id` values |
| Costs per model | `api_request` events (cost, tokens, model) |
| Tool actions | `tool_result` events (accepted/rejected per tool) |
| LOC | `lines_of_code` events (added/removed) |
| Commits | `git_commit` events (counter) |
| PRs | `pr_create` events (counter) |

### Event handlers

| event.name | Handler | Extracted data |
|------------|---------|----------------|
| `api_request` | `_handle_api_request` | model, cost_usd, input/output/cache tokens |
| `tool_result` | `_handle_tool_result` | tool.name, outcome (accepted/rejected) |
| `tool_use_result` | `_handle_tool_result` | (alias for tool_result) |
| `git_commit` | `_handle_commit` | Increments commit counter |
| `pr_create` | `_handle_pr` | Increments PR counter |
| `lines_of_code` | `_handle_loc` | lines.added, lines.removed |

### Cost encoding

Claude API costs are very small floats. To avoid precision loss when converting to integers:

```
Real USD:   0.0166836
micro-USD:  0.0166836 x 1,000,000 = 16,683 (stored as int)

# To convert back to USD:
16,683 / 1,000,000 = 0.016683 USD
```

Constant: `MICRO_USD = 1_000_000`

### Output: Normalized record

```python
{
    "actor": {
        "type": "user_actor",
        "email_address": "dev@company.com",
        "api_key_name": None
    },
    "date": "2024-03-15",
    "terminal_type": "vscode",
    "organization_id": "1",
    "core_metrics": {
        "num_sessions": 3,
        "commits_by_claude_code": 2,
        "lines_of_code": {"added": 150, "removed": 30},
        "pull_requests_by_claude_code": 1
    },
    "tool_actions": {
        "Edit": {"accepted": 15, "rejected": 2},
        "Bash": {"accepted": 8, "rejected": 1}
    },
    "model_breakdown": [
        {
            "model": "claude-sonnet-4-20250514",
            "estimated_cost": {"currency": "USD", "amount": 16683},
            "tokens": {
                "input": 50000,
                "output": 3000,
                "cache_creation": 10000,
                "cache_read": 40000
            }
        }
    ]
}
```

---

## Stage 3: Per-Actor Aggregation (normalize.py)

`build_actor_usage()` aggregates all records for a period by actor (user or API key).

### Process

1. Iterate normalized records
2. Classify actor: `user_actor` (by email) or `api_actor` (by API key)
3. Accumulate core metrics (sessions, commits, LOC, PRs)
4. Accumulate tool actions per tool
5. Accumulate costs and tokens per model
6. Track active dates and terminal types

### Output: Aggregated actor

```python
{
    "actor_key": "user:dev@company.com",
    "actor_type": "user_actor",
    "actor_label": "dev@company.com",
    "email_address": "dev@company.com",
    "active_days": 20,
    "dates": ["2024-01-02", "2024-01-03", ...],
    "core_metrics": {
        "num_sessions": 150,
        "commits_by_claude_code": 45,
        "lines_of_code": {"added": 5000, "removed": 800},
        "pull_requests_by_claude_code": 12
    },
    "tool_actions": {
        "Bash": {"accepted": 200, "rejected": 15},
        "Edit": {"accepted": 350, "rejected": 25}
    },
    "model_breakdown": [
        {
            "model": "claude-sonnet-4-20250514",
            "estimated_cost_by_currency": {"USD": 500000},
            "tokens": {"input": 1500000, "output": 100000, ...}
        }
    ]
}
```

---

## Stage 4: Git Enrichment (git_metrics.py)

Overwrites OTEL metrics with real git data (more reliable).

### Identity resolution flow

```
OTEL: authorization_token_sha256
  → user_identity_map: auth_token_sha256 → git_email
    → repo_commits: author_email → LOC, commits
    → repo_merge_requests: author_internal_id → PRs
```

### Dual strategy

1. **Primary:** `_fetch_via_identity_map()` — Uses `user_identity_map` to cross-reference tokens with git emails. Scoped by organization.
2. **Fallback:** `_fetch_direct()` — Direct match by `repo_commits.author_email` when the identity map is empty.

### Enrichment

`enrich_actors_with_git()` overwrites in-place:
- `core_metrics.lines_of_code.added` / `removed`
- `core_metrics.commits_by_claude_code`
- `core_metrics.pull_requests_by_claude_code`

---

## Stage 5: Analytics Summary (normalize.py)

`build_analytics_summary()` aggregates all actors into a global summary:

```python
{
    "record_count": 500,
    "actor_count": 15,
    "totals": {
        "num_sessions": 1250,
        "commits_by_claude_code": 380,
        "lines_of_code": {"added": 45000, "removed": 7500},
        "pull_requests_by_claude_code": 120
    },
    "cost_by_currency": {"USD": 12500000},  # micro-USD
    "model_breakdown": [...]
}
```

---

## Stage 6: Handler-Specific Computation

Each handler computes additional metrics:

### Usage handler
- Daily trend: active users, tokens consumed, and LOC added per day
- User list: per-user breakdown with tool acceptance rate and token consumption

### Impact handler
- Lead time timeline: grouped by ISO week, computed from real PR lifecycle data (`repo_merge_requests`), split by AI vs non-AI author
- AI share: % of PRs, commits, LOC attributed to AI (totals use `max(otel, git)`)
- PR size comparison: average LOC per PR for AI vs non-AI authors

### License efficiency handler
- Investment: total API cost (micro-USD -> USD)
- Cost per PR: `total_investment / total_prs`
- License efficiency %: `((investment / monthly_seat_cost) * 100) - 100`
- Adoption segments: power (>40%), casual (>10%), idle (<=10%), new users
- Seats summary: per tool with utilization %

---

## Cache

To avoid re-parsing OTEL payloads on consecutive requests, an in-memory cache is used:

- **TTL:** 300 seconds (5 minutes)
- **Key:** `{handler}:{org_id}:{start_date}:{end_date}`
- **Thread-safe:** `threading.Lock()`
- **Scope:** Per Lambda instance (lost on cold start)
