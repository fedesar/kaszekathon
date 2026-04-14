# GitHub Data Extractor → ai_governance

AWS Lambda (Python 3.11+) que extrae repos, PRs y commits de GitHub y los persiste en MySQL/Aurora.

## Estructura

```
├── lambda_function.py    # Handler principal + orquestación
├── github_client.py      # GitHub REST API v3 con paginación
├── db.py                 # Conexión MySQL + upserts idempotentes
├── requirements.txt      # requests, PyMySQL, python-dotenv
├── deploy.sh             # Script para generar .zip deployeable
└── .env.example          # Template de variables de entorno
```

## Setup

### 1. Variables de entorno

```bash
cp .env.example .env
# Editar con tus credenciales
```

### 2. Ejecución local

```bash
pip install -r requirements.txt
python lambda_function.py
```

### 3. Deploy a Lambda

```bash
chmod +x deploy.sh
./deploy.sh
# Subir github-extractor.zip a AWS Lambda
```

**Env vars en Lambda console** (o SSM/Secrets Manager):
- `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPOS`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

### 4. Trigger recomendado

EventBridge rule con cron diario:
```
cron(0 6 * * ? *)   # Todos los días a las 6 AM UTC
```

## Qué extrae

| GitHub               | Tabla                   | Key de dedup               |
|----------------------|-------------------------|----------------------------|
| Repository metadata  | `repositories`          | `repository_app_id`        |
| Pull Requests + reviews | `repo_merge_requests` | `(id_repository, merge_request_app_id)` |
| Commits (por PR + repo) | `repo_commits`       | `commit_app_id` (SHA)      |

## Rate Limits

- GitHub permite 5,000 req/h con token.
- Para repos grandes, el enrichment de PRs (reviews + diff stats) consume ~3 calls/PR.
- Considerar `SINCE` para acotar la ventana y evitar timeouts en Lambda (max 15 min).

## Notas

- Los upserts son idempotentes: se puede re-ejecutar sin duplicar data.
- `ensure_unique_indexes()` crea los índices únicos necesarios la primera vez.
- El `.env` solo se carga en local; en Lambda usar env vars nativas.
