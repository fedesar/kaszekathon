# Local Development

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 18+ |
| npm | 9+ |
| MySQL | 8.0 (local or remote) |

---

## Quick Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd kaszekathon
```

### 2. Backend

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your DB credentials
```

**Minimum `.env` content:**

```env
LEANMOTE_DB_HOST=localhost
LEANMOTE_DB_USER=root
LEANMOTE_DB_NAME=leanmote
LEANMOTE_DB_PORT=3306
LEANMOTE_DB_PASSWORD=your-password
DASHBOARD_API_KEY=dev-key
```

```bash
# Start local server
python local_server.py
# Running at http://localhost:3001
```

### 3. Database

```bash
# Create schema (from project root)
mysql -h localhost -u root -p < db/db.sql
```

### 4. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# Running at http://localhost:5173
```

**Frontend variables (`.env.development`):**

```env
VITE_API_BASE_URL=
VITE_API_KEY=dev-key
VITE_DEFAULT_ORG_ID=1
```

Empty `VITE_API_BASE_URL` makes Vite proxy requests to `localhost:3001`.

---

## Verification

### Health check

```bash
curl http://localhost:3001/health
# {"status": "ok"}
```

### Usage data

```bash
curl "http://localhost:3001/api/v1/usage?org_id=1&start_date=2024-01-01&end_date=2024-12-31" \
  -H "X-Api-Key: dev-key"
```

### Frontend in browser

Open `http://localhost:5173` — the dashboard should load and display data.

---

## Local Architecture

```
Browser (localhost:5173)
    │
    ▼
Vite Dev Server ──proxy──→ Python local_server.py (localhost:3001)
    │                              │
    │                              ▼
    │                         MySQL (localhost:3306)
    │
    └── Hot Module Replacement (React changes reflect instantly)
```

### Vite Proxy

In development, Vite proxies requests to the backend:

| Path | Target |
|------|--------|
| `/api/*` | `http://localhost:3001` (timeout: 120s) |
| `/health` | `http://localhost:3001` |

This avoids CORS issues and simulates production behavior.

---

## Useful Commands

### Backend

```bash
# Start local server
python local_server.py

# Run with specific environment variables
LEANMOTE_DB_HOST=remote-host python local_server.py
```

### Frontend

```bash
# Dev server with hot reload
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

### Database

```bash
# Connect to local MySQL
mysql -h localhost -u root -p leanmote

# Check tables
SHOW TABLES;

# Count OTEL records
SELECT COUNT(*) FROM claude_code_otel_ingest;

# View users in identity map
SELECT * FROM user_identity_map;
```

---

## Troubleshooting

### "Connection refused" on the backend

- Verify MySQL is running
- Check credentials in `.env`
- Verify the database and tables exist

### Frontend shows no data

- Verify the backend is running on port 3001
- Open DevTools → Network and check that requests reach the backend
- Verify `X-Api-Key` matches between frontend and backend

### "Unauthorized" on requests

- Verify `VITE_API_KEY` in frontend matches `DASHBOARD_API_KEY` in backend
- Both should be `dev-key` by default in development

### Backend responds but with empty data

- Verify there is data in `claude_code_otel_ingest` for the organization and date range
- Check the `org_id` (default: 1) and selected dates
