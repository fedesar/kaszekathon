# Frontend

## Overview

The frontend is a Single Page Application (SPA) built with React 18 and Vite 4. It presents a four-tab analytics dashboard that consumes the backend REST API.

**Stack:**
- **React 18** -- UI framework
- **Vite 4** -- Build tool and dev server
- **Material UI 6** -- Components and theming
- **Recharts 2** -- Charts (line, bar, donut, scatter)
- **Axios 1.7** -- HTTP client
- **Day.js 1.11** -- Date handling

---

## File Structure

```
frontend/src/
├── api/
│   └── dashboardApi.js             # Axios client (fetchUsage, fetchImpact, fetchLicenseEfficiency)
├── components/
│   ├── dashboard/
│   │   └── AIDashboard.jsx         # Tab controller (Usage, Impact, ROI, Agents)
│   ├── layout/
│   │   ├── TopHeader.jsx           # Logo, title, date selectors
│   │   └── Sidebar.jsx             # Navigation sidebar
│   ├── usage/
│   │   ├── UsageTab.jsx            # AI Usage main tab
│   │   ├── UsageTrendChart.jsx     # Daily trend chart (users, tokens, LOC)
│   │   └── UserActivityTable.jsx   # Per-user activity table
│   ├── impact/
│   │   ├── ImpactTab.jsx           # AI Impact main tab
│   │   ├── LeadTimeChart.jsx       # Lead time by ISO week (AI vs non-AI)
│   │   ├── ShareDonutChart.jsx     # AI share donuts (PRs, commits, LOC)
│   │   ├── BatchSizeChart.jsx      # PR size comparison (AI vs non-AI)
│   │   ├── CorrelationScatterChart.jsx  # Correlation scatter plots
│   │   └── StageSwitcher.jsx       # SDLC stage toggle
│   ├── license-efficiency/
│   │   ├── LicenseEfficiencyTab.jsx    # License Efficiency main tab
│   │   ├── ToolInvestmentCard.jsx      # Per-tool investment card
│   │   ├── AdoptionDonutChart.jsx      # Adoption segment donut
│   │   ├── DeliveryOutputChart.jsx     # PRs merged per day vs cost
│   │   └── WeeklyActiveUsersChart.jsx  # Active users per week
│   ├── agents/
│   │   └── AgentsTab.jsx           # Placeholder "Coming Soon"
│   └── common/
│       ├── KpiCard.jsx             # KPI metric card (with tooltip support)
│       ├── ChartCard.jsx           # Chart wrapper with loading/error
│       ├── LoadingSpinner.jsx      # Centered spinner
│       ├── EmptyState.jsx          # Empty / error state with retry
│       └── Icon.jsx                # SVG icon library
├── styles/
│   └── variables.css               # Global CSS variables
├── App.jsx                         # Root component
├── App.css                         # Global styles
└── main.jsx                        # Entry point with MUI theme
```

---

## Root Component: App.jsx

Manages global dashboard state:
- **orgId:** Organization ID (default: `VITE_DEFAULT_ORG_ID` or `1`)
- **startDate / endDate:** Date range (default: last 14 days)

Renders `TopHeader` (date controls) and `AIDashboard` (tabs).

---

## MUI Theme

Defined in `main.jsx`:

| Property | Value |
|----------|-------|
| Primary | `#419FFF` (blue) |
| Primary dark | `#1C2E62` |
| Secondary | `#4F7AB0` |
| Success | `#40D390` (green) |
| Warning | `#ECB22E` (yellow) |
| Error | `#FF3366` (red) |
| Background | `#F9F9F9` |
| Paper | `#FFFFFF` |
| Font family | Inter, Helvetica Neue, Arial |
| Border radius | 8px |

---

## Dashboard Tabs

### Tab 1: AI Usage (UsageTab)

Displays AI tool adoption and usage metrics.

**KPIs:**
- Total Sessions
- Active Users
- LOC Added
- PRs by AI
- AI Commits

