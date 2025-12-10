# Auto-Remediation & Duplicate Filtering - Complete Implementation

## Overview
This document describes the complete auto-remediation and duplicate filtering implementation for both **Azure Data Factory (ADF)** and **Databricks** in the AIOps RCA Assistant.

## Recent Commits (All Fixes Applied)
```
45f4c68 - Fix infinite loop race condition - prevent cascading ticket creation
b1af762 - Fix AI prompt to enforce Slack approval for High business impact
dd8d12d - Fix Logic App InvalidTemplate error - remove @int() conversion
4ed1d21 - Fix DatabricksDriverNotResponding remediation - use retry_job instead of restart_cluster
2dfa87d - Add updated Logic App with job_id integer type support
```

---

## 1. AI Prompt Fix - Slack Approval Logic

**File:** `genai_rca_assistant/main.py` (Lines 704-717, 840-853)

### Problem
AI was auto-approving remediation even when `business_impact: "High"`, contrary to policy requirements.

### Fix
Updated both Databricks and Azure RCA prompts to be explicit:

```python
5. **requires_human_approval**:
   - ALWAYS set to **true** if ANY of these conditions apply:
     * remediation_risk is "High"
     * severity is "Critical"
     * business_impact is "Critical" OR "High"
     * Affects production financial/customer data
     * Multiple failed remediation attempts already occurred
     * Uncertainty in root cause (confidence is "Low")
   - Set to **false** ONLY if ALL of these are true:
     * remediation_risk is "Low"
     * severity is NOT "Critical"
     * business_impact is "Low" or "Medium" (NOT High or Critical)
     * High confidence in diagnosis
```

### Impact
- ✅ `DatabricksDriverNotResponding` with High business impact → Slack approval required
- ✅ All High/Critical business impact errors → Human approval requested
- ✅ Only Low/Medium impact + Low risk → Auto-approved

---

## 2. Race Condition Fix - Placeholder Insertion

**File:** `genai_rca_assistant/main.py` (Lines 1298-1338 for ADF, similar for Databricks)

### Problem - The Race Condition
```
Timeline:
T0: Python calls Logic App to retry pipeline/job
T1: Logic App triggers Azure/Databricks → NEW run_id assigned
T2: Pipeline/job fails immediately (30-second timeout)
T3: Webhook arrives BEFORE remediation_run_id saved to database
T4: System doesn't recognize it as remediation attempt
T5: Creates DUPLICATE ticket ❌ (infinite loop!)
T6: Original Python call saves remediation_run_id (TOO LATE)
```

### Fix - Placeholder Insertion BEFORE Logic App Call

**Step 1: Insert Placeholder (Lines 1306-1319)**
```python
pending_run_id = f"PENDING-{ticket_id}-{attempt_number}"
db_execute('''INSERT INTO remediation_attempts
            (ticket_id, original_run_id, remediation_run_id, attempt_number,
             status, error_type, remediation_action, logic_app_response, started_at)
            VALUES (:ticket_id, :original_run_id, :remediation_run_id, :attempt_number,
             :status, :error_type, :remediation_action, :logic_app_response, :started_at)''',
         {"ticket_id": ticket_id, "original_run_id": original_run_id,
          "remediation_run_id": pending_run_id,
          "attempt_number": attempt_number, "status": "pending",
          "error_type": error_type,
          "remediation_action": remediation_config["action"],
          "logic_app_response": json.dumps({"status": "pending"}),
          "started_at": datetime.now(timezone.utc).isoformat()})
logger.info(f"[AUTO-REM] Pre-inserted placeholder remediation attempt: {pending_run_id}")
```

**Step 2: Call Logic App (Line 1323)**
```python
response = _http_post_with_retries(playbook_url, payload, timeout=30, retries=3)
```

