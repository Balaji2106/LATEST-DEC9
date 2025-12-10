# Testing AI-Driven Auto-Remediation

This guide walks you through testing the complete AI-driven auto-remediation system for ADF and Databricks failures.

## 📋 Prerequisites

1. **Python 3.8+** installed
2. **AI Provider** configured (Gemini or Ollama)
3. **Database** (SQLite for testing)
4. **Logic Apps** (optional - can test without them)

---

## 🚀 Quick Start (Local Testing)

### Step 1: Configure Environment

```bash
cd /home/user/LATEST-DEC9/genai_rca_assistant

# Copy test environment file
cp .env.test .env

# Edit .env with your settings
nano .env
```

**Minimum configuration for testing:**
```bash
# AI Provider (choose one)
AI_PROVIDER=ollama                          # For local testing (recommended)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:latest

# OR use Gemini
# AI_PROVIDER=gemini
# GEMINI_API_KEY=your-actual-api-key-here

# Enable auto-remediation
AUTO_REMEDIATION_ENABLED=true

# Database
DB_TYPE=sqlite
DB_PATH=data/tickets.db

# Logic App URLs (use dummy URLs for now - they'll be logged but not called)
PLAYBOOK_RETRY_PIPELINE=https://test.logicapp.com/retry-pipeline
PLAYBOOK_RETRY_JOB=https://test.logicapp.com/retry-job
PLAYBOOK_RESTART_CLUSTER=https://test.logicapp.com/restart-cluster
PLAYBOOK_REINSTALL_LIBRARIES=https://test.logicapp.com/reinstall-libraries
```

### Step 2: Install Dependencies

```bash
cd genai_rca_assistant
pip install -r requirements.txt
```

### Step 3: Start Ollama (if using local AI)

```bash
# In a new terminal:
ollama serve

# Pull the model (first time only):
ollama pull deepseek-r1:latest
```

### Step 4: Start RCA Application

```bash
cd /home/user/LATEST-DEC9/genai_rca_assistant

# Start the application
python main.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Run Tests

In a **new terminal**:

```bash
cd /home/user/LATEST-DEC9

# Run the test suite
python test_auto_remediation.py
```

---

## 🧪 Test Scenarios

The test script simulates 6 different failure scenarios:

### 1. ✅ ADF Network Timeout (Auto-remediable)
- **Error**: SQL connection timeout
- **Expected AI Decision**:
  - `is_auto_remediable`: `true`
  - `remediation_action`: `retry_pipeline`
  - `remediation_risk`: `Low`
- **Expected Outcome**: AI recommends immediate retry

### 2. ✅ ADF Throttling Error (Auto-remediable)
- **Error**: Azure service throttling (429)
- **Expected AI Decision**:
  - `is_auto_remediable`: `true`
  - `remediation_action`: `retry_pipeline`
  - `remediation_risk`: `Low`
- **Expected Outcome**: AI recommends retry with backoff

### 3. ✅ Databricks Driver Unreachable (Auto-remediable)
- **Error**: Cannot reach Spark driver
- **Expected AI Decision**:
  - `is_auto_remediable`: `true`
  - `remediation_action`: `restart_cluster`
  - `remediation_risk`: `Medium`
- **Expected Outcome**: AI recommends cluster restart

### 4. ✅ Databricks Out of Memory (Auto-remediable)
- **Error**: Container OOM killed
- **Expected AI Decision**:
  - `is_auto_remediable`: `true`
  - `remediation_action`: `restart_cluster`
  - `remediation_risk`: `Medium`
- **Expected Outcome**: AI recommends cluster restart

### 5. ✅ Databricks Library Install Failed (Auto-remediable)
- **Error**: Library installation failure
- **Expected AI Decision**:
  - `is_auto_remediable`: `true`
  - `remediation_action`: `reinstall_libraries`
  - `remediation_risk`: `Medium`
- **Expected Outcome**: AI recommends library reinstall

### 6. ❌ ADF Schema Mismatch (Manual Intervention)
- **Error**: Data schema validation failure
- **Expected AI Decision**:
  - `is_auto_remediable`: `false`
  - `remediation_action`: `manual_intervention`
  - `remediation_risk`: `High`
- **Expected Outcome**: AI escalates to human

---

## 📊 Verifying Results

### Check Logs
```bash
cd /home/user/LATEST-DEC9/genai_rca_assistant

# Watch RCA application logs
tail -f rca_app.log

# Look for:
# [POLICY-ENGINE] AI determined eligible for auto-remediation
# [AUTO-REM] Triggering auto-remediation
```

### Check Dashboard
```bash
# Open in browser:
http://localhost:8000/dashboard

# Login with default credentials if prompted
```

### Check Database
```bash
cd /home/user/LATEST-DEC9/genai_rca_assistant

sqlite3 data/tickets.db

# Query tickets
SELECT id, pipeline, error_type, remediation_status FROM tickets ORDER BY timestamp DESC LIMIT 10;

# Query remediation attempts
SELECT ticket_id, remediation_action, status FROM remediation_attempts;

