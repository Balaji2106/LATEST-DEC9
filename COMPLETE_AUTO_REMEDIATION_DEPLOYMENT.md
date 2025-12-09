# Complete Auto-Remediation Deployment Guide
# All Platforms: ADF, Databricks, and Airflow

Complete guide to deploy auto-remediation Logic Apps for all remediable errors across Azure Data Factory, Databricks, and Airflow.

---

## 🎯 Overview

This deployment enables **automatic remediation for 38+ error types** across three platforms:
- **Azure Data Factory (ADF)**: 10 error types
- **Databricks**: 19 error types
- **Airflow**: 9 error types

**Remediation Actions:**
- ✅ Retry pipeline/job/task
- ✅ Restart cluster
- ✅ Reinstall libraries
- ✅ Check upstream dependencies

---

## 📋 Prerequisites

### Azure Resources Required
1. **Azure subscription** with permissions to create Logic Apps
2. **Azure Data Factory** (for ADF remediation)
3. **Databricks workspace** (for Databricks remediation)
4. **Airflow deployment** (for Airflow remediation)
5. **RCA app** deployed and publicly accessible

### Permissions Required
- **Logic Apps**: Contributor role on resource group
- **ADF**: Data Factory Contributor
- **Databricks**: Workspace Admin or Contributor
- **Airflow**: Admin or Ops role

---

## 🏗️ Architecture

```
Failure Detected
      ↓
RCA System Analyzes Error
      ↓
Checks REMEDIABLE_ERRORS config
      ↓
Triggers appropriate Logic App
      ↓
Logic App executes remediation:
   - ADF: Retry pipeline
   - Databricks: Retry job / Restart cluster / Reinstall libraries
   - Airflow: Clear and retry task
      ↓
Logic App monitors execution
      ↓
Sends result to RCA callback endpoint
      ↓
RCA updates ticket status
```

---

## 📦 STEP 1: Deploy Logic Apps

### Logic App 1: ADF Pipeline Retry

**File:** `logic-apps/playbook-retry-adf-pipeline.json`

**Deploy via Azure Portal:**
1. Go to **Azure Portal → Logic Apps → Create**
2. Fill in:
   - Resource group: `rg-your-project`
   - Name: `logic-retry-adf-pipeline`
   - Region: Same as ADF
   - Plan: Consumption
3. Click **Review + Create**
4. After deployment, go to **Logic App Designer**
5. Click **Code View** and paste contents of `playbook-retry-adf-pipeline.json`
6. **Important**: Update these values in the JSON:
   - `subscriptions/YOUR_SUBSCRIPTION_ID`
   - `resourcegroups/YOUR_RESOURCE_GROUP`
   - `factories/YOUR_ADF_NAME`
7. Save the Logic App

**Deploy via Azure CLI:**
```bash
az deployment group create \
  --resource-group rg-your-project \
  --template-file logic-apps/playbook-retry-adf-pipeline.json \
  --parameters @parameters.json
```

**Get Webhook URL:**
```bash
az logic workflow show \
  --resource-group rg-your-project \
  --name logic-retry-adf-pipeline \
  --query "accessEndpoint" -o tsv
```

---

### Logic App 2: Databricks Job Retry

**File:** `logic-apps/playbook-retry-databricks-job.json`

**Deploy via Azure Portal:**
1. Create Logic App: `logic-retry-databricks-job`
2. Paste JSON from file
3. **No subscription IDs to update** (uses dynamic values)
4. Save

**Deploy via Azure CLI:**
```bash
az deployment group create \
  --resource-group rg-your-project \
  --template-file logic-apps/playbook-retry-databricks-job.json
```

**Enable Managed Identity:**
```bash
az logic workflow identity assign \
  --resource-group rg-your-project \
  --name logic-retry-databricks-job
```

**Grant Databricks Access:**
```bash
# Get the managed identity principal ID
PRINCIPAL_ID=$(az logic workflow identity show \
  --resource-group rg-your-project \
  --name logic-retry-databricks-job \
  --query principalId -o tsv)

# Add to Databricks workspace as Contributor
az databricks workspace create \
  --resource-group rg-your-project \
  --name your-databricks-workspace \
  --sku premium \
  --managed-resource-group databricks-managed-rg
```

**Get Webhook URL:**
```bash
az logic workflow show \
  --resource-group rg-your-project \
  --name logic-retry-databricks-job \
  --query "accessEndpoint" -o tsv
```

---

