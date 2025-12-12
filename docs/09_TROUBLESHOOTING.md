# Troubleshooting Guide

Common issues and solutions for the AIOps RCA Assistant.

---

## 📋 Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Issues](#configuration-issues)
3. [Database Issues](#database-issues)
4. [Integration Issues](#integration-issues)
5. [Runtime Errors](#runtime-errors)
6. [Performance Issues](#performance-issues)
7. [Debugging Tips](#debugging-tips)

---

## Installation Issues

### Issue: Python Version Not Found

**Error:**
```
python3.12: command not found
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev

# macOS
brew install python@3.12

# Verify
python3.12 --version
```

---

### Issue: pip Install Fails with Compiler Errors

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
sudo apt-get install python3-dev build-essential gcc g++
pip install -r requirements.txt
```

---

### Issue: ODBC Driver Not Found

**Error:**
```
Can't open lib 'ODBC Driver 18 for SQL Server'
```

**Solution (Linux):**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

**Solution (macOS):**
```bash
brew tap microsoft/mssql-release
brew update
brew install msodbcsql18 mssql-tools18
```

---

## Configuration Issues

### Issue: Gemini API Key Invalid

**Error in logs:**
```
WARNING: Gemini not initialized: 401 Client Error: Unauthorized
```

**Solution:**
1. Verify API key is correct in `.env`
2. Check key is active at https://aistudio.google.com/app/apikey
3. Ensure no extra spaces or quotes:
   ```bash
   # ❌ Wrong
   GEMINI_API_KEY=" AIzaSyD... "
   GEMINI_API_KEY='AIzaSyD...'

   # ✅ Correct
   GEMINI_API_KEY=AIzaSyD...
   ```
4. Regenerate key if needed
5. Restart application

---

### Issue: Environment Variables Not Loaded

**Symptom:** Application uses default values instead of .env values

**Solution:**
```bash
# Verify .env file location
ls -la genai_rca_assistant/.env

# Check file is being read
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"

# Ensure .env is in the same directory as main.py
cd genai_rca_assistant
ls -la
# Should show both main.py and .env
```

---

## Database Issues

### Issue: Database Permission Denied (SQLite)

**Error:**
```
OperationalError: unable to open database file
```

**Solution:**
```bash
# Create data directory
mkdir -p data
chmod 755 data

# Ensure user has write access
touch data/tickets.db
ls -la data/

# Check disk space
df -h
```

---

### Issue: Azure SQL Connection Timeout

**Error:**
```
OperationalError: (08001) [Microsoft][ODBC Driver 18 for SQL Server]TCP Provider: Error code 0x2746
```

**Solution:**
1. **Check firewall rules:**
   ```bash
   # Allow your IP
   az sql server firewall-rule create \
     --resource-group your-rg \
     --server your-sql-server \
     --name AllowMyIP \
     --start-ip-address YOUR_PUBLIC_IP \
     --end-ip-address YOUR_PUBLIC_IP
   ```

2. **Verify connection string:**
   ```bash
   # Test connection
   sqlcmd -S your-server.database.windows.net -U sqladmin -P 'password' -d aiops_rca -Q "SELECT 1"
   ```

3. **Check NSG rules** (if using private endpoint)

---

### Issue: UNIQUE Constraint Error

**Error:**
```
IntegrityError: UNIQUE constraint failed: tickets.run_id
```

**Cause:** Duplicate run_id detected (expected behavior for deduplication)

**Solution:**
This is normal - the system prevents duplicate tickets for the same run_id.

**If you need to test:**
```python
# Use different run_id for each test
payload["run_id"] = f"test-run-{uuid.uuid4()}"
```

---

## Integration Issues

### Issue: JIRA Authentication Failed

**Error:**
```
Failed to create Jira ticket: 401 Unauthorized
```

**Solution:**
1. **Verify credentials:**
   ```bash
   curl -u "your-email@company.com:your-api-token" \
     https://your-company.atlassian.net/rest/api/3/myself
   ```

2. **Check JIRA domain:**
   ```bash
   # ❌ Wrong (has trailing slash)
   JIRA_DOMAIN=https://your-company.atlassian.net/

   # ✅ Correct
   JIRA_DOMAIN=https://your-company.atlassian.net
   ```

3. **Regenerate API token:**
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Delete old token
   - Create new token
   - Update .env

---

### Issue: Slack Notification Failed

**Error:**
```
Slack notification failed: invalid_auth
```

**Solution:**
1. **Verify token format:**
   ```bash
   # Must start with xoxb-
   SLACK_BOT_TOKEN=xoxb-...
   ```

2. **Check bot scopes:**
   - Go to https://api.slack.com/apps
   - Select app → OAuth & Permissions
   - Verify scopes: `chat:write`, `chat:write.public`
   - Reinstall app if scopes changed

3. **Test token:**
   ```bash
   curl -X POST "https://slack.com/api/auth.test" \
     -H "Authorization: Bearer ${SLACK_BOT_TOKEN}"
   ```

---

### Issue: Slack Message Not Posted

**Error:** No error, but message doesn't appear

**Solution:**
1. **Verify channel ID:**
   ```bash
   # Get channel ID
   curl -X GET "https://slack.com/api/conversations.list" \
     -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" | jq '.channels[] | {name: .name, id: .id}'
   ```

2. **Check bot is in channel:**
   - In Slack, go to channel
   - Add bot: `/invite @AIOps RCA Bot`

3. **Use channel ID instead of name:**
   ```bash
   # More reliable
   SLACK_ALERT_CHANNEL=C01234567AB
   ```

---

### Issue: Databricks API Error

**Error:**
```
Failed to fetch Databricks run details: 403 Forbidden
```

**Solution:**
1. **Verify token permissions:**
   ```bash
   # Test token
   curl -X GET "${DATABRICKS_WORKSPACE_URL}/api/2.0/clusters/list" \
     -H "Authorization: Bearer ${DATABRICKS_TOKEN}"
   ```

2. **Check token not expired:**
   - Databricks PATs expire
   - Generate new token
   - Update .env

3. **Verify workspace URL:**
   ```bash
   # Must include https://
   DATABRICKS_WORKSPACE_URL=https://adb-1234567890123456.12.azuredatabricks.net
   ```

---

### Issue: Azure Monitor Alerts Not Triggering

**Symptom:** Pipelines fail but no webhook received

**Solution:**
1. **Check alert rule is enabled:**
   ```bash
   az monitor scheduled-query show \
     --name "adf-pipeline-failure-alert" \
     --resource-group rg_techdemo_2025_Q4
   ```

2. **Verify action group:**
   ```bash
   az monitor action-group show \
     --name "rca-webhook-action-group" \
     --resource-group rg_techdemo_2025_Q4
   ```

3. **Test webhook manually:**
   ```bash
   curl -X POST http://localhost:8000/azure-monitor \
     -H "Content-Type: application/json" \
     -d @test-payload.json
   ```

4. **Check alert query timeframe:**
   ```kql
   # Query should look back 15m, not 48h
   | where TimeGenerated > ago(15m)  # ✅ Correct
   | where TimeGenerated > ago(48h)  # ❌ Wrong (too long)
   ```

---

## Runtime Errors

### Issue: Port Already in Use

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

---

### Issue: WebSocket Connection Failed

**Error in browser console:**
```
WebSocket connection to 'ws://localhost:8000/ws' failed
```

**Solution:**
1. **Check application is running:**
   ```bash
   curl http://localhost:8000/
   ```

2. **Use correct protocol:**
   ```javascript
   // HTTP → ws://
   const ws = new WebSocket('ws://localhost:8000/ws');

   // HTTPS → wss://
   const ws = new WebSocket('wss://your-domain.com/ws');
   ```

3. **Check firewall/proxy:**
   - Ensure WebSocket traffic not blocked
   - Some corporate proxies block WebSockets

---

### Issue: AI RCA Generation Timeout

**Error:**
```
WARNING: Gemini RCA failed: Timeout
```

**Solution:**
1. **Check Gemini API status:**
   - Visit https://status.cloud.google.com/
   - Check for Gemini API outages

2. **Increase timeout:**
   ```python
   # In main.py, update timeout
   resp = model.generate_content(prompt, request_options={"timeout": 60})
   ```

3. **Switch to Ollama (offline):**
   ```bash
   AI_PROVIDER=ollama
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=deepseek-r1:latest
   ```

---

## Performance Issues

### Issue: Slow Dashboard Loading

**Symptom:** Dashboard takes >5 seconds to load

**Solution:**
1. **Check database query performance:**
   ```bash
   # Enable query logging
   echo "Ticket count: $(sqlite3 data/tickets.db 'SELECT COUNT(*) FROM tickets')"
   ```

2. **Add database indexes:**
   ```sql
   CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
   CREATE INDEX IF NOT EXISTS idx_tickets_timestamp ON tickets(timestamp);
   ```

3. **Limit API results:**
   ```python
   # In main.py, add LIMIT
   db_query("SELECT * FROM tickets WHERE status='open' ORDER BY timestamp DESC LIMIT 100")
   ```

---

### Issue: High Memory Usage

**Symptom:** Application uses >4GB RAM

**Solution:**
1. **Check for memory leaks:**
   ```bash
   # Monitor memory
   top -p $(pgrep -f "uvicorn main:app")
   ```

2. **Limit WebSocket connections:**
   ```python
   # In main.py, add connection limit
   if len(manager.active_connections) > 100:
       raise HTTPException(status_code=503, detail="Too many connections")
   ```

3. **Use connection pooling for database:**
   ```python
   # Already configured in main.py
   engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=10, max_overflow=20)
   ```

---

## Debugging Tips

### Enable Debug Logging

```python
# In main.py, change logging level
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
```

### View Real-Time Logs

```bash
# Local
tail -f logs/rca.log

# App Service
az webapp log tail --resource-group rg-aiops-rca-prod --name aiops-rca-prod

# AKS
kubectl logs -f deployment/aiops-rca
```

### Test Individual Components

```python
# Test Gemini
python3 -c "import google.generativeai as genai; genai.configure(api_key='your-key'); print(genai.list_models())"

# Test JIRA
curl -u "email:token" https://your-company.atlassian.net/rest/api/3/myself

# Test Slack
curl -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer xoxb-your-token" \
  -H "Content-Type: application/json" \
  -d '{"channel":"C01234567","text":"Test"}'
```

### Database Inspection

```bash
# SQLite
sqlite3 data/tickets.db

# Show tables
.tables

# Show schema
.schema tickets

# Query tickets
SELECT id, pipeline, status, timestamp FROM tickets ORDER BY timestamp DESC LIMIT 10;

# Count by status
SELECT status, COUNT(*) FROM tickets GROUP BY status;

# Exit
.quit
```

### API Testing with curl

```bash
# Test webhook endpoint
curl -X POST http://localhost:8000/azure-monitor \
  -H "Content-Type: application/json" \
  -d '{
    "schemaId": "azureMonitorCommonAlertSchema",
    "data": {
      "essentials": {"alertRule": "test", "severity": "Sev3"},
      "alertContext": {"SearchResults": {"tables": [{"rows": [["2025-12-12T10:00:00Z", "test-pipeline", "test-run-123", "Test Activity", "2200", "Test error"]]}]}}
    }
  }'

# Test API endpoints
curl -X GET http://localhost:8000/api/summary \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## Getting Help

### Check Logs First

```bash
# Application logs
tail -100 logs/rca.log

# System logs (if using systemd)
sudo journalctl -u aiops-rca -n 100
```

### Gather Diagnostic Information

```bash
# System info
uname -a
python --version
pip list | grep -E "fastapi|uvicorn|sqlalchemy"

# Configuration (sanitize secrets!)
cat .env | sed 's/\(.*KEY.*=\).*/\1***/'
cat .env | sed 's/\(.*TOKEN.*=\).*/\1***/'

# Database status
ls -lh data/tickets.db
sqlite3 data/tickets.db "SELECT COUNT(*) FROM tickets"
```

### Common Commands

```bash
# Restart application
sudo systemctl restart aiops-rca

# Check status
sudo systemctl status aiops-rca

# View recent logs
sudo journalctl -u aiops-rca --since "1 hour ago"

# Test endpoint
curl -I http://localhost:8000/
```

---

**Next:** [10_DEVELOPER_GUIDE.md](10_DEVELOPER_GUIDE.md) - Developer Guide
