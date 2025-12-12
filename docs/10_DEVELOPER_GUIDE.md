# Developer Guide

Guide for developers extending and customizing the AIOps RCA Assistant.

---

## 📋 Table of Contents

1. [Development Setup](#development-setup)
2. [Code Structure](#code-structure)
3. [Adding New Error Types](#adding-new-error-types)
4. [Creating Custom Integrations](#creating-custom-integrations)
5. [Extending Auto-Remediation](#extending-auto-remediation)
6. [Adding New API Endpoints](#adding-new-api-endpoints)
7. [Testing](#testing)
8. [Contributing Guidelines](#contributing-guidelines)

---

## Development Setup

### Prerequisites

- Python 3.12+
- Git
- VS Code or PyCharm (recommended)
- Docker (optional, for containerized development)

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Balaji2106/LATEST-DEC9.git
cd LATEST-DEC9/genai_rca_assistant

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio black flake8 mypy

# Create .env file for development
cp .env.example .env
# Edit .env with your development credentials
```

### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "ms-python.flake8",
    "charliermarsh.ruff",
    "njpwerner.autodocstring"
  ]
}
```

---

## Code Structure

### File Organization

```
genai_rca_assistant/
├── main.py                      # Main FastAPI application
├── cluster_failure_detector.py  # Databricks error classification
├── airflow_integration.py       # Airflow error classification
├── databricks_api_utils.py      # Databricks API utilities
├── error_extractors.py          # Error extraction utilities
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── data/                        # SQLite database directory
├── dashboard.html               # Dashboard UI
└── login.html                   # Login page
```

### main.py Structure

```python
# Lines 1-500: Imports, configuration, database setup
# Lines 500-1000: Helper functions (audit, blob storage, FinOps tags)
# Lines 1000-1400: AI RCA generation (Gemini, Ollama, fallback)
# Lines 1400-2000: Auto-remediation logic
# Lines 2000-2500: FastAPI app initialization, authentication
# Lines 2500-3000: Webhook endpoints (Azure Monitor, Databricks)
# Lines 3000-3500: Airflow webhook endpoint
# Lines 3500-4000: JIRA webhook, bidirectional sync
# Lines 4000-4500: Dashboard API endpoints
# Lines 4500+: WebSocket, export endpoints
```

### Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `init_db()` | main.py:227 | Initialize database schema |
| `generate_rca_and_recs()` | main.py:990 | Generate AI-powered RCA |
| `create_jira_ticket()` | main.py:1050 | Create JIRA ticket |
| `post_slack_notification()` | main.py:1217 | Send Slack notification |
| `classify_airflow_error()` | airflow_integration.py:119 | Classify Airflow errors |
| `is_cluster_related_error()` | cluster_failure_detector.py:150 | Detect Databricks cluster errors |

---

## Adding New Error Types

### Step 1: Define Error Classification

**File:** Create new file or edit existing classifier (e.g., `cluster_failure_detector.py`)

```python
# Example: Add new ADF error type
ADF_ERROR_PATTERNS = {
    "CustomDataValidationError": {
        "action": "check_data_quality",
        "max_retries": 0,  # Not auto-remediable
        "category": "DataError",
        "severity": "High",
        "typical_cause": "Data failed custom validation rules",
        "keywords": [
            "validation.*failed",
            "data.*quality.*check",
            "invalid.*data.*format"
        ]
    }
}
```

### Step 2: Update AI Prompt

**File:** `main.py` (function `call_ai_for_rca`)

```python
# Add new error type to the list
error_types = """[UserErrorSourceBlobNotExists, UserErrorColumnNameInvalid, GatewayTimeout,
CustomDataValidationError,  # ← Add new error type
HttpConnectionFailed, InternalServerError, ...]"""
```

### Step 3: Test New Error Type

```python
# Test classification
def test_new_error():
    error_msg = "Data validation failed: Invalid date format in column 'transaction_date'"
    result = classify_error(error_msg)
    assert result['error_type'] == 'CustomDataValidationError'
    assert result['is_remediable'] == False
```

---

## Creating Custom Integrations

### Example: Add ServiceNow Integration

**Step 1: Create Integration Module**

**File:** `servicenow_integration.py`

```python
import os
import requests
from typing import Optional

SERVICENOW_INSTANCE = os.getenv("SERVICENOW_INSTANCE", "")
SERVICENOW_USERNAME = os.getenv("SERVICENOW_USERNAME", "")
SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD", "")

def create_servicenow_incident(ticket_id: str, summary: str, description: str,
                                 priority: str, urgency: str) -> Optional[str]:
    """Create incident in ServiceNow"""
    if not all([SERVICENOW_INSTANCE, SERVICENOW_USERNAME, SERVICENOW_PASSWORD]):
        return None

    url = f"https://{SERVICENOW_INSTANCE}.service-now.com/api/now/table/incident"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "short_description": summary,
        "description": description,
        "priority": map_priority(priority),
        "urgency": map_urgency(urgency),
        "category": "Data Pipeline",
        "subcategory": "ADF Failure"
    }

    try:
        response = requests.post(
            url,
            auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 201:
            incident_number = response.json()['result']['number']
            return incident_number
        else:
            print(f"Failed to create ServiceNow incident: {response.text}")
            return None
    except Exception as e:
        print(f"Exception creating ServiceNow incident: {e}")
        return None

def map_priority(rca_priority: str) -> str:
    """Map RCA priority to ServiceNow priority"""
    mapping = {"P1": "1", "P2": "2", "P3": "3", "P4": "4"}
    return mapping.get(rca_priority, "3")

def map_urgency(rca_severity: str) -> str:
    """Map RCA severity to ServiceNow urgency"""
    mapping = {"Critical": "1", "High": "2", "Medium": "3", "Low": "3"}
    return mapping.get(rca_severity, "3")
```

**Step 2: Integrate into main.py**

```python
# In main.py, import the integration
from servicenow_integration import create_servicenow_incident

# In webhook endpoint (e.g., azure-monitor)
# After ticket creation
if ITSM_TOOL == "servicenow":
    snow_incident = create_servicenow_incident(
        ticket_id=ticket_id,
        summary=f"ADF Pipeline Failure: {pipeline_name}",
        description=rca_result,
        priority=priority,
        urgency=severity
    )
    if snow_incident:
        db_execute("UPDATE tickets SET itsm_ticket_id = :id WHERE id = :tid",
                   {"id": snow_incident, "tid": ticket_id})
```

**Step 3: Add Configuration**

```bash
# .env
ITSM_TOOL=servicenow
SERVICENOW_INSTANCE=your-instance
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

---

## Extending Auto-Remediation

### Example: Add Email Notification Remediation

**Step 1: Create Logic App**

Create Azure Logic App with HTTP trigger that sends email notification.

**Step 2: Add to Configuration**

```bash
# .env
PLAYBOOK_EMAIL_NOTIFICATION=https://prod-xx.eastus.logic.azure.com/workflows/.../triggers/manual/paths/invoke?...
```

**Step 3: Update Remediation Actions**

**File:** `main.py`

```python
# Add to REMEDIATION_ACTION_PLAYBOOKS
REMEDIATION_ACTION_PLAYBOOKS: Dict[str, str] = {
    # Existing actions
    "retry_pipeline": os.getenv("PLAYBOOK_RETRY_PIPELINE"),
    "retry_job": os.getenv("PLAYBOOK_RETRY_JOB"),

    # New action
    "email_notification": os.getenv("PLAYBOOK_EMAIL_NOTIFICATION"),
}
```

**Step 4: Trigger Email Notification**

```python
async def trigger_email_notification(ticket_id: str, recipients: list, error_summary: str):
    """Send email notification for critical failures"""
    playbook_url = REMEDIATION_ACTION_PLAYBOOKS.get("email_notification")

    if not playbook_url:
        logger.warning("Email notification playbook not configured")
        return None

    payload = {
        "ticket_id": ticket_id,
        "recipients": recipients,
        "subject": f"Critical Pipeline Failure: {ticket_id}",
        "body": error_summary
    }

    try:
        response = requests.post(playbook_url, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info(f"Email notification sent for {ticket_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return None
```

---

## Adding New API Endpoints

### Example: Add Endpoint to Get Tickets by Team

**File:** `main.py`

```python
@app.get("/api/tickets/by-team/{team_name}")
async def get_tickets_by_team(team_name: str, current_user: dict = Depends(get_current_user)):
    """Get all tickets for a specific FinOps team"""
    tickets = db_query(
        "SELECT * FROM tickets WHERE finops_team = :team ORDER BY timestamp DESC",
        {"team": team_name}
    )

    if not tickets:
        raise HTTPException(status_code=404, detail=f"No tickets found for team {team_name}")

    return tickets

@app.get("/api/teams/summary")
async def get_teams_summary(current_user: dict = Depends(get_current_user)):
    """Get ticket counts grouped by FinOps team"""
    summary = db_query("""
        SELECT
            finops_team,
            COUNT(*) as total_tickets,
            SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_tickets,
            SUM(CASE WHEN status='acknowledged' THEN 1 ELSE 0 END) as closed_tickets,
            AVG(ack_seconds) as avg_mttr_seconds
        FROM tickets
        WHERE finops_team IS NOT NULL
        GROUP BY finops_team
        ORDER BY total_tickets DESC
    """)

    return summary
```

### Test New Endpoint

```bash
# Get tickets by team
curl -X GET http://localhost:8000/api/tickets/by-team/DataEngineering \
  -H "Authorization: Bearer ${TOKEN}"

# Get teams summary
curl -X GET http://localhost:8000/api/teams/summary \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## Testing

### Unit Tests

**File:** `tests/test_error_classification.py`

```python
import pytest
from airflow_integration import classify_airflow_error

def test_connection_error_classification():
    error_msg = "psycopg2.OperationalError: could not connect to server: Connection refused"
    result = classify_airflow_error(error_msg)

    assert result is not None
    assert result['error_type'] == 'ConnectionError'
    assert result['category'] == 'NetworkError'
    assert result['is_remediable'] == True
    assert result['max_retries'] == 3

def test_timeout_error_classification():
    error_msg = "Task execution timeout after 300 seconds"
    result = classify_airflow_error(error_msg)

    assert result is not None
    assert result['error_type'] == 'TimeoutError'
    assert result['is_remediable'] == True

def test_unknown_error():
    error_msg = "Some random custom error message"
    result = classify_airflow_error(error_msg)

    assert result is None

# Run tests
# pytest tests/test_error_classification.py -v
```

### Integration Tests

**File:** `tests/test_webhook_endpoints.py`

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_azure_monitor_webhook():
    payload = {
        "schemaId": "azureMonitorCommonAlertSchema",
        "data": {
            "essentials": {
                "alertRule": "test-pipeline-alert",
                "severity": "Sev3"
            },
            "alertContext": {
                "SearchResults": {
                    "tables": [{
                        "rows": [[
                            "2025-12-12T10:00:00Z",
                            "test-pipeline",
                            "test-run-12345",
                            "Copy Activity",
                            "2200",
                            "Test failure"
                        ]]
                    }]
                }
            }
        }
    }

    response = client.post("/azure-monitor", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "ticket_id" in data
    assert data["status"] in ["created", "duplicate"]

def test_api_summary_requires_auth():
    response = client.get("/api/summary")
    assert response.status_code == 401  # Unauthorized

# Run tests
# pytest tests/test_webhook_endpoints.py -v
```

### Load Testing

**File:** `tests/load_test.py`

```python
import asyncio
import aiohttp
import time

async def send_webhook(session, payload_id):
    """Send single webhook request"""
    url = "http://localhost:8000/azure-monitor"
    payload = {
        "schemaId": "azureMonitorCommonAlertSchema",
        "data": {
            "essentials": {"alertRule": f"test-{payload_id}", "severity": "Sev3"},
            "alertContext": {
                "SearchResults": {
                    "tables": [{"rows": [[
                        "2025-12-12T10:00:00Z",
                        f"test-pipeline-{payload_id}",
                        f"run-{payload_id}",
                        "Test Activity",
                        "2200",
                        "Load test"
                    ]]}]
                }
            }
        }
    }

    async with session.post(url, json=payload) as response:
        return await response.json()

async def load_test(num_requests=100, concurrency=10):
    """Run load test with specified number of requests and concurrency"""
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(num_requests):
            tasks.append(send_webhook(session, i))
            if len(tasks) >= concurrency:
                await asyncio.gather(*tasks)
                tasks = []

        if tasks:
            await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    print(f"Completed {num_requests} requests in {elapsed:.2f}s")
    print(f"Throughput: {num_requests/elapsed:.2f} requests/second")

# Run: python tests/load_test.py
if __name__ == "__main__":
    asyncio.run(load_test(num_requests=100, concurrency=10))
```

---

## Contributing Guidelines

### Code Style

```bash
# Format code with Black
black genai_rca_assistant/*.py

# Lint with flake8
flake8 genai_rca_assistant/ --max-line-length=120

# Type checking with mypy
mypy genai_rca_assistant/main.py
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/add-servicenow-integration

# Make changes
# ...

# Commit with descriptive message
git add .
git commit -m "feat: Add ServiceNow integration for ITSM ticketing

- Added servicenow_integration.py module
- Integrated with main.py webhook endpoints
- Added configuration options to .env
- Updated documentation"

# Push to remote
git push origin feature/add-servicenow-integration

# Create pull request on GitHub
```

### Commit Message Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semi-colons, etc.
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(integrations): Add Microsoft Teams notification support

fix(databricks): Handle missing cluster_id in API response

docs(api): Update API reference with new endpoints

refactor(auth): Simplify JWT token validation logic
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

---

## Best Practices

### Error Handling

```python
# ✅ Good - Specific exception handling with logging
try:
    result = api_call()
except requests.exceptions.Timeout as e:
    logger.error(f"API timeout: {e}", exc_info=True)
    return fallback_value
except requests.exceptions.ConnectionError as e:
    logger.error(f"Connection error: {e}", exc_info=True)
    return fallback_value

# ❌ Bad - Silent failure
try:
    result = api_call()
except:
    pass
```

### Logging

```python
# ✅ Good - Structured logging with context
logger.info(f"Creating JIRA ticket for {ticket_id}, pipeline: {pipeline_name}")
logger.error(f"JIRA API error: {response.status_code} {response.text}", exc_info=True)

# ❌ Bad - Generic logging
logger.info("Creating ticket")
logger.error("Error occurred")
```

### Configuration

```python
# ✅ Good - Use environment variables with defaults
TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", "30"))

# ❌ Bad - Hardcoded values
TIMEOUT_SECONDS = 30
```

---

**Documentation Complete!**

All 10 comprehensive documentation files have been created covering:
1. Project Overview
2. Architecture
3. Azure Setup
4. Installation
5. Configuration
6. API Reference
7. Integrations
8. Deployment
9. Troubleshooting
10. Developer Guide