### Logic App 3: Databricks Cluster Restart

**File:** `logic-apps/playbook-restart-databricks-cluster.json`

**Deploy via Azure Portal:**
1. Create Logic App: `logic-restart-databricks-cluster`
2. Paste JSON from file
3. Save

**Deploy via Azure CLI:**
```bash
az deployment group create \
  --resource-group rg-your-project \
  --template-file logic-apps/playbook-restart-databricks-cluster.json

# Enable Managed Identity
az logic workflow identity assign \
  --resource-group rg-your-project \
  --name logic-restart-databricks-cluster
```

**Get Webhook URL:**
```bash
az logic workflow show \
  --resource-group rg-your-project \
  --name logic-restart-databricks-cluster \
  --query "accessEndpoint" -o tsv
```

---

### Logic App 4: Databricks Library Reinstall

**File:** `logic-apps/playbook-reinstall-databricks-libraries.json`

**Deploy via Azure Portal:**
1. Create Logic App: `logic-reinstall-databricks-libraries`
2. Paste JSON from file
3. Save

**Deploy via Azure CLI:**
```bash
az deployment group create \
  --resource-group rg-your-project \
  --template-file logic-apps/playbook-reinstall-databricks-libraries.json

# Enable Managed Identity
az logic workflow identity assign \
  --resource-group rg-your-project \
  --name logic-reinstall-databricks-libraries
```

**Get Webhook URL:**
```bash
az logic workflow show \
  --resource-group rg-your-project \
  --name logic-reinstall-databricks-libraries \
  --query "accessEndpoint" -o tsv
```

---

### Logic App 5: Airflow Task Retry

**File:** `logic-apps/playbook-retry-airflow-task.json`

**Deploy via Azure Portal:**
1. Create Logic App: `logic-retry-airflow-task`
2. Paste JSON from file
3. Save

**Deploy via Azure CLI:**
```bash
az deployment group create \
  --resource-group rg-your-project \
  --template-file logic-apps/playbook-retry-airflow-task.json
```

**Get Webhook URL:**
```bash
az logic workflow show \
  --resource-group rg-your-project \
  --name logic-retry-airflow-task \
  --query "accessEndpoint" -o tsv
```

---

## 🔐 STEP 2: Configure Managed Identity Permissions

### For Databricks Logic Apps

All three Databricks Logic Apps need access to your Databricks workspace.

**Option 1: Azure Portal**
1. Go to **Databricks Workspace → Access Control (IAM)**
2. Click **Add role assignment**
3. Select **Contributor**
4. Under **Members**, select **Managed Identity**
5. Search and select all three Logic Apps:
   - `logic-retry-databricks-job`
   - `logic-restart-databricks-cluster`
   - `logic-reinstall-databricks-libraries`
6. Click **Review + assign**

**Option 2: Azure CLI**
```bash
# Get Databricks workspace resource ID
DATABRICKS_ID=$(az databricks workspace show \
  --resource-group rg-your-project \
  --name your-databricks-workspace \
  --query id -o tsv)

# Get Logic App principal IDs
RETRY_JOB_ID=$(az logic workflow identity show \
  --resource-group rg-your-project \
  --name logic-retry-databricks-job \
  --query principalId -o tsv)

RESTART_CLUSTER_ID=$(az logic workflow identity show \
  --resource-group rg-your-project \
  --name logic-restart-databricks-cluster \
  --query principalId -o tsv)

REINSTALL_LIB_ID=$(az logic workflow identity show \
  --resource-group rg-your-project \
  --name logic-reinstall-databricks-libraries \
  --query principalId -o tsv)

# Assign Contributor role
az role assignment create \
  --assignee $RETRY_JOB_ID \
  --role "Contributor" \
  --scope $DATABRICKS_ID

az role assignment create \
  --assignee $RESTART_CLUSTER_ID \
  --role "Contributor" \
  --scope $DATABRICKS_ID

az role assignment create \
  --assignee $REINSTALL_LIB_ID \
  --role "Contributor" \
  --scope $DATABRICKS_ID
```

### For ADF Logic App

**Option 1: Azure Portal**
1. Go to **Data Factory → Access Control (IAM)**
2. Add role assignment: **Data Factory Contributor**
3. Select managed identity: `logic-retry-adf-pipeline`