**Step 3: Update with Actual run_id (Lines 1330-1338)**
```python
if response and response.status_code == 200:
    response_data = response.json()
    remediation_run_id = response_data.get("run_id", "N/A")

    db_execute('''UPDATE remediation_attempts
                SET remediation_run_id = :new_run_id,
                    status = :status,
                    logic_app_response = :response
                WHERE ticket_id = :ticket_id
                AND attempt_number = :attempt_number''',
             {"new_run_id": remediation_run_id, "status": "in_progress",
              "response": json.dumps(response_data),
              "ticket_id": ticket_id, "attempt_number": attempt_number})
    logger.info(f"[AUTO-REM] Updated remediation attempt with actual run_id: {remediation_run_id}")
```

### Impact
- ✅ Placeholder exists in database BEFORE Logic App triggers
- ✅ Webhook arrivals during race condition window are caught
- ✅ No duplicate tickets created even if retry fails immediately

---

## 3. Databricks - Recent Remediation Check

**File:** `genai_rca_assistant/main.py` (Lines 2968-2995)

### Problem
Even with placeholder insertion, there's a small window where:
1. Placeholder inserted as "PENDING-DBX-123-1"
2. Logic App triggers Databricks (run_id = 999999)
3. Job fails, webhook arrives with run_id = 999999
4. Database query for run_id = 999999 → NOT FOUND (placeholder is "PENDING-DBX-123-1")
5. Could still create duplicate

### Fix - Second Layer of Protection
```python
if job_id or cluster_id:
    recent_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    # Find tickets for this job_id or cluster_id with recent pending/in-progress remediation
    if job_id:
        recent_remediation = db_query('''
            SELECT t.id, t.remediation_status, ra.status as attempt_status
            FROM tickets t
            LEFT JOIN remediation_attempts ra ON t.id = ra.ticket_id
            WHERE t.pipeline = :job_name
            AND ra.started_at > :cutoff
            AND ra.status IN ('pending', 'in_progress')
            ORDER BY ra.started_at DESC
            LIMIT 1
        ''', {"job_name": job_name, "cutoff": recent_cutoff}, one=True)

        if recent_remediation:
            logger.warning(f"⏸️ Recent remediation in progress for job {job_name}, waiting for callback")
            logger.info(f"🔄 This appears to be a retry from ongoing remediation for ticket {recent_remediation['id']}")
            return {
                "status": "remediation_in_progress",
                "ticket_id": recent_remediation["id"],
                "message": f"Remediation already in progress for this job, handled by callback"
            }
```

### Impact
- ✅ Catches remediation retries based on job_name + timestamp (not just run_id)
- ✅ Backup protection if run_id hasn't been updated yet
- ✅ Prevents cascading ticket creation: Ticket #1 → Ticket #2 → Ticket #3 → ...

### Log Example (Fix Working)
```
2025-12-06 15:43:54,132 [WARNING] ⏸️ Recent remediation in progress for job auto-rem-random, waiting for callback
2025-12-06 15:43:54,132 [INFO] 🔄 This appears to be a retry from ongoing remediation for ticket DBX-20251206T100021-df5ed9
INFO:     20.42.4.210:0 - "POST /databricks-monitor HTTP/1.1" 200 OK
```

---

## 4. ADF - Webhook Deduplication

**File:** `genai_rca_assistant/main.py` (Lines 2407-2459)

### Check 1: Direct run_id Match in remediation_attempts
```python
remediation_match = db_query("""
    SELECT ra.ticket_id, ra.attempt_number, t.status, t.remediation_status
    FROM remediation_attempts ra
    JOIN tickets t ON ra.ticket_id = t.id
    WHERE ra.remediation_run_id = :run_id
    ORDER BY ra.started_at DESC
    LIMIT 1
""", {"run_id": runid}, one=True)

if remediation_match:
    ticket_id = remediation_match['ticket_id']
    attempt_num = remediation_match['attempt_number']
    logger.warning(f"[WEBHOOK-DEDUP] Remediation retry failure detected: run_id {runid} is attempt #{attempt_num} for ticket {ticket_id}")
    return JSONResponse({
        "status": "remediation_retry_ignored",
        "ticket_id": ticket_id,
        "message": f"Remediation attempt #{attempt_num} already tracked - callback will handle"
    })
```

