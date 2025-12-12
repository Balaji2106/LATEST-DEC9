# System Architecture

## Overview

The AIOps RCA Assistant is built using a **microservices-inspired monolithic architecture** with clear separation of concerns.

## Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
├────────────────────────────────────────────────────────────────┤
│  dashboard.html  │  login.html  │  register.html               │
│  (Static HTML/JS/CSS with WebSocket for real-time updates)     │
└───────────────────────┬────────────────────────────────────────┘
                        │ HTTP/WebSocket
                        ▼
┌────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER (FastAPI)                 │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐│
│  │  Webhook         │  │  Dashboard       │  │  Auth         ││
│  │  Endpoints       │  │  API             │  │  Module       ││
│  │                  │  │                  │  │               ││
│  │ /azure-monitor   │  │ /api/tickets     │  │ /login        ││
│  │ /databricks-mon  │  │ /api/open-tickets│  │ /register     ││
│  │ /airflow-monitor │  │ /api/audit       │  │ /logout       ││
│  │ /jira-webhook    │  │ /dashboard       │  │               ││
│  └──────────────────┘  └──────────────────┘  └───────────────┘│
└───────────────────────┬────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                       │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐│
│  │  RCA Generation  │  │  Error           │  │  Duplicate    ││
│  │                  │  │  Classification  │  │  Detection    ││
│  │ Gemini AI        │  │                  │  │               ││
│  │ Integration      │  │ Pattern Matching │  │ run_id check  ││
│  └──────────────────┘  └──────────────────┘  └───────────────┘│
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐│
│  │  JIRA            │  │  Slack           │  │  Azure Blob   ││
│  │  Integration     │  │  Integration     │  │  Storage      ││
│  └──────────────────┘  └──────────────────┘  └───────────────┘│
└───────────────────────┬────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────────┐
│                       DATA ACCESS LAYER                         │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  SQLite Database │  │  Audit Trail     │                   │
│  │  (tickets)       │  │  (audit_log)     │                   │
│  └──────────────────┘  └──────────────────┘                   │
└────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Webhook Receivers
**File:** `main.py` (lines 2600-3900)

**Endpoints:**
- `/azure-monitor` - Azure Data Factory & general alerts
- `/databricks-monitor` - Databricks cluster/job failures
- `/airflow-monitor` - Airflow DAG/task failures
- `/jira-webhook` - JIRA status updates

**Responsibilities:**
- Receive external failure notifications
- Validate webhook payloads
- Extract error metadata
- Route to processing pipeline

### 2. Error Classification Module
**File:** `cluster_failure_detector.py`, `airflow_integration.py`

**Purpose:** Pattern-match errors against known failure types

**Error Categories:**
- NetworkError
- DatabaseError
- ResourceExhaustion
- AuthenticationError
- DataError
- ExternalServiceError

### 3. AI RCA Engine
**File:** `main.py` - `generate_rca_and_recs()`

**Process:**
1. Receive error context
2. Send to Gemini AI with prompt
3. Parse AI response
4. Extract root cause, recommendations, severity

**Fallback:** If Gemini fails, use rule-based RCA

### 4. Ticket Management
**File:** `main.py` - Database operations

**Schema:**
- tickets table (30+ columns)
- audit_log table
- users table

**Operations:**
- Create ticket
- Update status
- Link JIRA ticket
- Track SLA

### 5. Integration Handlers

#### JIRA Integration
**Functions:**
- `create_jira_ticket()` - Create ticket
- `update_jira_status()` - Sync status
- `jira_webhook()` - Receive status updates

#### Slack Integration
**Functions:**
- `post_slack_notification()` - Send initial alert
- `update_slack_message_on_ack()` - Update on close
- `update_slack_message_on_reopen()` - Update on reopen

### 6. Dashboard
**File:** `dashboard.html`

**Features:**
- Ticket browsing (Open/In Progress/Closed)
- Real-time updates via WebSocket
- Detailed ticket modal view
- Audit trail viewer
- SLA countdown timers

## Data Flow

### Failure Detection Flow

```
1. Failure Occurs
   └─> Azure Monitor Alert / Airflow Callback
       └─> POST to RCA Webhook Endpoint
           └─> Extract & Validate Payload
               └─> Check for Duplicates (by run_id)
                   ├─> Duplicate Found: Return existing ticket_id
                   └─> New Failure:
                       └─> Classify Error Type
                           └─> Generate AI RCA
                               └─> Create Ticket in DB
                                   ├─> Create JIRA Ticket
                                   ├─> Send Slack Notification
                                   ├─> Upload Logs to Blob
                                   └─> Return ticket_id
```

