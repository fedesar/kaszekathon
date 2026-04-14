# API Reference

## General Information

| Property | Value |
|----------|-------|
| Base URL (production) | `https://ai-governance.leanmote.com` |
| Base URL (development) | `http://localhost:3001` |
| Protocol | HTTPS (production), HTTP (development) |
| Response format | JSON |
| Authentication | `X-Api-Key` header |
| CORS | Enabled for all origins |
| Allowed methods | GET, OPTIONS |

---

## Authentication

All endpoints require the `X-Api-Key` header with the value configured in `DASHBOARD_API_KEY`.

```
X-Api-Key: <your-api-key>
```

Also accepted as Bearer token:
```
Authorization: Bearer <your-api-key>
```

If `DASHBOARD_API_KEY` is not configured (development mode), all requests pass without validation.

**Error response (401):**
```json
{"error": "Unauthorized"}
```

---

## Common Parameters

The `/api/v1/*` endpoints require these query parameters:

| Parameter | Type | Required | Format | Description |
|-----------|------|----------|--------|-------------|
| `org_id` | integer | Yes | Numeric | Organization ID |
| `start_date` | string | Yes | `YYYY-MM-DD` | Range start |
| `end_date` | string | Yes | `YYYY-MM-DD` | Range end |

---

## Endpoints

### GET /health

Verifies database connectivity and measures latency.

**Parameters:** None (only requires `X-Api-Key`).

**Request:**
```bash
curl http://localhost:3001/health -H "X-Api-Key: dev-key"
```

**Response (200):**
```json
{"status": "ok", "db_ping_ms": 12.34}
```

---

### GET /api/v1/usage

Returns AI usage KPIs, daily trends, and per-user breakdown.

**Request:**
```bash
curl "http://localhost:3001/api/v1/usage?org_id=1&start_date=2024-01-01&end_date=2024-12-31" \
  -H "X-Api-Key: dev-key"
```

**Response (200):**

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
    {
      "date": "2024-01-01",
      "active_users": 8,
      "tokens_consumed": 250000,
      "loc_added": 1200
    }
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

**How KPIs are calculated:**

| KPI | Formula |
|-----|---------|
| `total_sessions` | Sum of distinct `session.id` per actor per day from OTEL |
| `active_users` | Count of unique actors with OTEL activity |
| `loc_added` | Sum of `lines_added` from git commits (enriched from `repo_commits`) |
| `prs_by_ai` | OTEL `pull_requests_by_claude_code` or `COUNT(repo_merge_requests)` fallback |
| `ai_commits` | Sum of `commits_by_claude_code` from enriched actor data |

---

### GET /api/v1/impact

Returns delivery impact metrics: lead time phases, AI share breakdowns, and PR size comparison.

**Request:**
```bash
curl "http://localhost:3001/api/v1/impact?org_id=1&start_date=2024-01-01&end_date=2024-12-31" \
  -H "X-Api-Key: dev-key"
```

**Response (200):**

```json
{
  "from": "2024-01-01",
  "to": "2024-12-31",
  "lead_time_timeline": [
    {
      "week": "2024-W01",
      "ai_lead_time": 24.5,
      "non_ai_lead_time": 48.2,
      "ai_coding": 2.1,
      "non_ai_coding": 4.8,
      "ai_waiting_for_review": 12.0,
      "non_ai_waiting_for_review": 20.5,
      "ai_in_review": 10.4,
      "non_ai_in_review": 22.9,
      "ai_ready_to_deploy": 0,
      "non_ai_ready_to_deploy": 0
    }
  ],
  "ai_pr_breakdown": {
    "ai_prs": 80,
    "total_prs": 120,
    "ai_pct": 66.7
  },
  "ai_commits_breakdown": {
    "ai_commits": 250,
    "total_commits": 380,
    "ai_pct": 65.8
  },
  "loc_breakdown": {
    "ai_loc": 30000,
    "total_loc": 45000,
    "ai_pct": 66.7
  },
  "pr_size_comparison": {
    "ai_avg_loc_per_pr": 375,
    "non_ai_avg_loc_per_pr": 280
  }
}
```

**How lead time phases are calculated (hours):**

| Phase | Formula | Data source |
|-------|---------|-------------|
| `lead_time` | `merged_at - creation_date` | `repo_merge_requests` |
| `coding` | `creation_date - first_commit_at` | `repo_merge_requests` + `repo_commits` |
| `waiting_for_review` | `first_approval_at - creation_date` | `repo_merge_requests` |
| `in_review` | `merged_at - first_approval_at` | `repo_merge_requests` |

Each phase is averaged across all merged PRs in that ISO week, split by AI vs non-AI author.

**How AI share is calculated:**

```
ai_pct = (ai_value / total_value) * 100
```

Where `total_value = max(otel_ai_value, git_total_query_result)` to ensure the total is never less than the AI portion.

---

### GET /api/v1/license-efficiency

Returns investment summary, adoption segmentation, and delivery output.

**Request:**
```bash
curl "http://localhost:3001/api/v1/license-efficiency?org_id=1&start_date=2024-01-01&end_date=2024-12-31" \
  -H "X-Api-Key: dev-key"
```

**Response (200):**

```json
{
  "from": "2024-01-01",
  "to": "2024-12-31",
  "license_efficiency_summary": {
    "total_investment_usd": 12500.00,
    "cost_per_pr": 104.17,
    "license_efficiency_pct": 25.5
  },
  "seats_summary": [
    {
      "tool": "claude_code",
      "tool_label": "Claude Code",
      "logo": "claude-code.svg",
      "seats": 15,
      "active_users": 12,
      "monthly_cost": 375.00,
      "price_per_seat": 25.0,
      "utilization_pct": 80.0
    }
  ],
  "adoption_segments": {
    "power_users": 5,
    "casual_users": 7,
    "idle_users": 2,
    "new_users": 1
  },
  "cost_vs_delivery": [
    {"date": "2024-01-01", "prs_merged": 3}
  ],
  "weekly_active_users": [
    {"week": "2024-W01", "active_users": 8}
  ]
}
```

**How license efficiency metrics are calculated:**

| Metric | Formula |
|--------|---------|
| `total_investment_usd` | `SUM(api_request costs) / 1,000,000` (micro-USD to USD) |
| `cost_per_pr` | `total_investment_usd / total_prs` |
| `license_efficiency_pct` | `((total_investment_usd / total_monthly_seat_cost) * 100) - 100` |
| `utilization_pct` | `min(active_users, seats) / seats * 100` (capped at 100%) |

**Adoption segments:**

| Segment | Criteria |
|---------|----------|
| `new_users` | First activity date >= today |
| `power_users` | Active days / period days > 40% |
| `casual_users` | Ratio > 10% |
| `idle_users` | Ratio <= 10% |

---

## Error Codes

| Code | Meaning | Cause |
|------|---------|-------|
| 400 | Bad Request | Missing or invalid parameters |
| 401 | Unauthorized | Invalid or missing API key |
| 404 | Not Found | Non-existent endpoint |
| 500 | Internal Server Error | Unhandled handler error |
| 503 | Service Unavailable | DB connectivity failure (/health only) |

---

## Response Headers (CORS)

All responses include:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: Content-Type,X-Api-Key,Authorization
Access-Control-Allow-Methods: GET,OPTIONS
Content-Type: application/json
```