### Check 2: Active Remediation for Same Pipeline
```python
active_remediation = db_query("""
    SELECT id, remediation_run_id, remediation_attempts, remediation_status, run_id
    FROM tickets
    WHERE pipeline = :pipeline
    AND remediation_status IN ('pending', 'in_progress', 'awaiting_approval')
    AND timestamp > datetime('now', '-20 minutes')
    ORDER BY timestamp DESC
    LIMIT 1
""", {"pipeline": pipeline}, one=True)

if active_remediation:
    logger.info(f"[WEBHOOK-DEDUP] Active remediation found for pipeline {pipeline}")
    logger.info(f"[WEBHOOK-DEDUP] Ticket: {active_remediation['id']}, Attempts: {active_remediation.get('remediation_attempts', 0)}")
    logger.info(f"[WEBHOOK-DEDUP] Webhook run_id: {runid}, Original ticket run_id: {active_remediation.get('run_id')}")

    log_audit(
        ticket_id=active_remediation['id'],
        action="webhook_ignored_during_remediation",
        pipeline=pipeline,
        run_id=runid,
        details=f"Webhook received during active remediation. Callback will handle retry logic."
    )

    return JSONResponse({
        "status": "webhook_ignored_during_remediation",
        "ticket_id": active_remediation['id'],
        "message": "Active remediation in progress, callback will handle"
    })
```

### Log Example (Fix Working)
```
2025-12-06 15:49:01,468 [INFO] [WEBHOOK-DEDUP] Active remediation found for pipeline Data_engineering_Pipeline_Copy_to_database
2025-12-06 15:49:01,468 [INFO] [WEBHOOK-DEDUP] Ticket: ADF-20251206T095908-815da1, Attempts: 0
2025-12-06 15:49:01,474 [INFO] Audit logged: webhook_ignored_during_remediation for ADF-20251206T095908-815da1
```

---

## 5. Databricks - Additional Deduplication

**File:** `genai_rca_assistant/main.py` (Lines 2936-2966)

### Check 1: Direct Ticket run_id Match
```python
if run_id:
    existing = db_query(
        "SELECT id, status FROM tickets WHERE run_id = :run_id",
        {"run_id": run_id},
        one=True
    )
    if existing:
        logger.warning(f"❗ Duplicate Databricks run detected: run_id={run_id}")
        return {
            "status": "duplicate_ignored",
            "ticket_id": existing["id"],
            "message": f"Ticket already exists for run_id {run_id}"
        }
```

### Check 2: Remediation run_id Match
```python
remediation_attempt = db_query(
    "SELECT ticket_id FROM remediation_attempts WHERE remediation_run_id = :run_id",
    {"run_id": str(run_id)},
    one=True
)
if remediation_attempt:
    original_ticket_id = remediation_attempt["ticket_id"]
    logger.warning(f"❗ This run_id ({run_id}) is a remediation attempt for ticket {original_ticket_id}")
    logger.info(f"🔄 Remediation run failed - will be handled by callback, not creating new ticket")
    return {
        "status": "remediation_run_failed",
        "ticket_id": original_ticket_id,
        "message": f"This is a remediation run for ticket {original_ticket_id}, handled by callback"
    }
```

### Check 3: Recent Remediation (described in Section 3 above)

---

## 6. Auto-Remediation Policy Engine

**File:** `genai_rca_assistant/main.py`
- **ADF:** Lines 2571-2630
- **Databricks:** Lines 3124-3183

### Common Flow (Both ADF and Databricks)