### JIRA Bidirectional Sync Flow

```
User Updates JIRA
└─> JIRA Webhook Triggered
    └─> POST /jira-webhook
        └─> Extract Status Change
            └─> Map JIRA Status → RCA Status
                ├─> "Done" → acknowledged
                ├─> "In Progress" → in_progress
                └─> "To Do" → open
                    └─> Update Local Ticket
                        └─> Update Slack Message
                            └─> Broadcast WebSocket Event
```

## Database Schema

### Tickets Table

```sql
CREATE TABLE tickets (
    id TEXT PRIMARY KEY,                  -- e.g., ADF-20251210T123456-abc123
    timestamp TEXT NOT NULL,
    pipeline TEXT NOT NULL,
    run_id TEXT UNIQUE,                   -- Azure/Airflow run identifier
    rca_result TEXT,                      -- AI-generated root cause
    recommendations TEXT,                 -- JSON array of recommendations
    confidence REAL,                      -- AI confidence score
    severity TEXT,                        -- Critical/High/Medium/Low
    priority TEXT,                        -- P1/P2/P3/P4
    error_type TEXT,                      -- Error classification
    affected_entity TEXT,                 -- JSON metadata
    status TEXT DEFAULT 'open',           -- open/in_progress/acknowledged
    sla_seconds INTEGER,                  -- SLA in seconds
    sla_status TEXT,                      -- Pending/Met/Breached
    finops_team TEXT,                     -- Team owner
    finops_owner TEXT,                    -- Email of owner
    finops_cost_center TEXT,              -- Cost center
    blob_log_url TEXT,                    -- Azure Blob URL
    itsm_ticket_id TEXT,                  -- JIRA ticket key
    ack_ts TEXT,                          -- Acknowledgment timestamp
    ack_user TEXT,                        -- Who closed ticket
    ack_seconds INTEGER,                  -- MTTR in seconds
    slack_ts TEXT,                        -- Slack message timestamp
    slack_channel TEXT,                   -- Slack channel ID
    logic_app_run_id TEXT,                -- Logic App run ID
    processing_mode TEXT,                 -- adf/databricks/airflow-arf
    remediation_status TEXT               -- Auto-remediation status
);
```

### Audit Log Table

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    ticket_id TEXT,
    action TEXT,                          -- Action type
    user_name TEXT,
    user_empid TEXT,
    pipeline TEXT,
    run_id TEXT,
    rca_summary TEXT,
    sla_status TEXT,
    finops_team TEXT,
    finops_owner TEXT,
    itsm_ticket_id TEXT,
    details TEXT
);
```

## Security Architecture

### Authentication
- Basic username/password (stored hashed with bcrypt)
- Session-based auth with secure cookies
- Password requirements enforced

### Authorization
- Role-based access control (future enhancement)
- API key authentication for webhooks (future)

### Data Protection
- Secrets stored in environment variables
- HTTPS recommended for production
- SQL injection prevention via parameterized queries

## Scalability Considerations

### Current Limits
- SQLite database (single file)
- Single-instance deployment
- In-memory WebSocket connections

### Production Scaling Options
1. **Database:** Migrate to PostgreSQL/MySQL
2. **Caching:** Add Redis for session management
3. **Load Balancing:** Deploy multiple instances with nginx
4. **Queue:** Add Celery for async task processing
5. **WebSocket:** Use Redis pub/sub for multi-instance WS

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI 0.104+, Python 3.12 |
| **Database** | SQLite (dev), PostgreSQL (prod recommended) |
| **AI/ML** | Google Gemini 2.5 Flash |
| **Frontend** | Vanilla JS, HTML5, CSS3 |
| **Real-time** | WebSocket (ASGI) |
| **Cloud** | Azure (Monitor, Blob, Databricks) |
| **ITSM** | JIRA Cloud API |
| **Messaging** | Slack Webhooks |
| **Data Pipeline** | Airflow 2.x |

## Performance Metrics

### Response Times
- Webhook processing: <2s
- AI RCA generation: 3-15s (Gemini API latency)
- JIRA ticket creation: 1-3s
- Slack notification: <1s
- Dashboard page load: <500ms

### Throughput
- Concurrent webhook requests: 50+
- Database operations: 1000+ ops/sec (SQLite)
- WebSocket connections: 100+ (single instance)

---

*Next: [02_AZURE_SETUP.md](02_AZURE_SETUP.md) - Azure Configuration*
