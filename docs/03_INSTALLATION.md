# Installation Guide

This guide provides step-by-step instructions for installing and setting up the AIOps RCA Assistant locally and in production environments.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Azure Services Configuration](#azure-services-configuration)
6. [Initial Testing](#initial-testing)
7. [Common Installation Issues](#common-installation-issues)

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Ubuntu 20.04+, macOS 11+, Windows 10+ | Ubuntu 22.04, macOS 13+ |
| **Python** | 3.12+ | 3.12+ |
| **RAM** | 4 GB | 8 GB+ |
| **Disk Space** | 2 GB | 5 GB+ |
| **Network** | Internet access | Stable broadband |

### Required Accounts & Access

1. **Azure Subscription**
   - Active Azure subscription
   - Contributor access or higher
   - Ability to create resources (Monitor, Blob Storage, Logic Apps)

2. **JIRA Cloud Account**
   - JIRA Cloud workspace
   - API token generation access
   - Permission to create tickets in target project

3. **Slack Workspace**
   - Slack workspace admin or bot creation permission
   - Ability to create and install apps

4. **Google Gemini API** (or Ollama for local AI)
   - Google Cloud account
   - Gemini API key
   - Alternatively: Local Ollama installation

---

## Local Development Setup

### Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/Balaji2106/LATEST-DEC9.git
cd LATEST-DEC9

# Navigate to application directory
cd genai_rca_assistant
```

### Step 2: Create Virtual Environment

#### Linux/macOS
```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.12.x
```

#### Windows
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.12.x
```

### Step 3: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
```

**Expected Output:**
```
fastapi==0.104.1
```

### Step 4: Install System Dependencies (Linux)

For Azure SQL Server support (optional):

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y unixodbc unixodbc-dev

# Install Microsoft ODBC Driver 18
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

### Step 5: Create Required Directories

```bash
# Create data directory for SQLite database
mkdir -p data

# Create logs directory (optional)
mkdir -p logs

# Verify directory structure
ls -la
```

Expected structure:
```
genai_rca_assistant/
├── data/               # SQLite database storage
├── logs/               # Application logs (optional)
├── dashboard.html      # Dashboard UI
├── login.html          # Login page
├── main.py             # Main application
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (create this)
└── ...
```

---

## Environment Configuration

### Step 1: Create .env File

```bash
# Create .env file from template
touch .env
```

### Step 2: Configure Environment Variables

Edit `.env` file with your editor:

```bash
nano .env  # or use vim, code, etc.
```

**Minimum Configuration for Local Development:**

```bash
# =============================================================================
# CORE SETTINGS
# =============================================================================
PUBLIC_BASE_URL=http://localhost:8000
RCA_API_KEY=your-secure-api-key-here-change-this

# =============================================================================
# AI CONFIGURATION
# =============================================================================
# AI Provider: gemini | ollama | auto
AI_PROVIDER=gemini

# Google Gemini Configuration
GEMINI_API_KEY=your-gemini-api-key-here
MODEL_ID=models/gemini-2.5-flash

# Ollama Configuration (Optional - for local AI)
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=deepseek-r1:latest

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# Database Type: sqlite | azuresql
DB_TYPE=sqlite
DB_PATH=data/tickets.db

# Azure SQL Configuration (Optional)
# AZURE_SQL_SERVER=your-server.database.windows.net
# AZURE_SQL_DATABASE=aiops_rca
# AZURE_SQL_USERNAME=your-username
# AZURE_SQL_PASSWORD=your-password

# =============================================================================
# JIRA CONFIGURATION
# =============================================================================
ITSM_TOOL=jira
JIRA_DOMAIN=https://your-company.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=APAIOPS
JIRA_WEBHOOK_SECRET=your-webhook-secret

# =============================================================================
# SLACK CONFIGURATION
# =============================================================================
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_ALERT_CHANNEL=aiops-rca-alerts

# =============================================================================
# AZURE SERVICES (Optional - for production)
# =============================================================================
# Azure Blob Storage
AZURE_BLOB_ENABLED=false
AZURE_STORAGE_CONN=DefaultEndpointsProtocol=https;AccountName=...

# Azure Data Factory Monitoring
# AZURE_SUBSCRIPTION_ID=your-subscription-id
# AZURE_RESOURCE_GROUP=your-resource-group
# AZURE_DATA_FACTORY_NAME=your-adf-name
# AZURE_TENANT_ID=your-tenant-id
# AZURE_CLIENT_ID=your-client-id
# AZURE_CLIENT_SECRET=your-client-secret

# =============================================================================
# DATABRICKS CONFIGURATION
# =============================================================================
# DATABRICKS_WORKSPACE_URL=https://adb-XXXX.azuredatabricks.net
# DATABRICKS_TOKEN=dapi...

# =============================================================================
# AUTO-REMEDIATION (Optional)
# =============================================================================
AUTO_REMEDIATION_ENABLED=false

# Logic Apps Endpoints (only needed if auto-remediation enabled)
# PLAYBOOK_RETRY_PIPELINE=https://prod-XX.eastus.logic.azure.com/...
# PLAYBOOK_RETRY_JOB=https://prod-XX.eastus.logic.azure.com/...
# PLAYBOOK_RESTART_CLUSTER=https://prod-XX.eastus.logic.azure.com/...

# =============================================================================
# AUTHENTICATION
# =============================================================================
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_EXPIRATION_HOURS=24
```

### Step 3: Obtain Required API Keys

#### Google Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key and set it in `.env` as `GEMINI_API_KEY`

#### JIRA API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it "AIOps RCA System"
4. Copy the token and set it in `.env` as `JIRA_API_TOKEN`

#### Slack Bot Token

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "AIOps RCA Bot", select your workspace
4. Go to "OAuth & Permissions"
5. Add Bot Token Scopes:
   - `chat:write`
   - `chat:write.public`
   - `channels:read`
6. Install app to workspace
7. Copy "Bot User OAuth Token" (starts with `xoxb-`)
8. Set it in `.env` as `SLACK_BOT_TOKEN`
9. Get channel ID:
   ```bash
   # In Slack, right-click channel → View channel details → Copy Channel ID
   ```

---

## Database Setup

### SQLite (Default for Development)

SQLite database is created automatically on first run. No additional setup needed.

```bash
# Verify database creation
ls -la data/
# You should see tickets.db after first run
```

### Azure SQL (Production)

If using Azure SQL Server:

1. **Create Azure SQL Database**
   ```bash
   # Create SQL Server
   az sql server create \
     --name your-sql-server \
     --resource-group your-rg \
     --location eastus \
     --admin-user sqladmin \
     --admin-password 'YourPassword123!'

   # Create database
   az sql db create \
     --name aiops_rca \
     --server your-sql-server \
     --resource-group your-rg \
     --service-objective S0
   ```

2. **Configure Firewall**
   ```bash
   # Allow Azure services
   az sql server firewall-rule create \
     --name AllowAzureServices \
     --server your-sql-server \
     --resource-group your-rg \
     --start-ip-address 0.0.0.0 \
     --end-ip-address 0.0.0.0

   # Allow your IP
   az sql server firewall-rule create \
     --name AllowMyIP \
     --server your-sql-server \
     --resource-group your-rg \
     --start-ip-address YOUR_PUBLIC_IP \
     --end-ip-address YOUR_PUBLIC_IP
   ```

3. **Update .env**
   ```bash
   DB_TYPE=azuresql
   AZURE_SQL_SERVER=your-sql-server.database.windows.net
   AZURE_SQL_DATABASE=aiops_rca
   AZURE_SQL_USERNAME=sqladmin
   AZURE_SQL_PASSWORD=YourPassword123!
   ```

---

## Azure Services Configuration

### Azure Blob Storage (Optional)

For storing audit logs and failure payloads:

```bash
# Create storage account
az storage account create \
  --name sttechdemorcadev \
  --resource-group your-rg \
  --location eastus \
  --sku Standard_LRS

# Create container
az storage container create \
  --name audit-logs \
  --account-name sttechdemorcadev

# Get connection string
az storage account show-connection-string \
  --name sttechdemorcadev \
  --resource-group your-rg
```

Update `.env`:
```bash
AZURE_BLOB_ENABLED=true
AZURE_STORAGE_CONN="DefaultEndpointsProtocol=https;AccountName=sttechdemorcadev;AccountKey=...;EndpointSuffix=core.windows.net"
```

---

## Initial Testing

### Step 1: Run Application

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Start the application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 2: Access Dashboard

1. **Open browser**: http://localhost:8000/dashboard
2. **Create first user**:
   - If redirected to login, click "Register"
   - Email: `yourname@sigmoidanalytics.com` (must be @sigmoidanalytics.com)
   - Password: At least 8 characters
   - Full Name: Your name
3. **Login** with created credentials

### Step 3: Test API Health

```bash
# Test root endpoint
curl http://localhost:8000/

# Test summary endpoint
curl http://localhost:8000/api/summary

# Expected response:
{
  "open": 0,
  "in_progress": 0,
  "closed": 0,
  "total": 0
}
```

### Step 4: Test Webhook Endpoint

```bash
# Test Azure Monitor webhook with sample payload
curl -X POST http://localhost:8000/azure-monitor \
  -H "Content-Type: application/json" \
  -d '{
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
      "essentials": {
        "alertRule": "test-pipeline-alert",
        "severity": "Sev3",
        "signalType": "Log"
      },
      "alertContext": {
        "SearchQuery": "ADFPipelineRun | where Status == \"Failed\"",
        "SearchResults": {
          "tables": [{
            "rows": [[
              "2025-12-12T10:00:00Z",
              "test-pipeline",
              "test-run-123",
              "Copy Activity",
              "2200",
              "Test failure for installation verification"
            ]]
          }]
        }
      }
    }
  }'
```

**Expected Response:**
```json
{
  "ticket_id": "ADF-20251212T100000-abc123",
  "status": "created",
  "message": "Ticket created successfully"
}
```

### Step 5: Verify Database

```bash
# Check if database was created
ls -la data/tickets.db

# Query database (requires sqlite3)
sqlite3 data/tickets.db "SELECT COUNT(*) FROM tickets;"
# Should show: 1 (from test webhook)
```

### Step 6: Check Logs

```bash
# View application logs in terminal
# Look for these key messages:
# ✓ "Connected to Azure SQL" or "Using SQLite"
# ✓ "Application startup complete"
# ✓ "Ticket created: ADF-..."
# ✓ "JIRA ticket created: ..." (if JIRA configured)
# ✓ "Slack notification sent" (if Slack configured)
```

---

## Common Installation Issues

### Issue 1: Python Version Mismatch

**Error:**
```
python3.12: command not found
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.12 python3.12-venv

# macOS (using Homebrew)
brew install python@3.12

# Verify installation
python3.12 --version
```

### Issue 2: pip Install Failures

**Error:**
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**Solution (Windows):**
1. Install Microsoft C++ Build Tools
2. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
3. Install "Desktop development with C++"
4. Retry: `pip install -r requirements.txt`

**Solution (Linux):**
```bash
sudo apt-get install python3-dev build-essential
pip install -r requirements.txt
```

### Issue 3: ODBC Driver Not Found (Azure SQL)

**Error:**
```
Can't open lib 'ODBC Driver 18 for SQL Server'
```

**Solution:**
```bash
# Install ODBC Driver 18
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

### Issue 4: Port Already in Use

**Error:**
```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Issue 5: Gemini API Key Invalid

**Error:**
```
WARNING: Gemini not initialized: 401 Client Error: Unauthorized
```

**Solution:**
1. Verify API key is correct in `.env`
2. Check key is active at https://aistudio.google.com/app/apikey
3. Ensure no extra spaces or quotes in `.env`
4. Try regenerating key if needed

### Issue 6: JIRA Authentication Failed

**Error:**
```
Failed to create Jira ticket: 401 Unauthorized
```

**Solution:**
1. Verify JIRA domain URL (should not have trailing slash)
2. Check email is correct (JIRA account email)
3. Regenerate API token at https://id.atlassian.com/manage-profile/security/api-tokens
4. Test credentials:
   ```bash
   curl -u "your-email@company.com:your-api-token" \
     https://your-company.atlassian.net/rest/api/3/myself
   ```

### Issue 7: Slack Bot Token Invalid

**Error:**
```
Slack notification failed: invalid_auth
```

**Solution:**
1. Verify token starts with `xoxb-`
2. Check bot is installed in workspace
3. Verify bot has required scopes: `chat:write`, `chat:write.public`
4. Reinstall app if needed

### Issue 8: Database Permission Denied

**Error:**
```
OperationalError: unable to open database file
```

**Solution:**
```bash
# Create data directory with proper permissions
mkdir -p data
chmod 755 data

# Ensure user has write access
touch data/tickets.db
```

---

## Next Steps

After successful installation:

1. **Configure Azure Monitor** → See [02_AZURE_SETUP.md](02_AZURE_SETUP.md)
2. **Set up Databricks monitoring** → See [06_INTEGRATIONS.md](06_INTEGRATIONS.md)
3. **Configure Airflow callbacks** → See [06_INTEGRATIONS.md](06_INTEGRATIONS.md)
4. **Deploy to production** → See [08_DEPLOYMENT.md](08_DEPLOYMENT.md)

---

## Verification Checklist

- [ ] Python 3.12+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip list` shows fastapi, uvicorn, etc.)
- [ ] `.env` file created with all required variables
- [ ] Gemini API key obtained and configured
- [ ] JIRA API token obtained and configured
- [ ] Slack bot token obtained and configured
- [ ] Application starts without errors
- [ ] Dashboard accessible at http://localhost:8000/dashboard
- [ ] User registration works
- [ ] Test webhook creates ticket successfully
- [ ] Database file created in `data/tickets.db`

---

**Next:** [04_CONFIGURATION.md](04_CONFIGURATION.md) - Detailed Configuration Guide