**Option 2: Azure CLI**
```bash
ADF_ID=$(az datafactory show \
  --resource-group rg-your-project \
  --name your-adf-name \
  --query id -o tsv)

ADF_LOGIC_ID=$(az logic workflow identity show \
  --resource-group rg-your-project \
  --name logic-retry-adf-pipeline \
  --query principalId -o tsv)

az role assignment create \
  --assignee $ADF_LOGIC_ID \
  --role "Data Factory Contributor" \
  --scope $ADF_ID
```

---

## ⚙️ STEP 3: Configure Environment Variables

Update your RCA app's `.env` file with Logic App webhook URLs:

```bash
# ========================================================================
# AUTO-REMEDIATION CONFIGURATION
# ========================================================================

AUTO_REMEDIATION_ENABLED=true
PUBLIC_BASE_URL=https://your-rca-app.azurewebsites.net

# ========================================================================
# ADF LOGIC APPS
# ========================================================================

PLAYBOOK_RETRY_PIPELINE=https://prod-12.northcentralus.logic.azure.com:443/workflows/abc123/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=YOUR_SIG

# ========================================================================
# DATABRICKS LOGIC APPS
# ========================================================================

PLAYBOOK_RETRY_JOB=https://prod-13.northcentralus.logic.azure.com:443/workflows/def456/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=YOUR_SIG

PLAYBOOK_RESTART_CLUSTER=https://prod-14.northcentralus.logic.azure.com:443/workflows/ghi789/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=YOUR_SIG

PLAYBOOK_REINSTALL_LIBRARIES=https://prod-15.northcentralus.logic.azure.com:443/workflows/jkl012/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=YOUR_SIG

# ========================================================================
# AIRFLOW LOGIC APPS
# ========================================================================

PLAYBOOK_RETRY_AIRFLOW_TASK=https://prod-16.northcentralus.logic.azure.com:443/workflows/mno345/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=YOUR_SIG

# Airflow connection details (for Logic App to use)
AIRFLOW_BASE_URL=https://your-airflow.com
AIRFLOW_API_USERNAME=your-airflow-user
AIRFLOW_API_PASSWORD=your-airflow-password

# ========================================================================
# DATABRICKS API CONFIGURATION
# ========================================================================

DATABRICKS_WORKSPACE_URL=https://adb-1234567890123456.7.azuredatabricks.net
DATABRICKS_TOKEN=dapi1234567890abcdef  # Only if not using managed identity

# ========================================================================
# SLACK NOTIFICATIONS (OPTIONAL)
# ========================================================================

SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_ALERT_CHANNEL=aiops-alerts

# ========================================================================
# AZURE SQL DATABASE (OPTIONAL)
# ========================================================================

DB_TYPE=azure_sql  # or sqlite
AZURE_SQL_SERVER=your-sql-server.database.windows.net
AZURE_SQL_DATABASE=rca_tickets
AZURE_SQL_USERNAME=sqladmin
AZURE_SQL_PASSWORD=your-password
```

---

## 🧪 STEP 4: Test Auto-Remediation

### Test 1: ADF Pipeline Retry

Create a test ADF pipeline that fails:

```json
{
  "name": "test-auto-remediation",
  "activities": [
    {
      "name": "FailActivity",
      "type": "Fail",
      "userProperties": [],
      "typeProperties": {
        "message": "NetworkTimeout - Testing auto-remediation",
        "errorCode": "NetworkTimeout"
      }
    }
  ]
}
```

**Trigger and verify:**
1. Run the pipeline manually
2. Wait for failure webhook to RCA
3. Check RCA logs for auto-remediation trigger
4. Verify Logic App execution in Azure Portal
5. Check ticket status in RCA dashboard

**Expected result:** Ticket shows "Auto-Remediation In Progress" → "Auto-Resolved" (or "Open" if retries exhausted)

---

### Test 2: Databricks Job Retry

Create a test Databricks job that fails:

```python
# test_auto_remediation_job.py
import random
import sys

# Simulate intermittent failure
if random.random() < 0.7:  # 70% chance of failure
    raise ConnectionError("DatabricksDriverNotResponding - Testing auto-remediation")
else:
    print("Job succeeded!")
```

**Trigger and verify:**
1. Create Databricks job with the test notebook
2. Run the job
3. If it fails, webhook triggers RCA
4. RCA triggers `PLAYBOOK_RETRY_JOB`
5. Logic App retries the job
6. Verify callback received

**Expected result:** Job retried up to 3 times, ticket auto-resolved if successful

---

### Test 3: Databricks Cluster Restart

Simulate cluster memory exhaustion:

```python
# test_cluster_oom.py
# This will cause OUT_OF_MEMORY error
huge_list = [i for i in range(10**10)]  # Allocate massive memory
```

**Expected result:** RCA detects OOM, triggers cluster restart, retries job

---

### Test 4: Airflow Task Retry

Create test Airflow DAG:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from rca_callbacks import on_failure_callback

def fail_with_connection_error():
    raise ConnectionError("AirflowConnectionError - Testing auto-remediation")

with DAG(
    'test_auto_remediation',
    default_args={'on_failure_callback': on_failure_callback},
    schedule_interval=None,
    start_date=datetime(2025, 1, 1)
) as dag:
    test_task = PythonOperator(
        task_id='fail_task',
        python_callable=fail_with_connection_error
    )
```

**Expected result:** Task fails → RCA triggered → Logic App clears and retries task

---

## 📊 STEP 5: Monitor Auto-Remediation

### View Logic App Execution History

**Azure Portal:**
1. Go to Logic App
2. Click **Overview**
3. View **Runs history**
4. Click on any run to see detailed execution

**Azure CLI:**
```bash
az logic workflow run list \
  --resource-group rg-your-project \
  --name logic-retry-databricks-job \
  --top 10
```

### Check RCA Logs

```bash
# View auto-remediation logs
grep "AUTO-REM" /var/log/rca-app.log

# View callback logs
grep "CALLBACK" /var/log/rca-app.log

# View remediation attempts
sqlite3 data/tickets.db "SELECT * FROM remediation_attempts ORDER BY started_at DESC LIMIT 10;"
```

### Query Remediation Statistics

```sql
-- Success rate by error type
SELECT
    error_type,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM remediation_attempts
GROUP BY error_type
ORDER BY total_attempts DESC;

-- Average remediation time
SELECT
    error_type,
    AVG(julianday(completed_at) - julianday(started_at)) * 24 * 60 as avg_minutes
FROM remediation_attempts
WHERE status IN ('completed', 'failed')
GROUP BY error_type;

-- Remediation attempts per ticket
SELECT
    t.id,
    t.pipeline,
    t.error_type,
    COUNT(ra.id) as attempts,
    MAX(ra.status) as final_status
FROM tickets t
LEFT JOIN remediation_attempts ra ON t.id = ra.ticket_id
WHERE t.remediation_status != 'not_eligible'
GROUP BY t.id
ORDER BY attempts DESC
LIMIT 20;
```

---

## 🎯 Supported Error Types

### Azure Data Factory (10 errors)
| Error Type | Action | Max Retries | Backoff (seconds) |
|------------|--------|-------------|-------------------|
| SqlFailedToConnect | retry_pipeline | 3 | 60, 120, 300 |
| NetworkTimeout | retry_pipeline | 3 | 30, 60, 120 |
| GatewayTimeout | retry_pipeline | 3 | 30, 60, 120 |
| HttpConnectionFailed | retry_pipeline | 3 | 30, 60, 120 |
| ConnectionError | retry_pipeline | 3 | 30, 60, 120 |
| ThrottlingError | retry_pipeline | 5 | 30, 60, 120, 300, 600 |
| ServiceBusy | retry_pipeline | 4 | 60, 120, 300, 600 |
| TransientError | retry_pipeline | 3 | 30, 60, 120 |
| TemporaryError | retry_pipeline | 3 | 30, 60, 120 |
| UserErrorSourceBlobNotExists | check_upstream | 2 | 300, 600 |

### Databricks (19 errors)
| Error Type | Action | Max Retries | Backoff (seconds) |
|------------|--------|-------------|-------------------|
| DRIVER_UNREACHABLE | restart_cluster | 3 | 60, 180, 300 |
| DatabricksDriverNotResponding | retry_job | 3 | 30, 60, 120 |
| CLOUD_PROVIDER_SHUTDOWN | retry_job | 3 | 60, 120, 300 |
| CLOUD_PROVIDER_LAUNCH_FAILURE | restart_cluster | 3 | 120, 300, 600 |
| OUT_OF_MEMORY | restart_cluster | 2 | 120, 300 |
| ClusterMemoryExhausted | restart_cluster | 2 | 60, 180 |
| OUT_OF_DISK | restart_cluster | 2 | 120, 300 |
| INIT_SCRIPT_FAILURE | restart_cluster | 2 | 60, 180 |
| LIBRARY_INSTALLATION_FAILURE | reinstall_libraries | 3 | 60, 120, 300 |
| DatabricksLibraryInstallationError | reinstall_libraries | 2 | 60, 180 |
| LibraryInstallationFailed | reinstall_libraries | 2 | 60, 180 |
| NETWORK_FAILURE | retry_job | 3 | 30, 60, 120 |
| CLUSTER_START_TIMEOUT | restart_cluster | 2 | 180, 300 |
| DatabricksJobExecutionError | retry_job | 3 | 30, 60, 120 |
| DatabricksClusterStartFailure | restart_cluster | 2 | 60, 180 |

### Airflow (9 errors)
| Error Type | Action | Max Retries | Backoff (seconds) |
|------------|--------|-------------|-------------------|
| AirflowConnectionError | retry_task | 3 | 30, 60, 120 |
| AirflowTimeoutError | retry_task | 2 | 60, 120 |
| SensorTimeout | retry_task | 2 | 300, 600 |
| AirflowOutOfMemory | retry_task | 2 | 60, 120 |
| FileNotFound | retry_task | 2 | 60, 120 |
| APIError | retry_task | 3 | 30, 60, 120 |
| DatabaseError | retry_task | 3 | 30, 60, 120 |
| DatabricksSubmitRunError | retry_task | 2 | 60, 120 |

---

## 🔧 Troubleshooting

### Problem: Logic App Not Triggered

**Check 1: Is auto-remediation enabled?**
```bash
grep "AUTO_REMEDIATION_ENABLED" .env
# Should be: AUTO_REMEDIATION_ENABLED=true
```

**Check 2: Is error type remediable?**
```bash
# Check RCA logs
grep "is not auto-remediable" /var/log/rca-app.log
```

**Check 3: Is webhook URL correct?**
```bash
# Test webhook manually
curl -X POST "LOGIC_APP_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TEST-123",
    "callback_url": "https://your-rca-app.com/remediation-callback"
  }'
