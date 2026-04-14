# System Architecture

## Overview

AI Governance follows a serverless three-layer architecture: a frontend SPA (Single Page Application) consuming a REST API served by AWS Lambda, backed by a MySQL database on AWS RDS.

```
┌──────────────────────────────────────────────────────────────┐
│                    Claude Code (Developer)                     │
│                Emits native OTEL telemetry                     │
└─────────────────────────┬────────────────────────────────────┘
                          │ OTLP HTTP (logs + metrics)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                    OTEL Collector / Ingest                     │
│              Stores raw payloads in MySQL                      │
└─────────────────────────┬────────────────────────────────────┘
                          │ INSERT -> claude_code_otel_ingest
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                     MySQL (AWS RDS)                            │
│                                                               │
│  claude_code_otel_ingest  <- Raw OTEL telemetry               │
│  user_identity_map        <- Auth token -> git email          │
│  repositories             <- Repository metadata              │
│  repo_commits             <- Git commits                      │
│  repo_merge_requests      <- Git pull requests                │
└─────────────────────────┬────────────────────────────────────┘
                          │ SELECT (pymysql + IAM auth)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              Backend (AWS Lambda / Python 3.12)                │
│                                                               │
│  lambda_function.py  -> Routing + auth                        │
│  handlers/usage.py   -> Usage KPIs                            │
│  handlers/impact.py  -> Impact metrics + lead time            │
│  handlers/license_efficiency.py -> Investment + adoption      │
│  handlers/health.py  -> Health check                          │
│                                                               │
│  services/otlp_parser.py    -> OTEL payload parsing           │
│  services/git_metrics.py    -> Git metrics + identity bridge  │
│  services/mysql_db.py       -> RDS connection + IAM           │
│  services/cache.py          -> In-memory cache (TTL 5min)     │
│  functions/claude_code/normalize.py -> Per-actor aggregation  │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP JSON (X-Api-Key)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              Frontend (React 18 + Vite 4)                      │
│                                                               │
│  AIDashboard.jsx         -> Tab controller                    │
│  UsageTab                -> Sessions, users, LOC, PRs         │
│  ImpactTab               -> Lead time, AI share, PR size      │
│  LicenseEfficiencyTab    -> Investment, cost/PR, adoption     │
│  AgentsTab               -> Placeholder (Coming Soon)         │
│                                                               │
│  MUI 6 (components) + Recharts 2 (charts) + Axios (HTTP)     │
└──────────────────────────────────────────────────────────────┘
```

---

## Main Components

### 1. Telemetry Ingestion

Claude Code emits standard telemetry via OpenTelemetry (OTLP). Each HTTP payload is stored in its entirety in the `claude_code_otel_ingest` table, preserving:

- Signal type (`logs` or `metrics`)
- Full HTTP headers
- Complete JSON payload
- Hashed authorization token (SHA-256)
- Request metadata (IP, user agent, request ID)

### 2. Backend API (Lambda)

A single Lambda function serves all endpoints via HTTP API Gateway. Routing is handled in `lambda_function.py` based on path and method.

**Per-request processing pipeline:**

1. Validate `X-Api-Key` header
2. Extract parameters (`org_id`, `start_date`, `end_date`)
3. Query `claude_code_otel_ingest` by organization and date range
4. Parse OTEL payloads (`otlp_parser.py`) -> normalized records
5. Aggregate by actor (`normalize.py`) -> per-user metrics
6. Enrich with git data (`git_metrics.py`) -> real LOC, commits, PRs
7. Compute summary metrics (`normalize.py`)
8. Return JSON to frontend

### 3. Frontend Dashboard

React SPA with four analytics tabs. Each tab makes an independent call to its corresponding endpoint and renders data with Recharts.

### 4. Database

MySQL 8.0 on RDS with five tables covering two domains:
- **OTEL Telemetry:** `claude_code_otel_ingest`
- **Git Data:** `repositories`, `repo_commits`, `repo_merge_requests`
- **Identity Bridge:** `user_identity_map` (connects OTEL tokens to git emails)

---

## End-to-End Data Flow

```
Developer uses Claude Code
    |
Claude Code emits OTEL (logs: sessions, commits, PRs, LOC, costs, tools)
    |
Payload is stored in claude_code_otel_ingest
    |
Frontend requests data (GET /api/v1/usage?org_id=1&start_date=...&end_date=...)
    |
Lambda queries raw payloads by org and date range
    |
otlp_parser.py extracts attributes from OTEL log records
    |
Groups by (email, date) -> normalized record per group
    |
normalize.py aggregates records by actor (user) -> totals
    |
git_metrics.py enriches with real git data (LOC, commits, PRs)
    |
Handler computes KPIs, trends, breakdowns
    |
Frontend renders charts and tables
```

---

## Design Decisions

| Decision | Reason |
|----------|--------|
| **Store raw OTEL payload** | Allows reprocessing without data loss; OTEL schema can evolve |
| **Parse on-read (no prior ETL)** | Simplifies architecture; acceptable for hackathon volumes |
| **IAM auth for RDS** | 15-minute temporary tokens; no passwords in code |
| **Thread-local DB connections** | Reuses connections across Lambda invocations in the same container |
| **Costs in micro-USD** | Avoids float truncation in DB; `0.0166836 USD -> 16683 micro-USD` |
| **In-memory cache (5 min TTL)** | Avoids re-parsing thousands of OTEL payloads on consecutive requests |
| **Mono-Lambda with internal routing** | Single deployment; simplifies SAM template and cold starts |
| **Multi-tenancy by org_id** | All queries filter by `id_organization`; query-level isolation |
| **max(otel, git) for totals** | Ensures total is never less than the AI-attributed portion |

---

## Dependency Diagram (Backend)

```
lambda_function.py
├── handlers/health.py             -> services/mysql_db.py
├── handlers/usage.py              -> services/mysql_db.py
│                                  -> services/otlp_parser.py
│                                  -> services/git_metrics.py
│                                  -> functions/claude_code/normalize.py
├── handlers/impact.py             -> services/mysql_db.py
│                                  -> services/otlp_parser.py
│                                  -> services/git_metrics.py
│                                  -> functions/claude_code/normalize.py
├── handlers/license_efficiency.py -> services/mysql_db.py
│                                  -> services/otlp_parser.py
│                                  -> services/git_metrics.py
│                                  -> functions/claude_code/normalize.py
└── services/
    ├── mysql_db.py          -> boto3 (IAM token), pymysql
    ├── otlp_parser.py       -> json (stdlib)
    ├── git_metrics.py       -> services/mysql_db.py
    ├── cache.py             -> threading (stdlib)
    └── logging_utils.py     -> json (stdlib)
```
