# Leanmote — AI Governance Dashboard

Built for the **Kaszek x Anthropic x Digital House Hackathon**.

Leanmote is a serverless analytics dashboard that helps engineering organizations track AI code assistant adoption, measure real impact on delivery speed, and calculate return on investment — all in one place.

---

## What it does

Engineering leaders often invest in AI coding tools (Claude Code, GitHub Copilot, Cursor) without a clear way to measure results. Leanmote solves that by ingesting OpenTelemetry telemetry from those tools and surfacing three key dimensions:

| Tab | What you see |
|-----|-------------|
| **AI Usage** | Sessions, active users, lines of code added, PRs and commits attributed to AI |
| **AI Impact** | Lead time trends, AI vs non-AI PR/commit/LOC share, delivery correlation |
| **AI ROI** | Total seat investment, cost per PR, ROI %, adoption segments, tool utilization |
| **AI Agents** | (Coming soon) Agent-level activity tracking |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (React + Vite)             │
│  UsageTab │ ImpactTab │ RoiTab │ AgentsTab           │
│  MUI + Recharts + Axios                              │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP (X-Api-Key)
┌─────────────────────▼───────────────────────────────┐
│             Backend (AWS Lambda / Python 3.12)       │
│                                                      │
│  /health        → handlers/health.py                 │
│  /api/v1/usage  → handlers/usage.py                  │
│  /api/v1/impact → handlers/impact.py                 │
│  /api/v1/roi    → handlers/roi.py                    │
│                                                      │
│  services/mysql_db.py   (RDS + IAM auth)             │
│  services/logging_utils.py (structured JSON logs)    │
│  functions/claude_code/normalize.py (OTEL parsing)   │
└─────────────────────┬───────────────────────────────┘
                      │ pymysql / SSL
┌─────────────────────▼───────────────────────────────┐
│          MySQL (AWS RDS)                             │
│  table: claude_code_otel_ingest                      │
└─────────────────────────────────────────────────────┘
```

---

## Tech stack

**Backend**
- Python 3.12 on AWS Lambda
- AWS SAM for infrastructure-as-code
- pymysql with RDS IAM token authentication
- boto3 for AWS SDK access
- Structured JSON logging for CloudWatch

**Frontend**
- React 18 + Vite 4
- Material UI 6 (components & theming)
- Recharts 2 (charts)
- Axios (API client)
- Day.js (date handling)

---

## Project structure

```
kaszekathon/
├── backend/
│   ├── handlers/          # One handler per API endpoint
│   │   ├── health.py
│   │   ├── usage.py
│   │   ├── impact.py
│   │   └── roi.py
│   ├── services/          # Shared infrastructure
│   │   ├── mysql_db.py
│   │   └── logging_utils.py
│   ├── functions/
│   │   └── claude_code/
│   │       └── normalize.py   # OTEL payload normalization
│   ├── lambda_function.py     # Lambda entry point + routing
│   ├── local_server.py        # Local dev server (port 3001)
│   ├── template.yaml          # AWS SAM template
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── dashboardApi.js
    │   ├── components/
    │   │   ├── dashboard/     # AIDashboard tab controller
    │   │   ├── usage/
    │   │   ├── impact/
    │   │   ├── roi/
    │   │   └── agents/
    │   ├── App.jsx
    │   └── main.jsx
    ├── vite.config.js
    └── .env.development
```

---

## Running locally

### Prerequisites

- Python 3.12+
- Node.js 18+
- A MySQL database with the `claude_code_otel_ingest` table populated

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in your DB credentials and API key
python local_server.py
# Runs on http://localhost:3001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
# /api and /health requests are proxied to localhost:3001
```

### Verify

```bash
# Health check
curl http://localhost:3001/health

# Usage data
curl "http://localhost:3001/api/v1/usage?org_id=1&start_date=2024-01-01&end_date=2024-12-31" \
  -H "X-Api-Key: dev-key"
```

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `LEANMOTE_DB_HOST` | RDS endpoint | — |
| `LEANMOTE_DB_USER` | DB user | — |
| `LEANMOTE_DB_NAME` | DB name | — |
| `LEANMOTE_DB_PORT` | DB port | `3306` |
| `LEANMOTE_DB_PASSWORD` | DB password | — |
| `LEANMOTE_AWS_REGION` | AWS region | `us-east-1` |
| `DASHBOARD_API_KEY` | API auth key | — |
| `CLAUDE_CODE_PRICE_PER_SEAT` | Monthly seat price | `25` |
| `COPILOT_PRICE_PER_SEAT` | Monthly seat price | `19` |
| `CURSOR_PRICE_PER_SEAT` | Monthly seat price | `20` |

### Frontend (`frontend/.env.development`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend base URL (empty = use Vite proxy) |
| `VITE_API_KEY` | API key to include in requests |
| `VITE_DEFAULT_ORG_ID` | Default organization ID |

---

## Deploying to AWS

```bash
cd backend
sam build
sam deploy --guided
```

The SAM template provisions a Lambda function with HTTP API Gateway. Environment variables are resolved from AWS SSM Parameter Store at deploy time.

---

## API reference

All endpoints require `X-Api-Key` header. Parameterized endpoints require `org_id`, `start_date`, and `end_date` query params (format: `YYYY-MM-DD`).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | DB connectivity check |
| `GET` | `/api/v1/usage` | Usage KPIs, daily trends, per-user breakdown |
| `GET` | `/api/v1/impact` | Lead time, AI share, delivery correlation |
| `GET` | `/api/v1/roi` | Investment summary, adoption segments, tool costs |

---

## Team

Built with love (and very little sleep) by the **Leanmote** team at the Kaszek x Anthropic x Digital House Hackathon.