```

### Problem: Logic App Fails with 403 Forbidden

**Cause:** Managed identity doesn't have permissions

**Fix:**
```bash
# Re-assign permissions (see STEP 2)
az role assignment create \
  --assignee YOUR_PRINCIPAL_ID \
  --role "Contributor" \
  --scope YOUR_RESOURCE_ID
```

### Problem: Callback Not Received

**Check 1: Is callback URL correct?**
```bash
echo $PUBLIC_BASE_URL/remediation-callback
```

**Check 2: Is RCA app accessible from Logic App?**
```bash
# Test from Azure Cloud Shell
curl https://your-rca-app.com/health
```

**Check 3: Check Logic App logs**
- Azure Portal → Logic App → Run History → Click failed run → View callback action

---

## 📈 Performance Tuning

### Optimize Retry Backoff

For high-priority pipelines, reduce backoff times:

```python
"NetworkTimeout": {
    "action": "retry_pipeline",
    "max_retries": 5,
    "backoff_seconds": [10, 20, 30, 60, 120],  # Faster retries
    "playbook_url": os.getenv("PLAYBOOK_RETRY_PIPELINE"),
    "platform": "adf"
}
```

### Increase Timeout Limits

For long-running jobs, increase Logic App timeout:

```json
"Monitor_Job_Until_Complete": {
    "type": "Until",
    "limit": {
        "count": 240,       // Increase from 120
        "timeout": "PT4H"   // Increase from PT2H
    }
}
```

---

## 🚀 Production Deployment Checklist

- [ ] All 5 Logic Apps deployed
- [ ] Managed identities assigned
- [ ] Permissions granted (ADF, Databricks)
- [ ] Environment variables configured
- [ ] Webhook URLs tested
- [ ] Test failures created and verified
- [ ] Monitoring dashboards set up
- [ ] Slack notifications configured
- [ ] Audit logging enabled
- [ ] Database backups configured
- [ ] Documentation updated for team

---

## 📞 Support

If issues persist:
1. Check Azure Logic App run history for detailed errors
2. Review RCA app logs: `grep "AUTO-REM" /var/log/rca-app.log`
3. Verify network connectivity between Logic Apps and RCA app
4. Ensure all managed identities have correct permissions
5. Test webhooks manually with curl

---

**Your complete auto-remediation system is ready! 🎉**

**Total Coverage:**
- ✅ 10 ADF errors
- ✅ 19 Databricks errors
- ✅ 9 Airflow errors
- ✅ **38 total auto-remediable errors**
