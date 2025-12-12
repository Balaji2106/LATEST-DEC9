# API Reference

Complete API endpoint documentation for the AIOps RCA Assistant.

---

## 📋 Table of Contents

1. [Base URL & Authentication](#base-url--authentication)
2. [Webhook Endpoints](#webhook-endpoints)
3. [Ticket Management API](#ticket-management-api)
4. [Dashboard & Export API](#dashboard--export-api)
5. [Authentication API](#authentication-api)
6. [WebSocket API](#websocket-api)
7. [Response Codes](#response-codes)
8. [Error Handling](#error-handling)

---

## Base URL & Authentication

### Base URL

```
http://localhost:8000          # Local development
https://your-domain.com        # Production
```

### Authentication

Most API endpoints use JWT Bearer token authentication (except webhooks).

**Header Format:**
```
Authorization: Bearer <jwt_token>
```

**Obtain Token:**
```bash
# Login to get token
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@sigmoidanalytics.com",
    "password": "your-password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## Webhook Endpoints

Webhook endpoints receive failure notifications from external systems (Azure Monitor, Databricks, Airflow, JIRA).

### 1. Azure Monitor Webhook

**Endpoint:** `POST /azure-monitor`

**Purpose:** Receives Azure Data Factory and general Azure Monitor alerts

**Authentication:** None (webhook from Azure)

**Content-Type:** `application/json`

**Request Body (Azure Common Alert Schema):**
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertRule": "adf-pipeline-failure-alert",
      "severity": "Sev3",
      "signalType": "Log",
      "monitoringService": "Log Analytics",
      "alertTargetIDs": ["/subscriptions/..."]
    },
    "alertContext": {
      "SearchQuery": "ADFPipelineRun | where Status == 'Failed'",
      "SearchResults": {
        "tables": [{
          "name": "PrimaryResult",
          "columns": [...],
          "rows": [[
            "2025-12-12T10:00:00Z",
            "pipeline-name",
            "run-id-12345",
            "Copy Activity",
            "2200",
            "Source blob not found"
          ]]
        }]
      }
    }
  }
}
```

**Response (Success):**
```json
{
  "ticket_id": "ADF-20251212T100000-abc123",
  "status": "created",
  "message": "Ticket created successfully",
  "jira_ticket_id": "APAIOPS-123",
  "slack_notification_sent": true
}
```

**Response (Duplicate):**
```json
{
  "ticket_id": "ADF-20251212T100000-abc123",
  "status": "duplicate",
  "message": "Duplicate run_id detected",
  "existing_ticket": "ADF-20251212T095000-xyz789"
}
```

**Status Codes:**
- `200 OK` - Ticket created successfully
- `200 OK` - Duplicate detected (returns existing ticket)
- `400 Bad Request` - Invalid payload
- `500 Internal Server Error` - Processing failed

**Example:**
```bash
curl -X POST http://localhost:8000/azure-monitor \
  -H "Content-Type: application/json" \
  -d @azure-monitor-payload.json
```

---

### 2. Databricks Monitor Webhook

**Endpoint:** `POST /databricks-monitor`

**Purpose:** Receives Databricks cluster/job failure alerts from Azure Monitor

**Authentication:** None

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "schemaId": "azureMonitorCommonAlertSchema",
  "data": {
    "essentials": {
      "alertRule": "databricks-cluster-failure",
      "severity": "Sev2"
    },
    "alertContext": {
      "SearchQuery": "DatabricksClusters | where clusterState == 'Error'",
      "SearchResults": {
        "tables": [{
          "rows": [[
            "2025-12-12T10:00:00Z",
            "cluster-id-123",
            "production-cluster",
            "Error",
            "CLOUD_PROVIDER_LAUNCH_FAILURE"
          ]]
        }]
      }
    }
  }
}
```

**Additional Processing:**
- Fetches detailed run information from Databricks API
- Extracts cluster events and error context
- Classifies error type (remediable vs non-remediable)
- Uploads logs to Azure Blob Storage (if enabled)

**Response:**
```json
{
  "ticket_id": "DBX-20251212T100000-def456",
  "status": "created",
  "error_type": "DatabricksClusterStartFailure",
  "is_auto_remediable": true,
  "remediation_action": "restart_cluster",
  "jira_ticket_id": "APAIOPS-124",
  "blob_log_url": "https://storage.blob.core.windows.net/audit-logs/2025-12-12/DBX-..."
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/databricks-monitor \
  -H "Content-Type: application/json" \
  -d @databricks-alert.json
```

---

### 3. Airflow Monitor Webhook

**Endpoint:** `POST /airflow-monitor`

**Purpose:** Receives Airflow DAG/task failure callbacks

**Authentication:** None (but should use secret parameter in production)

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "dag_id": "prod_etl_pipeline",
  "task_id": "extract_from_database",
  "execution_date": "2025-12-12T10:00:00",
  "run_id": "manual__2025-12-12T10:00:00",
  "state": "failed",
  "try_number": 1,
  "max_tries": 3,
  "exception": "psycopg2.OperationalError: could not connect to server: Connection refused",
  "log_url": "http://airflow:8080/dags/prod_etl_pipeline/grid?dag_run_id=manual__2025-12-12T10:00:00",
  "operator": "PostgresOperator"
}
```

**Processing:**
- Classifies error using pattern matching (ConnectionError, TimeoutError, etc.)
- Determines if error is auto-remediable
- Generates AI-powered RCA specific to Airflow context
- Creates JIRA ticket and sends Slack notification

**Response:**
```json
{
  "ticket_id": "ARF-20251212T100000-ghi789",
  "status": "created",
  "error_classification": {
    "error_type": "ConnectionError",
    "category": "NetworkError",
    "severity": "Medium",
    "is_remediable": true,
    "action": "retry_task",
    "max_retries": 3
  },
  "jira_ticket_id": "APAIOPS-125"
}
```

**Airflow DAG Integration Example:**
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests

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
    }
    requests.post(
        "http://rca-server:8000/airflow-monitor",
        json=payload,
        timeout=10
    )

with DAG('my_dag', on_failure_callback=airflow_failure_callback) as dag:
    task = PythonOperator(...)
```

---

### 4. JIRA Webhook

**Endpoint:** `POST /jira-webhook`

**Purpose:** Receives JIRA status update events (bidirectional sync)

**Authentication:** Webhook secret (query parameter)

**Content-Type:** `application/json`

**URL Format:**
```
POST /jira-webhook?secret=your-webhook-secret
```

**Request Body (JIRA Webhook):**
```json
{
  "timestamp": 1702380000000,
  "webhookEvent": "jira:issue_updated",
  "issue_event_type_name": "issue_generic",
  "issue": {
    "key": "APAIOPS-123",
    "fields": {
      "status": {
        "name": "Done",
        "statusCategory": {
          "key": "done"
        }
      },
      "summary": "ADF Pipeline Failure: pipeline-name",
      "description": "..."
    }
  },
  "user": {
    "displayName": "John Doe",
    "emailAddress": "john.doe@company.com"
  },
  "changelog": {
    "items": [{
      "field": "status",
      "fromString": "In Progress",
      "toString": "Done"
    }]
  }
}
```

**Processing:**
- Validates webhook secret
- Maps JIRA status to RCA status (Done → acknowledged, In Progress → in_progress)
- Updates local ticket status
- Updates Slack message
- Broadcasts WebSocket event to dashboard

**Status Mapping:**
| JIRA Status | RCA Status | Ticket State |
|-------------|------------|--------------|
| Done, Closed | acknowledged | Ticket closed |
| In Progress | in_progress | Work in progress |
| To Do, Open | open | Ticket open |
| Reopened | in_progress | Ticket reopened |

**Response:**
```json
{
  "status": "success",
  "ticket_id": "ADF-20251212T100000-abc123",
  "new_status": "acknowledged",
  "updated_at": "2025-12-12T10:30:00Z"
}
```

**Setup JIRA Webhook:**
1. Go to JIRA → Settings → System → WebHooks
2. Create webhook
3. URL: `https://your-rca-server.com/jira-webhook?secret=your-secret`
4. Events: Issue Updated
5. JQL: `project = APAIOPS`

---

### 5. Auto-Remediation Callback

**Endpoint:** `POST /api/remediation-callback`

**Purpose:** Receives callbacks from Logic Apps after remediation attempts

**Authentication:** None (internal callback)

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "ticket_id": "ADF-20251212T100000-abc123",
  "original_run_id": "run-id-12345",
  "remediation_run_id": "run-id-67890",
  "status": "succeeded",
  "pipeline_name": "pipeline-name",
  "error_type": "GatewayTimeout",
  "started_at": "2025-12-12T10:05:00Z",
  "completed_at": "2025-12-12T10:10:00Z",
  "attempt_number": 1
}
```

**Status Options:**
- `succeeded` - Remediation successful, ticket closed
- `failed` - Remediation failed, retry or escalate
- `in_progress` - Still running
- `timeout` - Monitoring timeout reached

**Response (Success):**
```json
{
  "status": "ticket_closed",
  "ticket_id": "ADF-20251212T100000-abc123",
  "mttr_minutes": 5.2,
  "jira_updated": true,
  "slack_updated": true
}
```

**Response (Failed - Retry):**
```json
{
  "status": "retrying",
  "ticket_id": "ADF-20251212T100000-abc123",
  "attempt_number": 2,
  "max_retries": 3,
  "next_retry_in_seconds": 60
}
```

**Response (Failed - Exhausted):**
```json
{
  "status": "escalated",
  "ticket_id": "ADF-20251212T100000-abc123",
  "attempts": 3,
  "remediation_status": "applied_not_solved",
  "message": "All retry attempts exhausted, manual intervention required"
}
```

---

## Ticket Management API

### 1. Get Ticket by ID

**Endpoint:** `GET /api/tickets/{ticket_id}`

**Authentication:** Required (JWT Bearer token)

**Parameters:**
- `ticket_id` (path) - Ticket ID (e.g., ADF-20251212T100000-abc123)

**Response:**
```json
{
  "id": "ADF-20251212T100000-abc123",
  "timestamp": "2025-12-12T10:00:00Z",
  "pipeline": "pipeline-name",
  "run_id": "run-id-12345",
  "rca_result": "The pipeline failed because the source blob file was not found...",
  "recommendations": "[\"Check upstream data availability\", \"Verify file path configuration\"]",
  "confidence": "High",
  "severity": "Medium",
  "priority": "P3",
  "error_type": "UserErrorSourceBlobNotExists",
  "affected_entity": "{\"pipeline\": \"pipeline-name\", \"activity\": \"Copy Activity\"}",
  "status": "open",
  "sla_seconds": 7200,
  "sla_status": "Pending",
  "finops_team": "DataEngineering",
  "finops_owner": "dataengineering@company.com",
  "finops_cost_center": "CC-DATA-001",
  "blob_log_url": "https://storage.blob.core.windows.net/...",
  "itsm_ticket_id": "APAIOPS-123",
  "ack_ts": null,
  "ack_user": null,
  "ack_seconds": null,
  "slack_ts": "1702380000.123456",
  "slack_channel": "C01234567",
  "processing_mode": "adf",
  "remediation_status": null,
  "remediation_attempts": 0
}
```

**Status Codes:**
- `200 OK` - Ticket found
- `404 Not Found` - Ticket not found
- `401 Unauthorized` - Invalid or missing token

**Example:**
```bash
curl -X GET http://localhost:8000/api/tickets/ADF-20251212T100000-abc123 \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### 2. Get Open Tickets

**Endpoint:** `GET /api/open-tickets`

**Authentication:** Required

**Parameters:** None

**Response:**
```json
[
  {
    "id": "ADF-20251212T100000-abc123",
    "timestamp": "2025-12-12T10:00:00Z",
    "pipeline": "pipeline-name",
    "severity": "Medium",
    "status": "open",
    "itsm_ticket_id": "APAIOPS-123",
    "sla_status": "Pending"
  },
  ...
]
```

**Example:**
```bash
curl -X GET http://localhost:8000/api/open-tickets \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### 3. Get In-Progress Tickets

**Endpoint:** `GET /api/in-progress-tickets`

**Authentication:** Required

**Response:** Same format as open tickets

**Example:**
```bash
curl -X GET http://localhost:8000/api/in-progress-tickets \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### 4. Get Closed Tickets

**Endpoint:** `GET /api/closed-tickets`

**Authentication:** Required

**Response:** Same format as open tickets

**Example:**
```bash
curl -X GET http://localhost:8000/api/closed-tickets \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### 5. Get Remediation Failed Tickets

**Endpoint:** `GET /api/remediation-failed-tickets`

**Authentication:** Required

**Purpose:** Get tickets where auto-remediation was attempted but failed

**Response:**
```json
[
  {
    "id": "ADF-20251212T100000-abc123",
    "remediation_status": "applied_not_solved",
    "remediation_attempts": 3,
    "status": "in_progress"
  },
  ...
]
```

---

### 6. Get Summary Statistics

**Endpoint:** `GET /api/summary`

**Authentication:** Required

**Response:**
```json
{
  "open": 5,
  "in_progress": 3,
  "closed": 42,
  "total": 50,
  "remediation_successful": 8,
  "remediation_failed": 2,
  "avg_mttr_minutes": 15.5,
  "sla_met_percentage": 92.5
}
```

**Example:**
```bash
curl -X GET http://localhost:8000/api/summary \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## Dashboard & Export API

### 1. Dashboard Page

**Endpoint:** `GET /dashboard`

**Authentication:** Required (redirects to /login if not authenticated)

**Response:** HTML page (dashboard.html)

**Example:**
```bash
# Access in browser
http://localhost:8000/dashboard
```

---

### 2. Audit Trail

**Endpoint:** `GET /api/audit-trail`

**Authentication:** Required

**Query Parameters:**
- `ticket_id` (optional) - Filter by specific ticket
- `limit` (optional) - Number of records (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2025-12-12T10:00:00Z",
    "ticket_id": "ADF-20251212T100000-abc123",
    "action": "Ticket Created",
    "user_name": "System",
    "pipeline": "pipeline-name",
    "run_id": "run-id-12345",
    "sla_status": "Pending",
    "itsm_ticket_id": "APAIOPS-123",
    "details": "Ticket created from Azure Monitor alert"
  },
  ...
]
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/audit-trail?ticket_id=ADF-20251212T100000-abc123" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### 3. Export Open Tickets (CSV)

**Endpoint:** `GET /api/export/open-tickets`

**Authentication:** Required

**Response:** CSV file download

**Headers:**
```
Content-Type: text/csv
Content-Disposition: attachment; filename=open_tickets.csv
```

**CSV Format:**
```csv
ID,Timestamp,Pipeline,Run ID,Severity,Priority,Status,SLA Status,JIRA Ticket
ADF-20251212T100000-abc123,2025-12-12T10:00:00Z,pipeline-name,run-id-12345,Medium,P3,open,Pending,APAIOPS-123
```

**Example:**
```bash
curl -X GET http://localhost:8000/api/export/open-tickets \
  -H "Authorization: Bearer ${TOKEN}" \
  -o open_tickets.csv
```

---

### 4. Export Closed Tickets (CSV)

**Endpoint:** `GET /api/export/closed-tickets`

**Similar to open tickets export**

---

### 5. Export Audit Trail (CSV)

**Endpoint:** `GET /api/export/audit-trail`

**Response:** CSV with audit trail data

---

## Authentication API

### 1. Register User

**Endpoint:** `POST /api/register`

**Authentication:** None

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "email": "user@sigmoidanalytics.com",
  "password": "SecurePassword123",
  "full_name": "John Doe"
}
```

**Validation Rules:**
- Email must end with `@sigmoidanalytics.com`
- Password must be at least 8 characters

**Response (Success):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response (Error):**
```json
{
  "detail": "Email must be from @sigmoidanalytics.com domain"
}
```

**Status Codes:**
- `200 OK` - User registered successfully
- `400 Bad Request` - Validation failed
- `409 Conflict` - Email already exists

---

### 2. Login

**Endpoint:** `POST /api/login`

**Authentication:** None

**Request Body:**
```json
{
  "email": "user@sigmoidanalytics.com",
  "password": "SecurePassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Status Codes:**
- `200 OK` - Login successful
- `401 Unauthorized` - Invalid credentials

---

### 3. Get Current User

**Endpoint:** `GET /api/me`

**Authentication:** Required

**Response:**
```json
{
  "id": 1,
  "email": "user@sigmoidanalytics.com",
  "full_name": "John Doe",
  "created_at": "2025-12-01T08:00:00Z",
  "last_login": "2025-12-12T09:00:00Z"
}
```

---

## WebSocket API

### WebSocket Connection

**Endpoint:** `WS /ws`

**Purpose:** Real-time dashboard updates

**Authentication:** None (should be added for production)

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('Connected to RCA WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);

  // Handle different event types
  switch(data.event) {
    case 'new_ticket':
      // New ticket created
      break;
    case 'status_update':
      // Ticket status changed
      break;
    case 'jira_sync':
      // JIRA status synced
      break;
  }
};

ws.onclose = () => {
  console.log('Disconnected from RCA WebSocket');
};
```

**Server Events:**

1. **new_ticket** - New ticket created
```json
{
  "event": "new_ticket",
  "ticket": {
    "id": "ADF-20251212T100000-abc123",
    "pipeline": "pipeline-name",
    "severity": "Medium",
    "status": "open"
  }
}
```

2. **status_update** - Ticket status changed
```json
{
  "event": "status_update",
  "ticket_id": "ADF-20251212T100000-abc123",
  "new_status": "acknowledged",
  "updated_by": "john.doe@company.com"
}
```

3. **jira_sync** - JIRA status synced
```json
{
  "event": "jira_sync",
  "ticket_id": "ADF-20251212T100000-abc123",
  "jira_ticket_id": "APAIOPS-123",
  "jira_status": "Done",
  "rca_status": "acknowledged"
}
```

---

## Response Codes

| Status Code | Meaning | Usage |
|-------------|---------|-------|
| **200 OK** | Success | Successful request |
| **201 Created** | Resource created | User registered |
| **400 Bad Request** | Invalid request | Malformed JSON, validation errors |
| **401 Unauthorized** | Authentication failed | Invalid/missing token |
| **403 Forbidden** | Access denied | Invalid webhook secret |
| **404 Not Found** | Resource not found | Ticket ID doesn't exist |
| **409 Conflict** | Resource conflict | Duplicate email registration |
| **500 Internal Server Error** | Server error | Unexpected error |

---

## Error Handling

### Error Response Format

All errors return JSON with `detail` field:

```json
{
  "detail": "Error description here"
}
```

### Common Errors

**Invalid Token:**
```json
{
  "detail": "Invalid or expired token"
}
```

**Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Email must be from @sigmoidanalytics.com domain",
      "type": "value_error"
    }
  ]
}
```

**Ticket Not Found:**
```json
{
  "detail": "Ticket not found"
}
```

---

## Rate Limiting

Currently no rate limiting implemented. Recommended for production:

- Webhooks: 100 requests/minute per IP
- API endpoints: 1000 requests/hour per user
- WebSocket: 50 connections per IP

---

**Next:** [06_INTEGRATIONS.md](06_INTEGRATIONS.md) - Integration Setup Guide
