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

If `DASHBOARD_API_KEY` is not configured on the server (development mode), all requests pass without validation.

The token is also accepted as Bearer:
```
Authorization: Bearer <your-api-key>
```

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

**Error response (400):**
```json
{"error": "org_id is required"}
{"error": "org_id must be an integer"}
{"error": "start_date and end_date are required (YYYY-MM-DD)"}
```

---

## Endpoints

### GET /health

Verifies database connectivity.

**Parameters:** None (only requires `X-Api-Key`).

**Request:**
```bash
curl http://localhost:3001/health \
  -H "X-Api-Key: dev-key"
```

**Success response (200):**
```json
{"status": "ok"}
```

**Error response (503):**
```json
{"error": "Service unavailable"}
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
      "sessions": 25,
      "active_users": 8
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

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `kpis.total_sessions` | int | Total Claude Code sessions |
| `kpis.active_users` | int | Unique active user count |
| `kpis.loc_added` | int | Lines of code added |
| `kpis.prs_by_ai` | int | Pull requests created by AI |
| `kpis.ai_commits` | int | Commits made by AI |
| `daily_trend[].date` | string | Date (YYYY-MM-DD) |
| `daily_trend[].sessions` | int | Sessions on that day |
| `daily_trend[].active_users` | int | Active users on that day |
| `user_list[].email` | string | User email |
| `user_list[].active_days` | int | Days with activity |
| `user_list[].sessions` | int | Total sessions |
| `user_list[].loc_added` | int | LOC added |
| `user_list[].prs` | int | PRs created |
| `user_list[].commits` | int | Commits made |
| `user_list[].tokens_consumed` | int | Total tokens consumed |
| `user_list[].tool_acceptance_rate` | float | Tool acceptance rate (0.0-1.0) |

---

### GET /api/v1/impact

Returns AI impact metrics on software delivery.

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
      "ai_lead_time": 0,
      "non_ai_lead_time": 0,
      "ai_coding": 0,
      "non_ai_coding": 0,
      "ai_waiting_for_review": 0,
      "non_ai_waiting_for_review": 0,
      "ai_in_review": 0,
      "non_ai_in_review": 0,
      "ai_ready_to_deploy": 0,
      "non_ai_ready_to_deploy": 0
    }
  ],
  "ai_pr_breakdown": {
    "ai_prs": 120,
    "total_prs": 120,
    "ai_pct": 100.0
  },
  "ai_commits_breakdown": {
    "ai_commits": 380,
    "total_commits": 380,
    "ai_pct": 100.0
  },
  "loc_breakdown": {
    "ai_loc": 45000,
    "total_loc": 45000,
    "ai_pct": 100.0
  },
  "pr_size_comparison": {
    "ai_avg_loc_per_pr": 375,
    "non_ai_avg_loc_per_pr": 0
  },
  "delivery_correlation": [
    {
      "date": "2024-01-01",
      "ai_intensity": 0.75,
      "cycle_time": 0,
      "throughput": 5,
      "bug_pct": 0.0
    }
  ]
}
```

**Note:** The `lead_time`, `cycle_time`, and `bug_pct` fields are zero-filled because OTEL does not contain PR lifecycle data or bug tracking information.

---

### GET /api/v1/roi

Returns ROI summary, per-tool investment breakdown, and adoption segmentation.

**Request:**
```bash
curl "http://localhost:3001/api/v1/roi?org_id=1&start_date=2024-01-01&end_date=2024-12-31" \
  -H "X-Api-Key: dev-key"
```

**Response (200):**

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
      "logo": "claude-code.svg",
      "seats": 15,
      "active_users": 12,
      "monthly_cost": 375.00,
      "price_per_seat": 25.0,
      "utilization_pct": 80.0
    },
    {
      "tool": "github_copilot",
      "tool_label": "GitHub Copilot",
      "logo": "github-copilot-logo.png",
      "seats": 0,
      "active_users": 0,
      "monthly_cost": 0.00,
      "price_per_seat": 19.0,
      "utilization_pct": 0.0
    },
    {
      "tool": "cursor_ai",
      "tool_label": "Cursor",
      "logo": "cursor-ai.png",
      "seats": 0,
      "active_users": 0,
      "monthly_cost": 0.00,
      "price_per_seat": 20.0,
      "utilization_pct": 0.0
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

**seats_summary fields:**

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Tool identifier |
| `tool_label` | string | Display name |
| `logo` | string | Logo file |
| `seats` | int | Total licenses |
| `active_users` | int | Active users (max = seats) |
| `monthly_cost` | float | Monthly cost (seats x price) |
| `price_per_seat` | float | Price per license/month |
| `utilization_pct` | float | Utilization % (max 100) |

**Adoption segments:**

| Segment | Criteria |
|---------|----------|
| `power_users` | Active days / period days > 50% |
| `casual_users` | Ratio > 10% |
| `idle_users` | Ratio <= 10% |
| `new_users` | First activity within the current period |

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
