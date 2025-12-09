# Logic Apps Deployment Guide

## Overview

These Logic Apps implement the callback-based monitoring architecture for auto-remediation. Instead of the RCA app polling Azure/Databricks APIs, the Logic Apps monitor pipeline/job execution and callback to the RCA app when complete.

## Architecture

```
1. RCA App triggers Logic App via HTTP POST
   ↓
2. Logic App retries pipeline/job
   ↓
3. Logic App monitors using "Until" loop (every 30s)
   ↓
4. When complete, Logic App calls back to RCA app
   ↓
5. RCA app handles success/failure/retry logic
```

## Benefits

- ✅ No Azure credentials needed in RCA app
- ✅ Event-driven (no polling overhead)
- ✅ Built-in retry and timeout handling
- ✅ Centralized monitoring in Logic Apps
- ✅ Prevents race conditions

---

## Important: Request Schema Requirements

### URI Format for Databricks Workflows

When calling the Databricks retry Logic App, the `databricks_workspace_url` field must be provided **WITHOUT** the `https://` protocol prefix. The Logic App automatically prepends `https://` to construct the full URI.

**Correct format:**
```json
{
  "databricks_workspace_url": "adb-1234567890123456.7.azuredatabricks.net",
  "callback_url": "https://your-rca-app.com/api/remediation-callback"
}
```

**Incorrect format (will fail):**
```json
{
  "databricks_workspace_url": "https://adb-1234567890123456.7.azuredatabricks.net",  // ❌ Don't include https://
  "callback_url": "https://your-rca-app.com/api/remediation-callback"
}
```

Note: The `callback_url` field should include the full URL with protocol.

---

## Deployment Instructions

### 1. Azure Data Factory Logic App

**File**: `playbook-retry-adf-pipeline-with-callback.json`

#### Prerequisites
- Azure subscription with ADF instance
- Logic Apps enabled in same subscription

#### Steps

1. **Create Logic App in Azure Portal**
   - Go to Azure Portal → Create Resource → Logic App
   - Name: `playbook-retry-adf-pipeline`
   - Resource Group: Same as your ADF
   - Region: Same as your ADF
   - Click "Create"

2. **Configure ADF Connection**
   - Open Logic App → API Connections
   - Add new connection: Azure Data Factory
   - Authenticate using Managed Identity or Service Principal
   - Grant permissions: Data Factory Contributor

3. **Import Workflow**
   - Open Logic App → Logic App Designer
   - Click "Code View"
   - Replace entire JSON with contents of `playbook-retry-adf-pipeline-with-callback.json`
   - **IMPORTANT**: Replace placeholders:
     - `<SUBSCRIPTION_ID>` → Your Azure subscription ID
     - `<RESOURCE_GROUP>` → Your ADF resource group name
     - `<DATA_FACTORY_NAME>` → Your ADF instance name
     - `<LOCATION>` → Azure region (e.g., "eastus")

4. **Get Logic App Trigger URL**
   - Save the Logic App
   - Go to "Overview" → "Trigger history"
   - Copy the "HTTP POST URL"
   - **Set environment variable in RCA app**:
     ```bash
     export LOGIC_APP_WEBHOOK_URL="<YOUR_LOGIC_APP_URL>"
     ```

5. **Test the Logic App**
   - Use Postman or curl to test:
     ```bash
     curl -X POST "<YOUR_LOGIC_APP_URL>" \
       -H "Content-Type: application/json" \
       -d '{
         "pipeline_name": "your-pipeline-name",
         "ticket_id": "test-123",
         "callback_url": "http://your-rca-app.com/api/remediation-callback",
         "retry_attempt": 1,
         "max_retries": 3,
         "error_type": "TestError",
         "original_run_id": "test-run-id",
         "remediation_action": "retry_pipeline",
         "timestamp": "2025-12-05T10:00:00Z"
       }'
     ```

---

### 2. Databricks Logic App

**File**: `databricks-auto-remediation-with-callback.json`

#### Prerequisites
- Databricks workspace
- Databricks Personal Access Token (PAT)

#### Steps

1. **Create Logic App in Azure Portal**
   - Name: `databricks-auto-remediation`
   - Resource Group: Same as your Databricks workspace
   - Region: Same as your Databricks workspace

2. **Import Workflow**
   - Open Logic App → Logic App Designer → Code View
   - Replace entire JSON with contents of `databricks-auto-remediation-with-callback.json`
   - **IMPORTANT**: Replace placeholders:
     - `<DATABRICKS_WORKSPACE>` → Your Databricks workspace URL (e.g., "adb-1234567890123456.7.azuredatabricks.net")
     - `<DATABRICKS_TOKEN>` → Your Databricks PAT token