**Charts:**
- `UsageTrendChart` -- Line/bar chart with active users, tokens consumed, and LOC added per day
- `UserActivityTable` -- Table with per-user breakdown: email, active days, sessions, LOC, PRs, commits, tokens consumed, tool acceptance rate

**Endpoint:** `GET /api/v1/usage`

### Tab 2: AI Impact (ImpactTab)

Displays AI impact on delivery speed and quality.

**Sections:**
- **Lead Time Timeline** -- Weekly AI vs non-AI lead time comparison with SDLC phase breakdown (coding, waiting for review, in review). Computed from real PR lifecycle data in `repo_merge_requests`.
- **AI Share Donuts** -- Percentage of PRs, commits, and LOC attributed to AI
- **Batch Size Comparison** -- Average LOC per PR (AI vs non-AI)

**`StageSwitcher` component:** Toggles between SDLC stages (lead_time, coding, review, deployment).

**Endpoint:** `GET /api/v1/impact`

### Tab 3: AI ROI (LicenseEfficiencyTab)

Displays license efficiency and return on investment for AI tools.

**KPIs:**
- Total Investment (USD)
- Cost per PR (USD)
- License Efficiency %

**Charts and cards:**
- `ToolInvestmentCard` -- Per-tool card (Claude Code, Copilot, Cursor) with seats, active users, monthly cost, utilization %
- `AdoptionDonutChart` -- Adoption segmentation (power users, casual, idle, new)
- `DeliveryOutputChart` -- PRs merged per day with cost overlay
- `WeeklyActiveUsersChart` -- Active users per ISO week

All KPI cards support info tooltips with contextual help text on hover.

**Endpoint:** `GET /api/v1/license-efficiency`

### Tab 4: AI Agents (AgentsTab)

**Status:** Placeholder with "Coming Soon" overlay.

**Planned features:**
- Agentic workflow tracking
- Per-agent metrics: tasks completed, cost per task, success rate
- Integration with OpenClaw, CrewAI

---

## Common Components

### KpiCard

Card displaying a metric with icon, color variant, and optional info tooltip.

**Props:**
- `title` -- Metric name
- `value` -- Numeric value
- `icon` -- SVG icon name
- `variant` -- Visual style (`highlight`, `success`, `warning`)
- `tooltip` -- Optional help text shown on hover

### ChartCard

Chart wrapper with loading and error states.

### EmptyState

Component for empty or error states with retry button.

### Icon

Inline SVG icon library: monitor, users, code, git-branch, trending-up, dollar-sign, etc.

---

## API Client (dashboardApi.js)

Configured with Axios:
- **Base URL:** `VITE_API_BASE_URL` (empty in dev -> uses Vite proxy)
- **API Key:** `VITE_API_KEY` in `X-Api-Key` header
- **Timeout:** 120 seconds

**Functions:**
- `fetchUsage(orgId, startDate, endDate, signal)` -> `GET /api/v1/usage`
- `fetchImpact(orgId, startDate, endDate, signal)` -> `GET /api/v1/impact`
- `fetchLicenseEfficiency(orgId, startDate, endDate, signal)` -> `GET /api/v1/license-efficiency`

All accept an optional `signal` (AbortController) for cancellation.

---

## Vite Configuration

```js
// vite.config.js
{
  server: {
    host: true,
    port: 5173,
    allowedHosts: ['ai-governance.leanmote.com'],
    proxy: {
      '/api':    { target: 'http://localhost:3001', changeOrigin: true, timeout: 120000 },
      '/health': { target: 'http://localhost:3001', changeOrigin: true }
    }
  }
}
```

In development, requests to `/api/*` and `/health` are proxied to the local backend on port 3001.

---

## Date Handling

- Default range is the last 14 days
- Date selectors are in `TopHeader`
- Dates are formatted as `YYYY-MM-DD`
- ISO week format (`YYYY-Www`) is used for weekly grouping
- Day.js handles ISO week calculations on the frontend
