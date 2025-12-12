# Integrations Guide

Complete guide for integrating the AIOps RCA Assistant with JIRA, Slack, Azure Data Factory, Databricks, and Airflow.

---

## 📋 Table of Contents

1. [JIRA Integration](#jira-integration)
2. [Slack Integration](#slack-integration)
3. [Azure Data Factory Integration](#azure-data-factory-integration)
4. [Databricks Integration](#databricks-integration)
5. [Airflow Integration](#airflow-integration)
6. [Azure Logic Apps (Auto-Remediation)](#azure-logic-apps-auto-remediation)

---

## JIRA Integration

### Overview

The JIRA integration provides:
- Automatic ticket creation for failures
- Bidirectional status sync (JIRA ↔ RCA System)
- Detailed RCA information in JIRA tickets
- Automatic ticket closure on remediation success

### Prerequisites

- JIRA Cloud account
- Project with create permission
- JIRA API token

### Step 1: Create JIRA API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name: `AIOps RCA System`
4. Copy the token (starts with `ATATT...`)

### Step 2: Configure JIRA in .env

```bash
ITSM_TOOL=jira
JIRA_DOMAIN=https://your-company.atlassian.net
JIRA_USER_EMAIL=aiops-bot@company.com
JIRA_API_TOKEN=ATATT3xFfGF0_your_token_here
JIRA_PROJECT_KEY=APAIOPS
JIRA_WEBHOOK_SECRET=your-random-secret
```

### Step 3: Test JIRA Connection

```bash
# Test authentication
curl -u "your-email@company.com:your-api-token" \
  https://your-company.atlassian.net/rest/api/3/myself

# Should return your user details
```

### Step 4: Configure JIRA Webhook (Bidirectional Sync)

1. In JIRA, go to **Settings → System → WebHooks**
2. Click **Create a WebHook**
3. Configure:
   - **Name:** AIOps RCA Status Sync
   - **Status:** Enabled
   - **URL:** `https://your-rca-server.com/jira-webhook?secret=your-random-secret`
   - **Events:** Issue Updated
   - **JQL:** `project = APAIOPS`
4. Save

### JIRA Ticket Format

**Title:**
```
ADF Pipeline Failure: <pipeline_name>
```

**Description:**
```
Ticket ID: ADF-20251212T100000-abc123
Pipeline: pipeline-name
Run ID: run-id-12345
Severity: Medium
Priority: P3
SLA: 2 hours

Root Cause Analysis:
<AI-generated root cause>

Recommendations:
• Step 1: Check source data availability
• Step 2: Verify connection string
• Step 3: Review pipeline configuration

Error Type: UserErrorSourceBlobNotExists
Confidence: High

Dashboard: https://your-rca-server.com/dashboard?ticket=ADF-20251212T100000-abc123
```

### JIRA Status Mapping

| JIRA Status | RCA Status | Action |
|-------------|------------|--------|
| Done, Closed | acknowledged | Ticket closed |
| In Progress | in_progress | Work in progress |
| To Do, Open | open | Ticket open |
| Reopened | in_progress | Ticket reopened |

### Troubleshooting JIRA

**Issue: 401 Unauthorized**
```bash
# Verify credentials
curl -u "your-email:your-token" \
  https://your-company.atlassian.net/rest/api/3/myself
```

**Issue: Ticket not created**
- Check JIRA project exists
- Verify create permission
- Check application logs for errors

---

## Slack Integration

### Overview

The Slack integration provides:
- Real-time failure notifications
- Rich formatted messages with RCA details
- Status updates (ticket closed/reopened)
- Dashboard links for investigation

### Prerequisites

- Slack workspace
- Permission to create/install apps

### Step 1: Create Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. App Name: `AIOps RCA Bot`
4. Select your workspace

### Step 2: Configure OAuth Scopes

1. Go to **OAuth & Permissions**
2. Under **Bot Token Scopes**, add:
   - `chat:write` - Send messages
   - `chat:write.public` - Send to public channels without joining
   - `channels:read` - List channels
3. Click **Install to Workspace**
4. Authorize the app

### Step 3: Copy Bot Token

1. Under **OAuth & Permissions**
2. Copy **Bot User OAuth Token** (starts with `xoxb-`)

### Step 4: Get Channel ID

**Method 1: From Slack App**
1. Right-click channel → View channel details
2. Scroll down → Copy Channel ID

**Method 2: Using API**
```bash
curl -X GET "https://slack.com/api/conversations.list" \
  -H "Authorization: Bearer xoxb-your-token"
```

### Step 5: Configure Slack in .env

```bash
SLACK_BOT_TOKEN=xoxb-YOUR-BOT-TOKEN-HERE
SLACK_ALERT_CHANNEL=C01234567AB  # or aiops-rca-alerts
```

### Step 6: Test Slack Integration

```bash
curl -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer xoxb-your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C01234567AB",
    "text": "Test message from AIOps RCA System"
  }'
```

### Slack Message Format

**Initial Failure Alert:**
```
🔴 ALERT: pipeline-name - Medium (P3)

Ticket: ADF-20251212T100000-abc123
ITSM Ticket: APAIOPS-123
Run ID: run-id-12345
Error Type: UserErrorSourceBlobNotExists

Root Cause: The pipeline failed because the source blob file was not found...
Confidence: High

Resolution Steps:
• Check upstream data availability
• Verify file path configuration
• Review pipeline schedule

[Open in Dashboard] (button)
```

**Ticket Closed:**
```
✅ pipeline-name - CLOSED

Ticket: ADF-20251212T100000-abc123
ITSM Ticket: APAIOPS-123
Run ID: run-id-12345
Status: CLOSED

Closed by John Doe on 2025-12-12 10:30:00 UTC

Root Cause: ...
Confidence: High
Error Type: UserErrorSourceBlobNotExists

Resolution Steps:
...

[Open in Dashboard] (button)
```

---

## Azure Data Factory Integration

### Overview

ADF integration monitors pipeline failures via Azure Monitor alerts and Log Analytics.

### Architecture

```
ADF Pipeline Fails → Diagnostic Settings → Log Analytics → Alert Rule → Action Group → RCA Webhook
```

### Step 1: Enable Diagnostic Settings

```bash
# Enable ADF diagnostic logs
az monitor diagnostic-settings create \
  --resource /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.DataFactory/factories/ADF_NAME \
  --name "adf-diagnostics" \
  --workspace /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.OperationalInsights/workspaces/WORKSPACE_NAME \
  --logs '[
    {"category":"PipelineRuns","enabled":true},
    {"category":"ActivityRuns","enabled":true},
    {"category":"TriggerRuns","enabled":true}
  ]'
```

### Step 2: Create Action Group

```bash
az monitor action-group create \
  --resource-group rg_techdemo_2025_Q4 \
  --name "rca-webhook-action-group" \
  --short-name "rcawebhook" \
  --webhook-receiver name=rca-webhook \
                      service-uri=https://your-rca-server.com/azure-monitor
```

### Step 3: Create Alert Rule

```bash
az monitor scheduled-query create \
  --resource-group rg_techdemo_2025_Q4 \
  --name "adf-pipeline-failure-alert" \
  --location eastus \
  --scopes /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.OperationalInsights/workspaces/WORKSPACE \
  --condition "count 'Placeholder' > 0" \
  --condition-query "ADFPipelineRun
| where TimeGenerated > ago(15m)
| where Status == 'Failed'
| join kind=inner (
    ADFActivityRun
    | where TimeGenerated > ago(15m)
    | where Status == 'Failed'
) on PipelineRunId
| project TimeGenerated, PipelineName, RunId=PipelineRunId, ActivityName, ErrorCode, ErrorMessage" \
  --evaluation-frequency 5m \
  --window-size 15m \
  --severity 3 \
  --action-groups /subscriptions/SUB_ID/resourceGroups/RG/providers/microsoft.insights/actionGroups/rca-webhook-action-group
```

### Tested Error Types

| Error Code | Description | Auto-Remediable |
|------------|-------------|-----------------|
| UserErrorSourceBlobNotExists | Source file not found | No (check upstream) |
| GatewayTimeout | ADF gateway timeout | Yes (retry) |
| HttpConnectionFailed | Connection failure | Yes (retry) |
| InternalServerError | ADF internal error | Yes (retry) |
| UserErrorInvalidDataType | Schema mismatch | No (manual fix) |
| AuthenticationError | Auth failed | No (fix credentials) |

---

## Databricks Integration

### Overview

Databricks integration monitors cluster and job failures via Azure Monitor and Databricks API.

### Architecture

```
Databricks Cluster/Job Fails → Diagnostic Settings → Log Analytics → Alert Rule → RCA Webhook → Databricks API (fetch details)
```

### Step 1: Create Databricks PAT

1. In Databricks workspace
2. User Settings → Developer → Access Tokens
3. Generate New Token
4. Lifetime: 365 days
5. Copy token (starts with `dapi...`)

### Step 2: Configure Databricks in .env

```bash
DATABRICKS_WORKSPACE_URL=https://adb-1234567890123456.12.azuredatabricks.net
DATABRICKS_TOKEN=dapi-YOUR-DATABRICKS-TOKEN-HERE
```

### Step 3: Enable Databricks Diagnostic Settings

```bash
az monitor diagnostic-settings create \
  --resource /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.Databricks/workspaces/DBX_WORKSPACE \
  --name "databricks-diagnostics" \
  --workspace /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.OperationalInsights/workspaces/WORKSPACE \
  --logs '[
    {"category":"clusters","enabled":true},
    {"category":"jobs","enabled":true},
    {"category":"notebook","enabled":true}
  ]'
```

### Step 4: Create Databricks Alert Rule

```bash
az monitor scheduled-query create \
  --resource-group rg_techdemo_2025_Q4 \
  --name "databricks-cluster-failure" \
  --location eastus \
  --scopes /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.OperationalInsights/workspaces/WORKSPACE \
  --condition "count 'Placeholder' > 0" \
  --condition-query "DatabricksClusters
| where TimeGenerated > ago(15m)
| extend req = todynamic(RequestParams)
| extend clusterId = tostring(req.clusterId)
| extend clusterName = tostring(req.clusterName)
| extend clusterState = tostring(req.clusterState)
| extend termination = tostring(req.clusterTerminationReasonCode)
| where clusterState in ('Error', 'Terminated', 'Restarting')
| where isempty(termination) == false
| where termination !in ('INACTIVITY', 'USER_REQUEST', 'SUCCESS', 'JOB_FINISHED')
| project TimeGenerated, clusterId, clusterName, clusterState, termination" \
  --evaluation-frequency 5m \
  --window-size 15m \
  --severity 2 \
  --action-groups /subscriptions/SUB_ID/resourceGroups/RG/providers/microsoft.insights/actionGroups/rca-webhook-action-group
```

### Databricks Error Classification

| Error Type | Remediable | Action |
|------------|------------|--------|
| CLOUD_PROVIDER_LAUNCH_FAILURE | Yes | Restart with different instance type |
| DRIVER_NOT_RESPONDING | Yes | Restart cluster |
| BOOTSTRAP_TIMEOUT | Yes | Increase timeout, retry |
| LIBRARY_INSTALLATION_FAILED | Yes | Reinstall libraries |
| PERMISSION_DENIED | No | Fix IAM/permissions |
| SPARK_EXCEPTION | No | Fix application code |

---

## Airflow Integration

### Overview

Airflow integration uses task failure callbacks to send failure notifications to RCA system.

### Step 1: Add Failure Callback to DAG

**File:** `airflow/dags/your_dag.py`

```python
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

RCA_WEBHOOK_URL = "http://rca-server:8000/airflow-monitor"

def airflow_failure_callback(context):
    """Send failure notification to RCA system"""
    payload = {
        "dag_id": context['dag'].dag_id,
        "task_id": context['task_instance'].task_id,
        "execution_date": context['execution_date'].isoformat(),
        "run_id": context['run_id'],
        "state": context['task_instance'].state,
        "try_number": context['task_instance'].try_number,
        "max_tries": context['task_instance'].max_tries,
        "exception": str(context.get('exception', '')),
        "log_url": context['task_instance'].log_url,
        "operator": context['task'].__class__.__name__
    }

    try:
        response = requests.post(RCA_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"RCA ticket created: {response.json().get('ticket_id')}")
    except Exception as e:
        print(f"Failed to send RCA notification: {e}")

# Apply to entire DAG
default_args = {
    'owner': 'airflow',
    'on_failure_callback': airflow_failure_callback
}

with DAG(
    'my_production_dag',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False
) as dag:

    task1 = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data_func
    )

    task2 = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data_func,
        # Can override at task level
        on_failure_callback=airflow_failure_callback
    )
```

### Step 2: Test Airflow Integration

```python
# Test DAG with intentional failure
with DAG('test_rca_integration', default_args=default_args) as dag:
    def fail_intentionally():
        raise Exception("Test error for RCA integration")

    test_task = PythonOperator(
        task_id='test_failure',
        python_callable=fail_intentionally
    )
```

### Airflow Error Classification

The system automatically classifies Airflow errors:

| Error Pattern | Classification | Remediable |
|---------------|----------------|------------|
| connection.*error | ConnectionError | Yes (retry) |
| timeout | TimeoutError | Yes (extend timeout) |
| out.*of.*memory | OutOfMemory | Yes (increase resources) |
| sensor.*timeout | SensorTimeout | Yes (check upstream) |
| file.*not.*found | FileNotFound | Yes (check upstream) |
| API.*error | APIError | Yes (retry) |
| authentication.*failed | AuthenticationError | No (fix credentials) |

---

## Azure Logic Apps (Auto-Remediation)

### Overview

Logic Apps enable automatic remediation of failures by retrying pipelines, restarting clusters, etc.

### Step 1: Create Logic App for ADF Retry

1. In Azure Portal → Create Logic App
2. Name: `playbook-retry-adf-pipeline`
3. Region: Same as ADF
4. Type: Consumption

### Step 2: Configure HTTP Trigger

```json
{
  "type": "Request",
  "kind": "Http",
  "inputs": {
    "schema": {
      "type": "object",
      "properties": {
        "ticket_id": {"type": "string"},
        "pipeline_name": {"type": "string"},
        "original_run_id": {"type": "string"},
        "callback_url": {"type": "string"}
      }
    }
  }
}
```

### Step 3: Add ADF Retry Action

```json
{
  "type": "ApiConnection",
  "inputs": {
    "host": {
      "connection": {
        "name": "@parameters('$connections')['azuredatafactory']['connectionId']"
      }
    },
    "method": "post",
    "path": "/subscriptions/@{encodeURIComponent('SUB_ID')}/resourcegroups/@{encodeURIComponent('RG')}/providers/Microsoft.DataFactory/factories/@{encodeURIComponent('ADF_NAME')}/pipelines/@{encodeURIComponent(triggerBody()?['pipeline_name'])}/createRun",
    "queries": {
      "x-ms-api-version": "2018-06-01"
    }
  }
}
```

### Step 4: Send Callback

```json
{
  "type": "Http",
  "inputs": {
    "method": "POST",
    "uri": "@triggerBody()?['callback_url']",
    "body": {
      "ticket_id": "@triggerBody()?['ticket_id']",
      "original_run_id": "@triggerBody()?['original_run_id']",
      "remediation_run_id": "@body('Create_Pipeline_Run')?['runId']",
      "status": "succeeded",
      "pipeline_name": "@triggerBody()?['pipeline_name']"
    }
  }
}
```

### Step 5: Configure .env with Logic App URL

```bash
AUTO_REMEDIATION_ENABLED=true
PLAYBOOK_RETRY_PIPELINE=https://prod-12.eastus.logic.azure.com/workflows/abc.../triggers/manual/paths/invoke?...
```

---

## Integration Testing

### Test All Integrations End-to-End

```bash
# 1. Trigger test failure in ADF
# Manually fail a pipeline in Azure Portal

# 2. Verify RCA System
# Check logs for ticket creation
tail -f logs/rca.log

# 3. Check JIRA
# Verify ticket created in JIRA project

# 4. Check Slack
# Verify message posted in Slack channel

# 5. Update JIRA to Done
# Verify RCA system status updates to "acknowledged"

# 6. Check Slack again
# Verify message updated to "CLOSED"
```

---

**Next:** [07_FUNCTION_REFERENCE.md](07_FUNCTION_REFERENCE.md) - Function-Level Documentation