3. **Secure the Token**
   - Don't hardcode token in JSON!
   - Use Azure Key Vault:
     - Store token in Key Vault
     - Grant Logic App managed identity access to Key Vault
     - Update Logic App to fetch token from Key Vault:
       ```json
       "@body('Get_Secret_From_KeyVault')?['value']"
       ```

4. **Get Logic App Trigger URL**
   - Copy the HTTP POST URL
   - **Set environment variable in RCA app**:
     ```bash
     export DATABRICKS_LOGIC_APP_URL="<YOUR_LOGIC_APP_URL>"
     ```

5. **Test the Logic App**
   ```bash
   curl -X POST "<YOUR_LOGIC_APP_URL>" \
     -H "Content-Type: application/json" \
     -d '{
       "job_name": "your-job-name",
       "job_id": "123456",
       "cluster_id": "your-cluster-id",
       "ticket_id": "test-456",
       "callback_url": "http://your-rca-app.com/api/remediation-callback",
       "retry_attempt": 1,
       "max_retries": 3,
       "error_type": "ClusterError",
       "original_run_id": "test-run-id",
       "remediation_action": "retry_job",
       "timestamp": "2025-12-05T10:00:00Z"
     }'
   ```

---

## Environment Variables Required

Add these to your RCA app's `.env` file:

```bash
# Logic Apps endpoints
LOGIC_APP_WEBHOOK_URL=https://prod-xx.region.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke?...
DATABRICKS_LOGIC_APP_URL=https://prod-yy.region.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke?...

# Public URL for callbacks (must be accessible from Azure)
PUBLIC_BASE_URL=https://your-rca-app.com
```

**IMPORTANT**: The `PUBLIC_BASE_URL` must be publicly accessible so Logic Apps can callback to it. Options:
- Deploy RCA app to Azure App Service
- Use ngrok for local testing: `ngrok http 8000`
- Use Azure API Management as proxy

---

## Monitoring and Troubleshooting

### View Logic App Runs
- Azure Portal → Logic App → "Run history"
- Click on a run to see detailed execution steps
- Check for failed actions

### Common Issues

1. **Logic App can't reach callback URL**
   - Ensure `PUBLIC_BASE_URL` is publicly accessible
   - Check firewall rules
   - Use ngrok for local testing

2. **ADF connection fails**
   - Verify Managed Identity has "Data Factory Contributor" role
   - Check subscription/resource group/factory names

3. **Databricks API returns 403**
   - Token expired - regenerate PAT
   - Token doesn't have permissions - recreate with "workspace" scope

4. **Pipeline times out**
   - Increase "Until" loop timeout: change `"timeout": "PT1H"` to `"PT2H"`
   - Increase count: change `"count": 60` to `"count": 120`

### Enable Diagnostic Logging
```bash
# Azure CLI - Enable diagnostics for Logic App
az monitor diagnostic-settings create \
  --resource <LOGIC_APP_RESOURCE_ID> \
  --name LogicAppDiagnostics \
  --workspace <LOG_ANALYTICS_WORKSPACE_ID> \
  --logs '[{"category": "WorkflowRuntime", "enabled": true}]'
```

---

## Testing the Complete Flow

1. **Trigger a pipeline failure** in ADF/Databricks
2. **Azure Monitor sends webhook** to RCA app at `/api/webhook/azure-monitor`
3. **RCA app creates ticket** and triggers Logic App
4. **Logic App retries pipeline** and monitors until complete
5. **Logic App callbacks** to RCA app at `/api/remediation-callback`
6. **RCA app handles result**:
   - Success → Close ticket
   - Failure → Retry (up to max_retries) or mark as "remediation applied not solved"

---

## Upgrading from Old Architecture

If you're currently using polling-based monitoring:

1. **Deploy both Logic Apps** following steps above
2. **Set environment variables** (LOGIC_APP_WEBHOOK_URL, etc.)
3. **Restart RCA app** to pick up new Logic App endpoints
4. **Remove old polling code** (already removed in main.py)
5. **Test with a sample failure**

The RCA app will automatically use the new callback-based architecture.

---

## Security Best Practices

1. **Use Managed Identity** for ADF connections (no credentials in Logic App)
2. **Store Databricks token in Key Vault** (don't hardcode)
3. **Enable authentication** on callback endpoint (optional - requires OAuth setup)
4. **Restrict Logic App trigger URL** using IP whitelisting
5. **Use HTTPS** for all endpoints (PUBLIC_BASE_URL must be https://)

---

## Cost Optimization

- Logic Apps charge per action execution
- "Until" loop with 30s delay = ~2 actions/minute
- For 1-hour pipeline: ~120 actions = $0.012 (very cheap)
- Monitor monthly costs in Azure Cost Management

---

## Support

If you encounter issues:
1. Check Logic App run history in Azure Portal
2. Check RCA app logs for callback errors
3. Verify environment variables are set correctly
4. Test Logic App manually using curl/Postman