```python
if AUTO_REMEDIATION_ENABLED:
    # Get AI recommendations
    is_auto_remediable = rca.get("is_auto_remediable", False)
    requires_approval = rca.get("requires_human_approval", False)
    error_type = rca.get("error_type")
    remediation_action = rca.get("remediation_action", "manual_intervention")
    remediation_risk = rca.get("remediation_risk", "High")
    business_impact = rca.get("business_impact", "Medium")

    if is_auto_remediable and error_type in REMEDIABLE_ERRORS:
        logger.info(f"[POLICY-ENGINE] Eligible for auto-remediation: {error_type} for ticket {tid}")

        # POLICY ENGINE DECISION POINT
        if requires_approval:
            # Risky remediation - request human approval
            logger.warning(f"[POLICY-ENGINE] Remediation requires human approval (Risk: {remediation_risk}, Impact: {business_impact})")
            await send_slack_approval_request(
                ticket_id=tid,
                pipeline_name=pipeline_name,
                error_type=error_type,
                remediation_action=remediation_action,
                remediation_risk=remediation_risk,
                business_impact=business_impact,
                root_cause=rca.get("root_cause", "Unknown"),
                recommendations=rca.get("recommendations", [])
            )
            log_audit(ticket_id=tid, action="auto_remediation_approval_required", ...)
        else:
            # Low risk - proceed with auto-remediation
            logger.info(f"[POLICY-ENGINE] Auto-remediation approved automatically (Risk: {remediation_risk}, Impact: {business_impact})")

            # ADF triggers: trigger_auto_remediation()
            # Databricks triggers: trigger_databricks_remediation()
            asyncio.create_task(trigger_xxx_remediation(
                ticket_id=tid,
                pipeline_name=pipeline_name,
                error_type=error_type,
                original_run_id=run_id,
                attempt_number=1
            ))
            log_audit(ticket_id=tid, action="auto_remediation_eligible", ...)
```

### Remediable Errors Configuration

**File:** `genai_rca_assistant/main.py` (Lines 164-205)

```python
REMEDIABLE_ERRORS = {
    # Azure Data Factory Errors
    "SqlFailedToConnect": {
        "action": "retry_pipeline",
        "max_retries": 2,
        "backoff_seconds": [60, 120],
        "playbook_url": os.getenv("PLAYBOOK_RETRY_PIPELINE")
    },
    "NetworkTimeout": {
        "action": "retry_pipeline",
        "max_retries": 3,
        "backoff_seconds": [30, 60, 120],
        "playbook_url": os.getenv("PLAYBOOK_RETRY_PIPELINE")
    },

    # Databricks Errors
    "DatabricksDriverNotResponding": {
        "action": "retry_job",  # ✅ FIXED: Was restart_cluster
        "max_retries": 3,
        "backoff_seconds": [30, 60, 120],
        "playbook_url": os.getenv("PLAYBOOK_RETRY_JOB")
    },
    "CLUSTER_OVERLOADED": {
        "action": "restart_cluster",
        "max_retries": 2,
        "backoff_seconds": [300, 600],
        "playbook_url": os.getenv("PLAYBOOK_RESTART_CLUSTER")
    },
    "LIBRARY_INSTALLATION_FAILED": {
        "action": "reinstall_libraries",
        "max_retries": 2,
        "backoff_seconds": [120, 300],
        "playbook_url": os.getenv("PLAYBOOK_REINSTALL_LIBRARIES")
    }
}
```

---

## 7. Remediation Callback Handler

**File:** `genai_rca_assistant/main.py` (Lines 2647-2795 for ADF/Databricks combined)

### Purpose
Logic Apps call this endpoint after:
1. Retrying the pipeline/job
2. Monitoring it until completion (Success/Failed)
3. Sending result back

### Key Logic

