# Environment Variables

## Backend

File: `backend/.env` (local development) | SSM Parameter Store (production)

### Database Connection

| Variable | Description | Required | Default | SSM Path |
|----------|-------------|----------|---------|----------|
| `LEANMOTE_DB_HOST` | MySQL/RDS server hostname | Yes | — | `/leanmote/db/host` |
| `LEANMOTE_DB_USER` | Database user | Yes | — | `/leanmote/db/user` |
| `LEANMOTE_DB_NAME` | Database name | Yes | — | `/leanmote/db/name` |
| `LEANMOTE_DB_PORT` | MySQL port | No | `3306` | — |
| `LEANMOTE_DB_PASSWORD` | DB password (if set, used instead of IAM auth) | No | — (IAM fallback) | — |
| `LEANMOTE_AWS_REGION` | AWS region for boto3 / IAM token | No | `us-east-1` | — |

**Note on DB authentication:**
- If `LEANMOTE_DB_PASSWORD` is defined → uses direct password
- If `LEANMOTE_DB_PASSWORD` is NOT defined → generates IAM token via `boto3.rds.generate_db_auth_token()`

### API Authentication

| Variable | Description | Required | Default | SSM Path |
|----------|-------------|----------|---------|----------|
| `DASHBOARD_API_KEY` | API key to validate requests (`X-Api-Key` header) | No | — (open mode) | `/leanmote/dashboard/api-key` |

**Note:** If not defined, all requests pass without validation (development mode).

### Tool Pricing (ROI)

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_CODE_PRICE_PER_SEAT` | Monthly price per Claude Code license (USD) | `25` |
| `COPILOT_PRICE_PER_SEAT` | Monthly price per GitHub Copilot license (USD) | `19` |
| `CURSOR_PRICE_PER_SEAT` | Monthly price per Cursor license (USD) | `20` |

### Tool Seats (ROI)

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_CODE_SEATS` | Total Claude Code licenses | `0` (falls back to active_users) |
| `COPILOT_SEATS` | Total GitHub Copilot licenses | `0` |
| `CURSOR_SEATS` | Total Cursor licenses | `0` |

**Note:** If `CLAUDE_CODE_SEATS` is `0`, the system uses the detected active user count as the number of seats.

---

## Frontend

File: `frontend/.env.development` (development) | `frontend/.env.production` (production)

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | No | `""` (empty = uses Vite proxy) |
| `VITE_API_KEY` | API key sent in `X-Api-Key` header | No | `""` |
| `VITE_DEFAULT_ORG_ID` | Default organization ID | No | `1` |

**Note on `VITE_API_BASE_URL`:**
- In development: leave empty to use the Vite proxy (requests go to `localhost:3001`)
- In production: full API Gateway URL (e.g., `https://abc123.execute-api.us-east-1.amazonaws.com`)

---

## Example: Full .env for development

### backend/.env

```env
# Database
LEANMOTE_DB_HOST=localhost
LEANMOTE_DB_USER=root
LEANMOTE_DB_NAME=leanmote
LEANMOTE_DB_PORT=3306
LEANMOTE_DB_PASSWORD=my-local-password

# Auth
DASHBOARD_API_KEY=dev-key

# ROI pricing (optional, has defaults)
CLAUDE_CODE_PRICE_PER_SEAT=25
COPILOT_PRICE_PER_SEAT=19
CURSOR_PRICE_PER_SEAT=20

# ROI seats (optional)
CLAUDE_CODE_SEATS=10
COPILOT_SEATS=8
CURSOR_SEATS=5
```

### frontend/.env.development

```env
VITE_API_BASE_URL=
VITE_API_KEY=dev-key
VITE_DEFAULT_ORG_ID=1
```

---

## Example: Production variables (SSM)

```bash
# Create SSM parameters
aws ssm put-parameter --name "/leanmote/db/host" --value "my-rds.cluster-abc.us-east-1.rds.amazonaws.com" --type String
aws ssm put-parameter --name "/leanmote/db/user" --value "leanmote_app" --type String
aws ssm put-parameter --name "/leanmote/db/name" --value "leanmote_prod" --type String
aws ssm put-parameter --name "/leanmote/dashboard/api-key" --value "secure-production-api-key" --type SecureString
```

### frontend/.env.production

```env
VITE_API_BASE_URL=https://abc123.execute-api.us-east-1.amazonaws.com
VITE_API_KEY=secure-production-api-key
VITE_DEFAULT_ORG_ID=1
```
