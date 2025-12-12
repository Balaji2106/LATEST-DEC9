# Configuration Guide

This guide provides detailed explanation of all environment variables and configuration options for the AIOps RCA Assistant.

---

## 📋 Table of Contents

1. [Environment Variables Overview](#environment-variables-overview)
2. [Core Settings](#core-settings)
3. [AI Provider Configuration](#ai-provider-configuration)
4. [Database Configuration](#database-configuration)
5. [JIRA Configuration](#jira-configuration)
6. [Slack Configuration](#slack-configuration)
7. [Azure Services Configuration](#azure-services-configuration)
8. [Databricks Configuration](#databricks-configuration)
9. [Auto-Remediation Configuration](#auto-remediation-configuration)
10. [Authentication & Security](#authentication--security)
11. [Advanced Configuration](#advanced-configuration)

---

## Environment Variables Overview

All configuration is done via environment variables in a `.env` file located in `genai_rca_assistant/` directory.

**File Location:** `genai_rca_assistant/.env`

### Configuration Priorities

1. Environment variables (highest priority)
2. `.env` file values
3. Default values in code (lowest priority)

---

## Core Settings

### PUBLIC_BASE_URL
**Purpose:** Base URL where the RCA application is accessible

**Required:** Yes

**Default:** `http://localhost:8000`

**Examples:**
```bash
# Local development
PUBLIC_BASE_URL=http://localhost:8000

# Production with domain
PUBLIC_BASE_URL=https://aiops-rca.company.com

# Azure App Service
PUBLIC_BASE_URL=https://your-app.azurewebsites.net
```

**Used for:**
- Generating callback URLs for webhooks
- Creating dashboard links in Slack notifications
- JIRA ticket links

---

### RCA_API_KEY
**Purpose:** API key for authenticating webhook requests (future use)

**Required:** No (but recommended)

**Default:** `balaji-rca-secret-2025`

**Example:**
```bash
RCA_API_KEY=your-secure-random-api-key-change-this-in-production
```

**Security Note:** Change this in production to a strong random value:
```bash
# Generate secure key
openssl rand -hex 32
```

---

## AI Provider Configuration

### AI_PROVIDER
**Purpose:** Select which AI provider to use for RCA generation

**Required:** Yes

**Default:** `gemini`

**Options:**
- `gemini` - Use Google Gemini only
- `ollama` - Use local Ollama only
- `auto` - Try Ollama first, fallback to Gemini, then static fallback

**Example:**
```bash
# Use Google Gemini (recommended for production)
AI_PROVIDER=gemini

# Use local Ollama (for air-gapped environments)
AI_PROVIDER=ollama

# Auto fallback (try local first, then cloud)
AI_PROVIDER=auto
```

---

### Google Gemini Configuration

#### GEMINI_API_KEY
**Purpose:** Google Gemini API key for AI-powered RCA generation

**Required:** Yes (if AI_PROVIDER=gemini or auto)

**Default:** None

**How to obtain:**
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

**Example:**
```bash
GEMINI_API_KEY=AIzaSyD_your_actual_api_key_here
```

**Cost:** ~$0.10 per 1 million characters (as of Dec 2025)

**Rate Limits:**
- Free tier: 15 requests per minute
- Paid tier: 360 requests per minute

---

#### MODEL_ID
**Purpose:** Specific Gemini model to use

**Required:** No

**Default:** `models/gemini-2.5-flash`

**Options:**
```bash
# Fast, cost-effective (recommended)
MODEL_ID=models/gemini-2.5-flash

# More capable, slower, more expensive
MODEL_ID=models/gemini-1.5-pro

# Experimental models
MODEL_ID=models/gemini-2.0-flash-exp
```

**Model Comparison:**

| Model | Speed | Cost | Accuracy | Use Case |
|-------|-------|------|----------|----------|
| gemini-2.5-flash | Fast | Low | High | Production RCA |
| gemini-1.5-pro | Slower | Higher | Very High | Complex analysis |
| gemini-2.0-flash-exp | Very Fast | Low | Good | Experimental |

---

### Ollama Configuration (Local AI)

#### OLLAMA_HOST
**Purpose:** URL of local Ollama server

**Required:** Yes (if AI_PROVIDER=ollama)

**Default:** `http://localhost:11434`

**Example:**
```bash
# Local Ollama instance
OLLAMA_HOST=http://localhost:11434

# Remote Ollama server
OLLAMA_HOST=http://ollama-server.internal:11434
```

**Setup Ollama:**
```bash
# Install Ollama (macOS/Linux)
curl https://ollama.ai/install.sh | sh

# Pull DeepSeek-R1 model (recommended)
ollama pull deepseek-r1:latest

# Or pull smaller model
ollama pull llama2:7b
```

---

#### OLLAMA_MODEL
**Purpose:** Ollama model to use for RCA

**Required:** No

**Default:** `deepseek-r1:latest`

**Options:**
```bash
# DeepSeek R1 (best for reasoning)
OLLAMA_MODEL=deepseek-r1:latest

# Llama 2 (smaller, faster)
OLLAMA_MODEL=llama2:7b

# Mixtral (good balance)
OLLAMA_MODEL=mixtral:8x7b
```

---

## Database Configuration

### DB_TYPE
**Purpose:** Database backend to use

**Required:** Yes

**Default:** `sqlite`

**Options:**
- `sqlite` - SQLite file-based database (development)
- `azuresql` - Azure SQL Server (production)

**Example:**
```bash
# Development
DB_TYPE=sqlite

# Production
DB_TYPE=azuresql
```

---

### SQLite Configuration

#### DB_PATH
**Purpose:** Path to SQLite database file

**Required:** No

**Default:** `data/tickets.db`

**Example:**
```bash
# Default location
DB_PATH=data/tickets.db

# Custom location
DB_PATH=/var/lib/aiops-rca/tickets.db
```

**Notes:**
- Directory must exist and be writable
- Automatically created on first run
- Not recommended for production (use Azure SQL)

---

### Azure SQL Configuration

#### AZURE_SQL_SERVER
**Purpose:** Azure SQL Server hostname

**Required:** Yes (if DB_TYPE=azuresql)

**Format:** `your-server.database.windows.net`

**Example:**
```bash
AZURE_SQL_SERVER=aiops-sql-server.database.windows.net
```

---

#### AZURE_SQL_DATABASE
**Purpose:** Azure SQL database name

**Required:** Yes (if DB_TYPE=azuresql)

**Example:**
```bash
AZURE_SQL_DATABASE=aiops_rca_db
```

---

#### AZURE_SQL_USERNAME
**Purpose:** SQL Server admin username

**Required:** Yes (if DB_TYPE=azuresql)

**Example:**
```bash
AZURE_SQL_USERNAME=sqladmin
```

---

#### AZURE_SQL_PASSWORD
**Purpose:** SQL Server admin password

**Required:** Yes (if DB_TYPE=azuresql)

**Example:**
```bash
AZURE_SQL_PASSWORD='YourSecurePassword123!'
```

**Security Notes:**
- Use strong password (12+ characters, mixed case, numbers, symbols)
- Store in Azure Key Vault for production
- Never commit to git

---

## JIRA Configuration

### ITSM_TOOL
**Purpose:** ITSM tool to use for ticket creation

**Required:** Yes

**Default:** `none`

**Options:**
- `jira` - JIRA Cloud
- `none` - Disable ITSM integration

**Example:**
```bash
ITSM_TOOL=jira
```

---

### JIRA_DOMAIN
**Purpose:** JIRA Cloud instance URL

**Required:** Yes (if ITSM_TOOL=jira)

**Format:** `https://your-company.atlassian.net` (NO trailing slash)

**Example:**
```bash
JIRA_DOMAIN=https://sigmoidanalytics.atlassian.net
```

**Common Mistakes:**
```bash
# ❌ Wrong - has trailing slash
JIRA_DOMAIN=https://your-company.atlassian.net/

# ❌ Wrong - missing https
JIRA_DOMAIN=your-company.atlassian.net

# ✅ Correct
JIRA_DOMAIN=https://your-company.atlassian.net
```

---

### JIRA_USER_EMAIL
**Purpose:** Email of JIRA user for API authentication

**Required:** Yes (if ITSM_TOOL=jira)

**Example:**
```bash
JIRA_USER_EMAIL=aiops-bot@company.com
```

**Recommendation:** Use dedicated service account email

---

### JIRA_API_TOKEN
**Purpose:** JIRA API token for authentication

**Required:** Yes (if ITSM_TOOL=jira)

**How to obtain:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it "AIOps RCA System"
4. Copy the token

**Example:**
```bash
JIRA_API_TOKEN=ATATT3xFfGF0_your_actual_token_here
```

**Security:** Store in Azure Key Vault for production

---

### JIRA_PROJECT_KEY
**Purpose:** JIRA project key where tickets will be created

**Required:** Yes (if ITSM_TOOL=jira)

**Format:** Uppercase letters (2-10 characters)

**Example:**
```bash
JIRA_PROJECT_KEY=APAIOPS
```

**How to find:**
- In JIRA, go to project settings
- Look for "Key" field (e.g., APAIOPS, DATA, INFRA)

---

### JIRA_WEBHOOK_SECRET
**Purpose:** Secret for validating JIRA webhook requests

**Required:** Recommended

**Example:**
```bash
JIRA_WEBHOOK_SECRET=your-webhook-secret-random-string
```

**Generate secure secret:**
```bash
openssl rand -base64 32
```

---

## Slack Configuration

### SLACK_BOT_TOKEN
**Purpose:** Slack Bot OAuth token for sending notifications

**Required:** Yes (for Slack notifications)

**Format:** Starts with `xoxb-`

**How to obtain:**
1. Go to https://api.slack.com/apps
2. Create new app → "From scratch"
3. Name: "AIOps RCA Bot"
4. Go to "OAuth & Permissions"
5. Add Bot Token Scopes:
   - `chat:write`
   - `chat:write.public`
   - `channels:read`
6. Install to workspace
7. Copy "Bot User OAuth Token"

**Example:**
```bash
SLACK_BOT_TOKEN=xoxb-YOUR-BOT-TOKEN-HERE
```

---

### SLACK_ALERT_CHANNEL
**Purpose:** Default Slack channel for failure alerts

**Required:** Yes (for Slack notifications)

**Format:** Channel name (without #) or Channel ID

**Examples:**
```bash
# By channel name
SLACK_ALERT_CHANNEL=aiops-rca-alerts

# By channel ID (more reliable)
SLACK_ALERT_CHANNEL=C01234567AB
```

**How to get Channel ID:**
1. In Slack, right-click channel
2. Click "View channel details"
3. Scroll down, click "Copy" next to Channel ID

---

## Azure Services Configuration

### Azure Blob Storage

#### AZURE_BLOB_ENABLED
**Purpose:** Enable/disable Azure Blob Storage for audit logs

**Required:** No

**Default:** `false`

**Options:** `true`, `false`, `1`, `0`, `yes`, `no`

**Example:**
```bash
# Enable Blob Storage
AZURE_BLOB_ENABLED=true

# Disable Blob Storage
AZURE_BLOB_ENABLED=false
```

---

#### AZURE_STORAGE_CONN
**Purpose:** Azure Storage connection string

**Required:** Yes (if AZURE_BLOB_ENABLED=true)

**How to obtain:**
```bash
az storage account show-connection-string \
  --name your-storage-account \
  --resource-group your-rg
```

**Example:**
```bash
AZURE_STORAGE_CONN="DefaultEndpointsProtocol=https;AccountName=sttechdemorcadev;AccountKey=abc123...;EndpointSuffix=core.windows.net"
```

---

#### AZURE_BLOB_CONTAINER_NAME
**Purpose:** Blob container name for storing logs

**Required:** No

**Default:** `audit-logs`

**Example:**
```bash
AZURE_BLOB_CONTAINER_NAME=audit-logs
```

---

### Azure Data Factory Monitoring (Optional)

#### AZURE_SUBSCRIPTION_ID
**Purpose:** Azure subscription ID

**Required:** No (only for ADF API monitoring)

**How to obtain:**
```bash
az account show --query id -o tsv
```

**Example:**
```bash
AZURE_SUBSCRIPTION_ID=12345678-1234-1234-1234-123456789012
```

---

#### AZURE_RESOURCE_GROUP
**Purpose:** Resource group containing ADF

**Required:** No

**Example:**
```bash
AZURE_RESOURCE_GROUP=rg_techdemo_2025_Q4
```

---

#### AZURE_DATA_FACTORY_NAME
**Purpose:** ADF factory name

**Required:** No

**Example:**
```bash
AZURE_DATA_FACTORY_NAME=adf-techdemo-prod
```

---

#### AZURE_TENANT_ID
**Purpose:** Azure AD tenant ID for authentication

**Required:** No

**How to obtain:**
```bash
az account show --query tenantId -o tsv
```

**Example:**
```bash
AZURE_TENANT_ID=12345678-1234-1234-1234-123456789012
```

---

#### AZURE_CLIENT_ID
**Purpose:** Service principal application ID

**Required:** No

**How to obtain:**
```bash
# From service principal creation output
az ad sp create-for-rbac --name "aiops-rca-sp" --role Contributor
```

**Example:**
```bash
AZURE_CLIENT_ID=87654321-4321-4321-4321-210987654321
```

---

#### AZURE_CLIENT_SECRET
**Purpose:** Service principal password

**Required:** No

**Example:**
```bash
AZURE_CLIENT_SECRET=your-client-secret-here
```

---

## Databricks Configuration

### DATABRICKS_WORKSPACE_URL
**Purpose:** Databricks workspace URL

**Required:** Yes (for Databricks monitoring)

**Format:** `https://adb-XXXX.azuredatabricks.net`

**Example:**
```bash
DATABRICKS_WORKSPACE_URL=https://adb-1234567890123456.12.azuredatabricks.net
```

---

### DATABRICKS_TOKEN
**Purpose:** Databricks personal access token (PAT)

**Required:** Yes (for Databricks monitoring)

**Format:** Starts with `dapi`

**How to obtain:**
1. In Databricks workspace
2. User Settings → Developer → Access Tokens
3. Generate New Token
4. Lifetime: 365 days (or as per policy)
5. Copy token

**Example:**
```bash
DATABRICKS_TOKEN=dapi-YOUR-DATABRICKS-TOKEN-HERE
```

**Security:** Store in Azure Key Vault for production

---

## Auto-Remediation Configuration

### AUTO_REMEDIATION_ENABLED
**Purpose:** Enable/disable automatic remediation of failures

**Required:** No

**Default:** `false`

**Options:** `true`, `false`

**Example:**
```bash
# Enable auto-remediation
AUTO_REMEDIATION_ENABLED=true

# Disable auto-remediation
AUTO_REMEDIATION_ENABLED=false
```

**Warning:** Only enable after thorough testing. Auto-remediation can retry pipelines/jobs automatically.

---

### Logic Apps Playbook URLs

These are Azure Logic Apps HTTP trigger URLs for auto-remediation actions.

#### PLAYBOOK_RETRY_PIPELINE
**Purpose:** Logic App to retry ADF pipeline

**Required:** No (if AUTO_REMEDIATION_ENABLED=true)

**Example:**
```bash
PLAYBOOK_RETRY_PIPELINE=https://prod-12.eastus.logic.azure.com/workflows/abc123.../triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=xyz789...
```

---

#### PLAYBOOK_RETRY_JOB
**Purpose:** Logic App to retry Databricks job

**Required:** No

**Example:**
```bash
PLAYBOOK_RETRY_JOB=https://prod-13.eastus.logic.azure.com/workflows/def456.../triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=abc123...
```

---

#### PLAYBOOK_RESTART_CLUSTER
**Purpose:** Logic App to restart Databricks cluster

**Required:** No

**Example:**
```bash
PLAYBOOK_RESTART_CLUSTER=https://prod-14.eastus.logic.azure.com/workflows/ghi789.../triggers/manual/paths/invoke?...
```

---

#### PLAYBOOK_RERUN_UPSTREAM
**Purpose:** Logic App to check/rerun upstream dependencies

**Required:** No

**Example:**
```bash
PLAYBOOK_RERUN_UPSTREAM=https://prod-15.eastus.logic.azure.com/workflows/jkl012.../triggers/manual/paths/invoke?...
```

---

#### PLAYBOOK_RETRY_AIRFLOW_TASK
**Purpose:** Logic App to retry Airflow task

**Required:** No

**Example:**
```bash
PLAYBOOK_RETRY_AIRFLOW_TASK=https://prod-16.eastus.logic.azure.com/workflows/mno345.../triggers/manual/paths/invoke?...
```

---

## Authentication & Security

### JWT_SECRET_KEY
**Purpose:** Secret key for JWT token encryption

**Required:** Yes

**Default:** `your-secret-key-change-in-production-please-use-a-long-random-string`

**Generate secure key:**
```bash
openssl rand -hex 32
```

**Example:**
```bash
JWT_SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

**Security:**
- Use different keys for dev/staging/prod
- Never commit to git
- Store in Azure Key Vault
- Rotate regularly (every 90 days)

---

### JWT_EXPIRATION_HOURS
**Purpose:** JWT token expiration time in hours

**Required:** No

**Default:** `24`

**Example:**
```bash
# 24 hours (default)
JWT_EXPIRATION_HOURS=24

# 8 hours (more secure)
JWT_EXPIRATION_HOURS=8

# 7 days (less secure, for development)
JWT_EXPIRATION_HOURS=168
```

---

## Advanced Configuration

### Configuration Validation

Check if configuration is correct:

```bash
# Start application and check logs
uvicorn main:app --host 0.0.0.0 --port 8000

# Look for these startup messages:
# ✓ "Connected to Azure SQL" or "Using SQLite"
# ✓ "Azure Blob Storage enabled" (if configured)
# ✓ "JIRA integration enabled" (if configured)
```

### Test API Config Endpoint

```bash
curl http://localhost:8000/api/config
```

**Response:**
```json
{
  "ai_provider": "gemini",
  "db_type": "sqlite",
  "itsm_tool": "jira",
  "azure_blob_enabled": true,
  "auto_remediation_enabled": false,
  "slack_enabled": true,
  "databricks_enabled": true
}
```

---

## Environment-Specific Configurations

### Development (.env.dev)

```bash
# Minimal config for local development
PUBLIC_BASE_URL=http://localhost:8000
AI_PROVIDER=gemini
GEMINI_API_KEY=your-dev-key
DB_TYPE=sqlite
DB_PATH=data/tickets_dev.db
ITSM_TOOL=none
AZURE_BLOB_ENABLED=false
AUTO_REMEDIATION_ENABLED=false
JWT_SECRET_KEY=dev-secret-key-not-for-production
```

### Staging (.env.staging)

```bash
# Staging with cloud services but test data
PUBLIC_BASE_URL=https://aiops-rca-staging.company.com
AI_PROVIDER=gemini
GEMINI_API_KEY=your-staging-key
DB_TYPE=azuresql
AZURE_SQL_SERVER=aiops-sql-staging.database.windows.net
AZURE_SQL_DATABASE=aiops_rca_staging
ITSM_TOOL=jira
JIRA_DOMAIN=https://your-company-test.atlassian.net
AZURE_BLOB_ENABLED=true
AUTO_REMEDIATION_ENABLED=true
JWT_SECRET_KEY=staging-secret-key
```

### Production (.env.prod)

```bash
# Full production config with all services
PUBLIC_BASE_URL=https://aiops-rca.company.com
AI_PROVIDER=gemini
GEMINI_API_KEY=your-production-key
DB_TYPE=azuresql
AZURE_SQL_SERVER=aiops-sql-prod.database.windows.net
AZURE_SQL_DATABASE=aiops_rca_production
ITSM_TOOL=jira
JIRA_DOMAIN=https://your-company.atlassian.net
AZURE_BLOB_ENABLED=true
AUTO_REMEDIATION_ENABLED=true
JWT_SECRET_KEY=production-secret-key-from-key-vault
```

---

## Configuration Best Practices

1. **Never commit .env files to git**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo ".env.*" >> .gitignore
   ```

2. **Use Azure Key Vault for secrets**
   ```python
   # In production, load secrets from Key Vault
   from azure.identity import DefaultAzureCredential
   from azure.keyvault.secrets import SecretClient

   credential = DefaultAzureCredential()
   client = SecretClient(vault_url="https://your-kv.vault.azure.net/", credential=credential)

   JIRA_API_TOKEN = client.get_secret("jira-api-token").value
   ```

3. **Validate configuration on startup**
   - Application logs missing required variables
   - Fails fast if critical config missing

4. **Use environment-specific configs**
   - .env.dev, .env.staging, .env.prod
   - Never mix environments

5. **Document custom variables**
   - If adding new env vars, update this guide

---

**Next:** [05_API_REFERENCE.md](05_API_REFERENCE.md) - Complete API Documentation