**Update remediation_run_id (Lines 2681-2693)**
```python
if remediation_run_id and remediation_run_id != "N/A":
    try:
        db_execute('''UPDATE remediation_attempts
                    SET remediation_run_id = :new_run_id
                    WHERE ticket_id = :ticket_id
                    AND attempt_number = :attempt_number''',
                  {"new_run_id": str(remediation_run_id),
                   "ticket_id": ticket_id,
                   "attempt_number": attempt_number})
        logger.info(f"[CALLBACK] Updated remediation_attempts with actual run_id: {remediation_run_id}")
    except Exception as e:
        logger.warning(f"[CALLBACK] Failed to update remediation_run_id: {e}")
```

**Handle Success (Lines 2717-2737)**
```python
if success:
    logger.info(f"[CALLBACK] ✅ Remediation SUCCEEDED for {ticket_id} (attempt {attempt_number})")
    db_execute('''UPDATE remediation_attempts
                SET status = :status, completed_at = :completed_at
                WHERE ticket_id = :ticket_id AND attempt_number = :attempt_number''',
              {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat(),
               "ticket_id": ticket_id, "attempt_number": attempt_number})

    db_execute('''UPDATE tickets
                SET remediation_status = :status, status = :ticket_status
                WHERE id = :id''',
              {"status": "completed", "ticket_status": "Auto-Resolved",
               "id": ticket_id})

    log_audit(ticket_id=ticket_id, action="auto_remediation_succeeded", ...)
    # Send Slack success notification
```

**Handle Failure + Retry (Lines 2739-2777)**
```python
else:
    logger.warning(f"[CALLBACK] ❌ Remediation FAILED for {ticket_id} (attempt {attempt_number})")
    db_execute('''UPDATE remediation_attempts
                SET status = :status, completed_at = :completed_at, error_message = :error_message
                WHERE ticket_id = :ticket_id AND attempt_number = :attempt_number''',
              {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat(),
               "error_message": error_message, "ticket_id": ticket_id, "attempt_number": attempt_number})

    # Check if we should retry
    if attempt_number < REMEDIABLE_ERRORS[error_type]["max_retries"]:
        logger.info(f"[CALLBACK] 🔄 Scheduling retry #{attempt_number + 1} for {ticket_id}")

        # Trigger next retry attempt
        asyncio.create_task(trigger_xxx_remediation(
            ticket_id=ticket_id,
            pipeline_name=pipeline_name,
            error_type=error_type,
            original_run_id=original_run_id,
            attempt_number=attempt_number + 1
        ))
    else:
        # Max retries exceeded
        logger.warning(f"[CALLBACK] ⛔ Max retries exceeded for {ticket_id}")
        db_execute('''UPDATE tickets
                    SET remediation_status = :status, status = :ticket_status
                    WHERE id = :id''',
                  {"status": "failed", "ticket_status": "Open",
                   "id": ticket_id})
        # Send Slack failure notification
```

---

## 8. Logic App Updates

**File:** `logic-apps/databricks-auto-remediation-updated.json`

### Fix 1: Schema - Accept Integer job_id (Lines 16-20)
```json
"job_id": {
    "type": ["integer", "null"]
}
```

### Fix 2: Remove @int() Conversion (Line 115)
```json
"body": {
    "job_id": "@triggerBody()?['job_id']"
}
```

**Why:** Python sends job_id as integer. Logic App no longer needs @int() conversion which was causing InvalidTemplate errors when job_id was null.

---

## Summary - Protection Layers

### Databricks Infinite Loop Prevention (3 Layers)

1. **Layer 1: Placeholder Insertion** (Lines 1306-1338)
   - Insert "PENDING-{ticket}-{attempt}" BEFORE Logic App call
   - Catches webhooks that match exact run_id

2. **Layer 2: Recent Remediation Check** (Lines 2968-2995)
   - Check for pending/in-progress remediation by job_name + timestamp
   - Catches webhooks during race condition window

3. **Layer 3: Direct Duplicate Detection** (Lines 2936-2966)
   - Check if run_id already exists in tickets table
   - Check if run_id exists in remediation_attempts table

### ADF Infinite Loop Prevention (3 Layers)