.quit
```

---

## 🔍 What to Look For

### ✅ Success Indicators:

1. **AI Analysis Completed**
   - Log: `[RCA] AI analysis completed for ticket`
   - Each ticket gets AI analysis with `is_auto_remediable` field

2. **Policy Engine Decision**
   - Log: `[POLICY-ENGINE] AI determined eligible for auto-remediation`
   - AI decision is respected (no hardcoded checks)

3. **Remediation Triggered**
   - Log: `[AUTO-REM] Triggering auto-remediation`
   - Action and risk level logged correctly

4. **Correct Action Mapping**
   - Network errors → `retry_pipeline`
   - Driver unreachable → `restart_cluster`
   - Library failures → `reinstall_libraries`

5. **Risk-Based Retry Strategy**
   - Low risk: 3 retries, backoff [30, 60, 120]s
   - Medium risk: 2 retries, backoff [60, 180, 300]s
   - High risk: 1 retry, backoff [180]s

### ❌ Failure Indicators:

1. **No AI Analysis**
   - Check GEMINI_API_KEY or OLLAMA_HOST configuration
   - Verify Ollama is running

2. **Remediation Not Triggered**
   - Check `AUTO_REMEDIATION_ENABLED=true`
   - Verify AI returns `is_auto_remediable: true`

3. **Wrong Action Selected**
   - AI might make different decisions (this is okay if reasoning is sound)
   - Check AI's root cause analysis

4. **Playbook URL Not Found**
   - Error: `No playbook URL configured for action`
   - Ensure REMEDIATION_ACTION_PLAYBOOKS has URLs

---

## 🧩 Testing with Real Logic Apps

Once you deploy Logic Apps to Azure:

1. **Update .env with real URLs:**
   ```bash
   PLAYBOOK_RETRY_PIPELINE=https://prod-12.eastus.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke
   PLAYBOOK_RETRY_JOB=https://prod-34.eastus.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke
   # ... etc
   ```

2. **Restart RCA application**
   ```bash
   # Stop with Ctrl+C
   # Start again
   python main.py
   ```

3. **Run tests again**
   ```bash
   python test_auto_remediation.py
   ```

4. **Verify Logic App execution**
   - Check Azure Portal → Logic Apps → Runs
   - Look for triggered runs with matching ticket_id

---

## 📈 Expected Test Results

### Test Output Example:
```
🧪 TEST SCENARIO: adf_network_timeout
================================================================================

📤 Sending webhook to: http://localhost:8000/adf-monitor
✅ Success!

🎫 Ticket Created: TIK-20251209-ABC123

🤖 AI DECISION:
   Auto-remediable: True
   Action: retry_pipeline
   Risk: Low
   Requires Approval: False
   Business Impact: Medium

✅ EXPECTED:
   Auto-remediable: True
   Action: retry_pipeline
   Risk: Low

✅ TEST PASSED: AI decision matches expectations

💡 Root Cause:
   Network timeout connecting to SQL database endpoint

📝 Recommendations:
   1. Retry pipeline execution immediately
   2. Check SQL server availability if retry fails
   3. Review network connectivity to database endpoint

🔄 Remediation Status: in_progress

================================================================================
```

---

## 🐛 Troubleshooting

### Issue: "CONNECTION ERROR: Could not connect to RCA system"
**Solution**: Start the RCA application first (`python main.py`)

### Issue: "AI analysis failed - no API key"
**Solution**:
- For Gemini: Set `GEMINI_API_KEY` in .env
- For Ollama: Start Ollama server (`ollama serve`)

### Issue: "No playbook URL configured for action"
**Solution**: Add placeholder URLs to .env:
```bash
PLAYBOOK_RETRY_PIPELINE=https://test.com/retry
PLAYBOOK_RETRY_JOB=https://test.com/retry-job
# etc.
```

### Issue: "Auto-remediation not triggered"
**Solution**:
1. Check `.env`: `AUTO_REMEDIATION_ENABLED=true`
2. Restart application
3. Verify AI returns `is_auto_remediable: true`

### Issue: "AI always says 'manual_intervention'"
**Solution**:
- Check AI provider is working
- Verify error messages are clear in test payloads
- AI might be conservative - check root cause analysis

---

## 📝 Manual Testing (Alternative)

If you want to test manually:

```bash
# Test ADF failure
curl -X POST http://localhost:8000/adf-monitor \
  -H "Content-Type: application/json" \
  -H "X-API-Key: balaji-rca-secret-2025" \
  -d '{
    "pipelineName": "test_pipeline",
    "runId": "test-123",
    "status": "Failed",
    "errorCode": "NetworkTimeout",
    "errorMessage": "Connection timeout to SQL server",
    "startTime": "2025-12-09T10:00:00Z",
    "endTime": "2025-12-09T10:05:00Z",
    "dataFactoryName": "test-adf"
  }'

# Check response for ticket_id
# Then query ticket details:
curl http://localhost:8000/api/tickets/TIK-... \
  -H "X-API-Key: balaji-rca-secret-2025"
```

---

## ✅ Success Criteria

Your AI-driven auto-remediation is working if:

1. ✅ AI analyzes every failure and returns structured JSON
2. ✅ AI correctly identifies auto-remediable vs manual errors
3. ✅ AI chooses appropriate remediation action (retry/restart/reinstall)
4. ✅ AI assesses risk level (Low/Medium/High)
5. ✅ Policy engine respects AI decisions (no hardcoded checks)
6. ✅ Remediation attempts are logged to database
7. ✅ Risk-based retry strategies are applied

---

## 🎯 Next Steps

After successful testing:

1. **Deploy Logic Apps** to Azure (see `COMPLETE_AUTO_REMEDIATION_DEPLOYMENT.md`)
2. **Update .env** with real Logic App URLs
3. **Connect real ADF/Databricks** webhooks
4. **Monitor production** auto-remediation
5. **Tune AI prompts** if needed based on real failures

---

## 📚 Related Documentation

- `AI_DRIVEN_REMEDIATION_ARCHITECTURE.md` - Architecture overview
- `COMPLETE_AUTO_REMEDIATION_DEPLOYMENT.md` - Production deployment
- `logic-apps/` - Logic App definitions

---

**Ready to test!** 🚀

Run: `python test_auto_remediation.py`
