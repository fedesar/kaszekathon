# Leanmote AI Governance - Project Documentation

Complete technical documentation for the **AI Governance Dashboard** by Leanmote, built for the **Kaszek x Anthropic x Digital House Hackathon**.

---

## Index

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System overview, components, and data flow |
| [Backend](backend.md) | Lambda handlers, shared services, and business logic |
| [Frontend](frontend.md) | React components, dashboard tabs, and visualizations |
| [Database](database.md) | MySQL schema, tables, relationships, and indexes |
| [API Reference](api-reference.md) | Endpoints, parameters, responses, and examples |
| [Data Pipeline](data-pipeline.md) | OTEL ingestion, parsing, normalization, and aggregation |
| [Deployment](deployment.md) | AWS infrastructure, SAM template, and production |
| [Local Development](local-development.md) | Local setup guide |
| [Security](security.md) | Authentication, authorization, and security considerations |
| [Environment Variables](environment-variables.md) | Full configuration reference |

---

## Pitch Decks

| Document | Description |
|----------|-------------|
| [Pitch 2 minutes](pitch-2min-en.md) | Short presentation script |
| [Pitch 3 minutes](pitch-3min-en.md) | Extended presentation script |

---

## What is AI Governance

AI Governance is a serverless analytics dashboard that enables engineering organizations to:

- **Track adoption** of AI tools (Claude Code, GitHub Copilot, Cursor)
- **Measure real impact** on delivery speed (lead time, throughput, quality)
- **Calculate ROI** of AI tool investment (cost per PR, license utilization)
- **Govern autonomous agents** (future roadmap)

The system captures native telemetry from Claude Code via OpenTelemetry and cross-references it with real software delivery metrics (commits, PRs, LOC) to answer the key question:

> "Is AI actually making my team deliver faster, or is it just burning tokens?"

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.12, AWS Lambda, AWS SAM, pymysql, boto3 |
| **Frontend** | React 18, Vite 4, Material UI 6, Recharts 2, Axios, Day.js |
| **Database** | MySQL 8.0 (AWS RDS), InnoDB, utf8mb4 |
| **Infrastructure** | AWS Lambda, API Gateway (HTTP API), RDS, SSM Parameter Store, CloudWatch |
| **Telemetry** | OpenTelemetry (OTLP) native from Claude Code |