1. **Layer 1: Placeholder Insertion** (Lines 1306-1338)
   - Same as Databricks

2. **Layer 2: Remediation run_id Match** (Lines 2407-2434)
   - Check if run_id exists in remediation_attempts
   - Return "remediation_retry_ignored"

3. **Layer 3: Active Remediation Check** (Lines 2436-2459)
   - Check for active remediation by pipeline_name + timestamp
   - Return "webhook_ignored_during_remediation"

### Slack Approval Logic (Both ADF and Databricks)

**Require Approval IF:**
- remediation_risk is "High", OR
- severity is "Critical", OR
- business_impact is "Critical" OR "High", OR
- Affects production financial/customer data, OR
- Multiple failed remediation attempts, OR
- Uncertainty in root cause (confidence is "Low")

**Auto-Approve ONLY IF:**
- remediation_risk is "Low", AND
- severity is NOT "Critical", AND
- business_impact is "Low" or "Medium", AND
- High confidence in diagnosis

---

## Testing Results

### Before Fixes ❌
```
Ticket #1: DBX-20251206T100024-d1f5ed9 (3:30:21 PM) ← Original
Ticket #2: DBX-20251206T100023-20348c  (3:32:21 PM) ← Duplicate
Ticket #3: DBX-20251206T100022-e2ae17  (3:32:50 PM) ← Duplicate
Ticket #4: DBX-20251206T100021-df5ed9  (3:33:18 PM) ← Duplicate
```

### After Fixes ✅
```
2025-12-06 15:43:54,132 [WARNING] ⏸️ Recent remediation in progress for job auto-rem-random, waiting for callback
2025-12-06 15:43:54,132 [INFO] 🔄 This appears to be a retry from ongoing remediation for ticket DBX-20251206T100021-df5ed9
INFO:     20.42.4.210:0 - "POST /databricks-monitor HTTP/1.1" 200 OK
```
**Result:** No duplicate tickets created! ✅

### ADF Deduplication ✅
```
2025-12-06 15:49:01,468 [INFO] [WEBHOOK-DEDUP] Active remediation found for pipeline Data_engineering_Pipeline_Copy_to_database
2025-12-06 15:49:01,474 [INFO] Audit logged: webhook_ignored_during_remediation for ADF-20251206T095908-815da1
```
**Result:** Webhook correctly ignored during active remediation! ✅

---

## Files Modified

1. **genai_rca_assistant/main.py**
   - AI prompts (lines 704-717, 840-853)
   - Placeholder insertion (lines 1298-1338)
   - Databricks recent remediation check (lines 2968-2995)
   - All auto-remediation logic

2. **logic-apps/databricks-auto-remediation-updated.json**
   - Schema fix for integer job_id
   - Removed @int() conversion

---

## Deployment Checklist

- [x] Code committed and pushed
- [x] AI prompt updated for Slack approval logic
- [x] Placeholder insertion before Logic App calls
- [x] Recent remediation checks for both ADF and Databricks
- [ ] Restart uvicorn server to load new changes
- [ ] Deploy updated Logic App JSON to Azure Portal
- [ ] Test with new failures to verify:
  - [ ] Slack approval requested for High impact
  - [ ] No duplicate tickets created
  - [ ] Remediation callbacks working

---

## Environment Variables Required

```bash
# Auto-Remediation
AUTO_REMEDIATION_ENABLED=true
PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.dev

# Logic App Playbooks
PLAYBOOK_RETRY_PIPELINE=https://...logicapp.../retry-pipeline
PLAYBOOK_RETRY_JOB=https://...logicapp.../retry-job
PLAYBOOK_RESTART_CLUSTER=https://...logicapp.../restart-cluster
PLAYBOOK_REINSTALL_LIBRARIES=https://...logicapp.../reinstall-libraries

# Slack (Optional - for approval requests)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_ALERT_CHANNEL=aiops-alerts
```

---

## End of Document
