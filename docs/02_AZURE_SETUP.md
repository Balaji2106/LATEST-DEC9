# Azure Setup & Permissions Guide

This document provides **complete Azure configuration** including all required permissions, resource setup, and integration configuration.

---

## 📋 Table of Contents

1. [Azure Resources Overview](#azure-resources-overview)
2. [Required Azure Permissions](#required-azure-permissions)
3. [Azure Monitor Setup](#azure-monitor-setup)
4. [Azure Data Factory Integration](#azure-data-factory-integration)
5. [Databricks Integration](#databricks-integration)
6. [Azure Blob Storage Setup](#azure-blob-storage-setup)
7. [Logic Apps Setup](#logic-apps-setup)
8. [Network & Security Configuration](#network--security-configuration)

---

## Azure Resources Overview

###

 Required Azure Services

| Service | Purpose | Cost Estimate |
|---------|---------|---------------|
| **Azure Monitor** | Alert rules for ADF/Databricks | ~$10/month |
| **Log Analytics Workspace** | Store Databricks/ADF logs | ~$50/month |
| **Azure Blob Storage** | Store failure payloads/logs | ~$5/month |
| **Azure Data Factory** | Data pipeline (monitored service) | Variable |
| **Databricks** | Spark workloads (monitored service) | Variable |
| **Logic Apps** | Auto-remediation workflows | ~$20/month |
| **Action Groups** | Webhook delivery | Free |

---

## Required Azure Permissions

### 1. Service Principal / Managed Identity Permissions

Create a Service Principal for the RCA system:

```bash
# Create service principal
az ad sp create-for-rbac --name "aiops-rca-sp" --role Contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Output (save these values):
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "aiops-rca-sp",
  "password": "your-client-secret",
  "tenant": "your-tenant-id"
}
```

### 2. Azure Monitor Permissions

**Required Roles:**
- `Monitoring Reader` - Read alert rules and metrics
- `Monitoring Contributor` - Create/edit alert rules (optional)

**Assign Role:**
```bash
az role assignment create \
  --assignee "aiops-rca-sp-app-id" \
  --role "Monitoring Reader" \
  --scope "/subscriptions/YOUR_SUBSCRIPTION_ID"
```

**Required Permissions:**
```
Microsoft.Insights/AlertRules/Read
Microsoft.Insights/AlertRules/Write
Microsoft.Insights/Components/Read
Microsoft.Insights/ScheduledQueryRules/Read
Microsoft.Insights/ScheduledQueryRules/Write
Microsoft.Insights/ActionGroups/Read
Microsoft.Insights/ActionGroups/Write
```

### 3. Log Analytics Workspace Permissions

**Required Roles:**
- `Log Analytics Reader` - Query logs

**Assign Role:**
```bash
az role assignment create \
  --assignee "aiops-rca-sp-app-id" \
  --role "Log Analytics Reader" \
  --scope "/subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.OperationalInsights/workspaces/WORKSPACE_NAME"
```

**Required Permissions:**
```
Microsoft.OperationalInsights/workspaces/read
Microsoft.OperationalInsights/workspaces/query/read
Microsoft.OperationalInsights/workspaces/query/*/read
```

### 4. Azure Blob Storage Permissions

**Required Roles:**
- `Storage Blob Data Contributor` - Upload logs/payloads

**Assign Role:**
```bash
az role assignment create \
  --assignee "aiops-rca-sp-app-id" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/STORAGE_ACCOUNT_NAME"
```

**Required Permissions:**
```
Microsoft.Storage/storageAccounts/read
Microsoft.Storage/storageAccounts/blobServices/containers/read
Microsoft.Storage/storageAccounts/blobServices/containers/write
Microsoft.Storage/storageAccounts/blobServices/generateUserDelegationKey/action
```

**Connection String Alternative:**
```bash
# Get storage account connection string
az storage account show-connection-string \
  --name YOUR_STORAGE_ACCOUNT \
  --resource-group YOUR_RESOURCE_GROUP
```

### 5. Databricks Permissions

**Required:**
- Databricks Workspace Access
- Personal Access Token (PAT) or Service Principal

**Create Databricks PAT:**
1. Go to Databricks Workspace
2. User Settings → Access Tokens
3. Generate New Token
4. Save token (starts with `dapi...`)

**Required Databricks API Permissions:**
```
clusters/get
clusters/list
clusters/events/get
jobs/runs/get
jobs/runs/list
```

**Service Principal Setup (Recommended for Production):**
```bash
# Add service principal to Databricks workspace
az databricks workspace update \
  --resource-group YOUR_RESOURCE_GROUP \
  --name YOUR_WORKSPACE \
  --public-network-access Enabled

# In Databricks UI:
# Settings → Admin Console → Service Principals
# Add the Azure AD app ID
```

### 6. Azure Data Factory Permissions

**Required Roles:**
- `Data Factory Contributor` (if modifying pipelines)
- `Reader` (if only monitoring)

**Assign Role:**
```bash
az role assignment create \
  --assignee "aiops-rca-sp-app-id" \
  --role "Reader" \
  --scope "/subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.DataFactory/factories/FACTORY_NAME"
```

**Required Permissions:**
```
Microsoft.DataFactory/factories/read
Microsoft.DataFactory/factories/pipelineruns/read
Microsoft.DataFactory/factories/activityruns/read
```

### 7. Logic Apps Permissions

**Required Roles:**
- `Logic App Contributor` - Create/edit Logic Apps

**Assign Role:**
```bash
az role assignment create \
  --assignee "aiops-rca-sp-app-id" \
  --role "Logic App Contributor" \
  --scope "/subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP"
```

**Required Permissions:**
```
Microsoft.Logic/workflows/read
Microsoft.Logic/workflows/write
Microsoft.Logic/workflows/run/action
Microsoft.Logic/workflows/runs/read
```

---

## Azure Monitor Setup

### Step 1: Create Log Analytics Workspace

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
  --resource-group rg_techdemo_2025_Q4 \
  --workspace-name log-techdemo-rca \
  --location eastus
```

### Step 2: Connect Databricks to Log Analytics

```bash
# Enable diagnostic settings for Databricks
az monitor diagnostic-settings create \
  --resource /subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.Databricks/workspaces/DATABRICKS_WORKSPACE \
  --name "databricks-diagnostics" \
  --workspace /subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.OperationalInsights/workspaces/log-techdemo-rca \
  --logs '[{"category":"clusters","enabled":true},{"category":"jobs","enabled":true}]'
```

### Step 3: Connect Azure Data Factory to Log Analytics

```bash
# Enable diagnostic settings for ADF
az monitor diagnostic-settings create \
  --resource /subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.DataFactory/factories/ADF_FACTORY_NAME \
  --name "adf-diagnostics" \
  --workspace /subscriptions/SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.OperationalInsights/workspaces/log-techdemo-rca \
  --logs '[{"category":"PipelineRuns","enabled":true},{"category":"ActivityRuns","enabled":true}]'
```

### Step 4: Create Action Group

```bash
# Create action group for webhooks
az monitor action-group create \
  --resource-group rg_techdemo_2025_Q4 \
  --name "rca-webhook-action-group" \
  --short-name "rcawebhook" \
  --webhook-receiver name=rca-webhook \
                      service-uri=https://your-rca-server.com/azure-monitor
```

### Step 5: Create Alert Rules

#### Databricks Cluster Failure Alert

```bash
# Create Databricks alert rule
az monitor scheduled-query create \
  --resource-group rg_techdemo_2025_Q4 \
  --name "databricks-alert" \
  --location eastus \
  --scopes /subscriptions/SUBSCRIPTION_ID/resourceGroups/rg_techdemo_2025_Q4/providers/Microsoft.OperationalInsights/workspaces/log-techdemo-rca \
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
  --severity 3 \
  --action-groups /subscriptions/SUBSCRIPTION_ID/resourceGroups/rg_techdemo_2025_Q4/providers/microsoft.insights/actionGroups/rca-webhook-action-group
```

#### Azure Data Factory Pipeline Failure Alert

```bash
# Create ADF alert rule
az monitor scheduled-query create \
  --resource-group rg_techdemo_2025_Q4 \
  --name "tech-demo-adf-alert" \
  --location eastus \
  --scopes /subscriptions/SUBSCRIPTION_ID/resourceGroups/rg_techdemo_2025_Q4/providers/Microsoft.OperationalInsights/workspaces/log-techdemo-rca \
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
  --action-groups /subscriptions/SUBSCRIPTION_ID/resourceGroups/rg_techdemo_2025_Q4/providers/microsoft.insights/actionGroups/rca-webhook-action-group
```

---

## Azure Data Factory Integration

### Enable ADF Monitoring

1. **Enable Diagnostic Logs** (done above in Azure Monitor setup)

2. **Configure Action Group in ADF**:
   - Go to ADF Studio → Monitor → Alerts
   - Create alert rule for pipeline failures
   - Link to action group: `rca-webhook-action-group`

### ADF Payload Structure

When ADF pipeline fails, Azure Monitor sends:

```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertRule": "tech-demo-adf-alert",
      "severity": "Sev3",
      "signalType": "Log"
    },
    "alertContext": {
      "SearchQuery": "ADFPipelineRun | where Status == 'Failed'",
      "SearchResults": {
        "tables": [{
          "rows": [[
            "2025-12-10T20:00:00Z",
            "my-pipeline",
            "run-123-abc",
            "Copy Activity",
            "2200",
            "File not found error"
          ]]
        }]
      }
    }
  }
}
```

---

## Databricks Integration

### Databricks Workspace Setup

1. **Create Personal Access Token**:
   ```bash
   # In Databricks UI:
   # User Settings → Developer → Access Tokens → Generate New Token
   # Name: "RCA System"
   # Lifetime: 365 days
   # Save token: dapi...
   ```

2. **Required Environment Variables**:
   ```bash
   export DATABRICKS_WORKSPACE_URL="https://adb-XXXX.azuredatabricks.net"
   export DATABRICKS_TOKEN="dapi..."
   ```

### Databricks API Endpoints Used

| Endpoint | Purpose | Permission |
|----------|---------|-----------|
| `/api/2.0/clusters/get` | Get cluster details | clusters/get |
| `/api/2.0/clusters/events` | Get cluster events | clusters/events/get |
| `/api/2.1/jobs/runs/get` | Get job run details | jobs/runs/get |
| `/api/2.1/jobs/run-now` | Trigger job retry | jobs/run-now |

### Test Databricks Connection

```python
import requests

headers = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}"
}

response = requests.get(
    f"{DATABRICKS_WORKSPACE_URL}/api/2.0/clusters/list",
    headers=headers
)

print(response.json())
```

---

## Azure Blob Storage Setup

### Create Storage Account & Container

```bash
# Create storage account
az storage account create \
  --name sttechdemorcadev \
  --resource-group rg_techdemo_2025_Q4 \
  --location eastus \
  --sku Standard_LRS

# Create container for audit logs
az storage container create \
  --name audit-logs \
  --account-name sttechdemorcadev \
  --public-access off

# Get connection string
az storage account show-connection-string \
  --name sttechdemorcadev \
  --resource-group rg_techdemo_2025_Q4
```

### Environment Variable

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=sttechdemorcadev;AccountKey=...;EndpointSuffix=core.windows.net"
```

### Blob Storage Structure

```
audit-logs/
├── 2025-12-10/
│   ├── ADF-20251210T120000-abc123-payload.json
│   ├── DBX-20251210T130000-def456-databricks-logs.json
│   └── ARF-20251210T140000-ghi789-airflow-logs.json
├── 2025-12-11/
│   └── ...
```

---

## Logic Apps Setup

### Create Auto-Remediation Logic App

```bash
# Create Logic App
az logic workflow create \
  --resource-group rg_techdemo_2025_Q4 \
  --location eastus \
  --name playbook-retry-databricks-job \
  --definition @logic-apps/playbook-retry-databricks-job.json
```

### Logic App Definition

See `logic-apps/playbook-retry-databricks-job.json` for complete definition.

**Key Parameters:**
- `databricks_workspace_url` - Databricks workspace URL
- `databricks_token` - Databricks PAT (stored as SecureString)

### Test Logic App

```bash
# Trigger Logic App manually
az logic workflow run trigger \
  --resource-group rg_techdemo_2025_Q4 \
  --name playbook-retry-databricks-job \
  --trigger-name "manual" \
  --parameters '{
    "ticket_id": "DBX-TEST-12345",
    "job_id": 123456,
    "callback_url": "https://your-rca-server.com/auto-remediation/callback"
  }'
```

---

## Network & Security Configuration

### Firewall Rules

**If using Azure Firewall or NSG:**

Allow outbound to:
- `*.google.com` (Gemini AI)
- `*.atlassian.net` (JIRA)
- `*.slack.com` (Slack)
- `*.azuredatabricks.net` (Databricks)
- `*.blob.core.windows.net` (Blob Storage)

**Inbound Webhook Ports:**
- Port 8000 (or your configured port) from:
  - Azure Monitor IPs
  - JIRA webhook IPs
  - Airflow server IP

### Webhook Security

**Azure Monitor Webhooks:**
- Use HTTPS only
- Validate common alert schema
- Check `schemaId` field

**JIRA Webhooks:**
- Use webhook secret in URL parameter
- Validate JIRA IP ranges

```python
# Example webhook secret validation
@app.post("/webhook/jira")
async def jira_webhook(request: Request, secret: str):
    if secret != JIRA_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    # Process webhook...
```

---

## Environment Variables Summary

```bash
# Azure
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=..."
export AZURE_BLOB_ENABLED="true"

# Databricks
export DATABRICKS_WORKSPACE_URL="https://adb-XXXX.azuredatabricks.net"
export DATABRICKS_TOKEN="dapi..."

# AI
export GEMINI_API_KEY="your-gemini-api-key"

# JIRA
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-jira-api-token"
export JIRA_PROJECT_KEY="APAIOPS"
export ITSM_TOOL="jira"

# Slack
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_ALERT_CHANNEL="C01234567"

# Logic Apps
export LOGIC_APP_RETRY_DATABRICKS_URL="https://prod-XX.eastus.logic.azure.com/workflows/..."

# Application
export PUBLIC_BASE_URL="https://your-rca-server.com"
```

---

## Verification Checklist

- [ ] Service Principal created with required roles
- [ ] Log Analytics Workspace created
- [ ] Databricks diagnostics enabled
- [ ] ADF diagnostics enabled
- [ ] Action Group created with webhook
- [ ] Alert rules created (Databricks, ADF)
- [ ] Blob Storage account created
- [ ] Blob container `audit-logs` created
- [ ] Databricks PAT generated
- [ ] Logic App deployed
- [ ] All environment variables set
- [ ] Firewall rules configured
- [ ] Webhook endpoints tested

---

**Next:** [03_INSTALLATION.md](03_INSTALLATION.md) - Installation Guide

