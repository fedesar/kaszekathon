# Deployment

## Overview

The system is deployed on AWS using a serverless architecture:

- **Backend:** AWS Lambda + HTTP API Gateway (via AWS SAM)
- **Frontend:** Static build (Vite) for hosting on S3 + CloudFront or similar
- **Database:** MySQL 8.0 on AWS RDS
- **Configuration:** AWS SSM Parameter Store
- **DNS:** `ai-governance.leanmote.com`

---

## AWS Architecture

```
Internet
    │
    ▼
CloudFront / S3  ← Frontend (React static build)
    │
    ▼
API Gateway (HTTP API)
    │
    ▼
Lambda Function (kaszekathon-ai-dashboard)
    │ pymysql + IAM auth token
    ▼
RDS (MySQL 8.0)
    │
SSM Parameter Store ← Configuration variables
```

---

## Backend: AWS SAM

### Template (template.yaml)

The backend infrastructure is defined as code using AWS SAM (Serverless Application Model).

**Resources created:**
- A Lambda function with HTTP API Gateway
- Four GET routes configured

**Lambda configuration:**

| Property | Value |
|----------|-------|
| Function name | `kaszekathon-ai-dashboard` |
| Runtime | Python 3.12 |
| Handler | `lambda_function.lambda_handler` |
| Timeout | 30 seconds |
| Memory | 256 MB |
| Event source | HTTP API Gateway |

**Configured endpoints:**
- `GET /health`
- `GET /api/v1/usage`
- `GET /api/v1/impact`
- `GET /api/v1/roi`

### Environment variables (SSM)

Variables are resolved from AWS SSM Parameter Store at deploy time:

| Variable | SSM Path |
|----------|----------|
| `LEANMOTE_DB_HOST` | `/leanmote/db/host` |
| `LEANMOTE_DB_USER` | `/leanmote/db/user` |
| `LEANMOTE_DB_NAME` | `/leanmote/db/name` |
| `DASHBOARD_API_KEY` | `/leanmote/dashboard/api-key` |
| `LEANMOTE_DB_PORT` | `3306` (hardcoded) |
| `LEANMOTE_AWS_REGION` | `AWS::Region` (ref) |

### Deploy commands

```bash
cd backend

# Build
sam build

# Deploy (first time, interactive)
sam deploy --guided

# Deploy (subsequent, uses samconfig.toml)
sam deploy
```

**Deploy prerequisites:**
- AWS CLI configured with valid credentials
- AWS SAM CLI installed
- SSM parameters created in the target account/region
- RDS accessible from Lambda (VPC / Security Groups)

### Create SSM parameters

```bash
aws ssm put-parameter --name "/leanmote/db/host" --value "your-rds-endpoint.amazonaws.com" --type String
aws ssm put-parameter --name "/leanmote/db/user" --value "admin" --type String
aws ssm put-parameter --name "/leanmote/db/name" --value "leanmote" --type String
aws ssm put-parameter --name "/leanmote/dashboard/api-key" --value "your-secure-api-key" --type SecureString
```

---

## Frontend: Build and Deploy

### Production build

```bash
cd frontend
npm install
npm run build
# Output: frontend/dist/
```

### Deploy to S3 + CloudFront

```bash
# Upload build to S3
aws s3 sync frontend/dist/ s3://your-frontend-bucket/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Environment variables (production)

Create `frontend/.env.production`:

```env
VITE_API_BASE_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com
VITE_API_KEY=your-production-api-key
VITE_DEFAULT_ORG_ID=1
```

---

## Database: RDS

### Initial setup

1. Create an RDS MySQL 8.0 instance
2. Configure Security Group to allow access from Lambda
3. Enable IAM authentication on the RDS instance
4. Create the database and tables:

```bash
mysql -h your-rds-endpoint.amazonaws.com -u admin -p < db/db.sql
```

### IAM Authentication

For Lambda to use IAM auth instead of password:

1. Enable IAM auth on the RDS instance
2. Create an IAM policy for `rds-db:connect`
3. Assign the policy to the Lambda execution role
4. Do not define `LEANMOTE_DB_PASSWORD` (the code falls back to IAM token)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "rds-db:connect",
      "Resource": "arn:aws:rds-db:us-east-1:ACCOUNT_ID:dbuser:DBI_RESOURCE_ID/DB_USER"
    }
  ]
}
```

---

## Production Considerations

### Performance

- **Cold start:** ~2-3 seconds (Python 3.12 + pymysql + boto3)
- **Warm invocation:** ~100-500ms depending on OTEL data volume
- **In-memory cache:** Reduces reprocessing on consecutive requests (5 min TTL)
- **Connection pooling:** Thread-local connections reused across invocations

### Monitoring

- **CloudWatch Logs:** Structured JSON logging compatible with CloudWatch Insights
- **Lambda metrics:** Invocations, errors, duration, throttles
- **Health endpoint:** `GET /health` for health checks and uptime monitoring

### Security

- IAM auth for RDS (no passwords in code)
- API key stored in SSM Parameter Store (SecureString type)
- HTTPS via API Gateway
- CORS configured (currently permissive `*` — restrict in production)

### Scalability

- Lambda scales automatically with demand
- RDS may require read replicas for high query volumes
- In-memory cache is per-instance (not shared across concurrent Lambdas)
