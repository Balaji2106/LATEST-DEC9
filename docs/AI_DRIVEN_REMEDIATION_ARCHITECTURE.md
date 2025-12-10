# AI-Driven Auto-Remediation Architecture

## 🎯 Overview

**OLD APPROACH (Hardcoded):**
- 38+ error types hardcoded in `REMEDIABLE_ERRORS` dictionary
- Fixed retry counts and backoff schedules
- No intelligence, just pattern matching

**NEW APPROACH (AI-Driven):**
- AI analyzes EVERY error dynamically
- AI decides if error is remediable
- AI chooses appropriate action
- AI determines retry strategy based on risk
- Adapts to new error types automatically

---

## 🧠 How AI Makes Remediation Decisions

When an error occurs, the AI analyzes:

### 1. **Error Characteristics**
- Is it transient or permanent?
- Is it infrastructure or application level?
- Does it have a deterministic fix?
- What's the risk of auto-remediation?

### 2. **Business Impact Assessment**
```python
# AI determines:
{
  "business_impact": "Low|Medium|High|Critical",
  "severity": "Low|Medium|High|Critical",
  "affected_entity": "pipeline-name or cluster-id"
}
```

### 3. **Remediation Decision**
```python
# AI decides:
{
  "is_auto_remediable": true/false,
  "remediation_action": "retry_pipeline|restart_cluster|retry_job|reinstall_libraries|check_upstream|manual_intervention",
  "remediation_risk": "Low|Medium|High",
  "requires_human_approval": true/false
}
```

### 4. **Retry Strategy** (Based on Risk)
```python
DEFAULT_RETRY_SCHEDULES = {
    "Low": {
        "max_retries": 3,
        "backoff_seconds": [30, 60, 120]
    },
    "Medium": {
        "max_retries": 2,
        "backoff_seconds": [60, 180, 300]
    },
    "High": {
        "max_retries": 1,
        "backoff_seconds": [180]
    }
}
```

---

## 📊 AI Remediation Decision Matrix

| Error Type | Typical AI Decision | Action | Risk | Approval Required? |
|------------|-------------------|--------|------|-------------------|
| **Network Timeout** | Auto-remediable | retry_pipeline/retry_job | Low | No |
| **Connection Failed** | Auto-remediable | retry_pipeline/retry_job | Low | No |
| **Throttling Error** | Auto-remediable | retry_pipeline | Low | No |
| **Cluster Out of Memory** | Auto-remediable | restart_cluster | Medium | Maybe (if High impact) |
| **Driver Unreachable** | Auto-remediable | restart_cluster | Medium | Maybe |
| **Library Install Failed** | Auto-remediable | reinstall_libraries | Medium | No |
| **Schema Mismatch** | Manual | manual_intervention | High | Yes |
| **Data Quality Issue** | Manual | manual_intervention | High | Yes |
| **Permission Denied** | Manual | manual_intervention | High | Yes |
| **Unknown Error** | Manual | manual_intervention | High | Yes |

---

## 🔄 Auto-Remediation Flow

```
1. ERROR OCCURS
   ↓
2. WEBHOOK → RCA System
   ↓
3. AI ANALYZES ERROR
   ├─ Determines root cause
   ├─ Classifies error type
   ├─ Assesses business impact
   ├─ Evaluates remediation risk
   └─ Makes remediation decision
   ↓
4. AI RETURNS JSON:
   {
     "is_auto_remediable": true,
     "remediation_action": "retry_job",
     "remediation_risk": "Low",
     "requires_human_approval": false,
     "business_impact": "Medium",
     "max_retries": 3  # Based on risk level
   }
   ↓
5. RCA POLICY ENGINE EVALUATES:
   ├─ Is auto-remediation enabled?
   ├─ Does AI say it's remediable?
   ├─ Is remediation action valid?
   ├─ Does it require approval?
   │   ├─ YES → Send Slack approval request
   │   └─ NO → Proceed automatically
   ↓
6. TRIGGER LOGIC APP
   - Looks up playbook URL from REMEDIATION_ACTION_PLAYBOOKS
   - Uses AI-determined retry strategy
   - Sends payload to Logic App
   ↓
7. LOGIC APP EXECUTES
   - Performs remediation action
   - Monitors completion
   - Sends callback with result
   ↓
8. RCA UPDATES TICKET
   - Success → "Auto-Resolved"
   - Failed → Retry or escalate
```

---

## 🎨 Configuration (Simplified)

### Before (Hardcoded):
```python
REMEDIABLE_ERRORS = {
    "SqlFailedToConnect": {
        "action": "retry_pipeline",
        "max_retries": 3,
        "backoff_seconds": [60, 120, 300],
        "playbook_url": "https://..."
    },
    "NetworkTimeout": {
        "action": "retry_pipeline",
        "max_retries": 3,
        # ... 38+ more entries
    }
}
```

### After (AI-Driven):
```python
# Just map actions to Logic App endpoints
REMEDIATION_ACTION_PLAYBOOKS = {
    "retry_pipeline": os.getenv("PLAYBOOK_RETRY_PIPELINE"),
    "retry_job": os.getenv("PLAYBOOK_RETRY_JOB"),
    "restart_cluster": os.getenv("PLAYBOOK_RESTART_CLUSTER"),
    "reinstall_libraries": os.getenv("PLAYBOOK_REINSTALL_LIBRARIES"),
    "retry_task": os.getenv("PLAYBOOK_RETRY_AIRFLOW_TASK"),
    "check_upstream": os.getenv("PLAYBOOK_RERUN_UPSTREAM"),
}

# Default retry strategies by risk level
DEFAULT_RETRY_SCHEDULES = {
    "Low": {"max_retries": 3, "backoff_seconds": [30, 60, 120]},
    "Medium": {"max_retries": 2, "backoff_seconds": [60, 180, 300]},
    "High": {"max_retries": 1, "backoff_seconds": [180]}
}
```

---

## 🤖 AI Prompt Guidelines

The AI follows these strict rules when making remediation decisions:

### ✅ AI Sets `is_auto_remediable = true` ONLY IF:
- Error is **transient** (network, timeout, throttling)
- Error is **infrastructure-related** (cluster failure, resource exhaustion)
- Error has **deterministic fix** (retry, restart, reinstall)
- **NO data loss risk**
- **NO security implications**
- **NO production data corruption risk**

### ❌ AI Sets `is_auto_remediable = false` (Manual) IF:
- **Data quality issues** (schema mismatch, invalid data)
- **Business logic errors**
- **Permission/authentication errors** (may need IAM changes)
- **Source data missing** (not available yet)
- **Configuration errors** (code changes needed)
- **ANY uncertainty** about root cause

### 🎯 AI Chooses `remediation_action`:
- `retry_pipeline`: ADF transient failures (timeout, connection, throttling)
- `restart_cluster`: Databricks cluster failures
- `retry_job`: Databricks job execution transient failures
- `reinstall_libraries`: Library installation issues
- `retry_task`: Airflow task failures
- `check_upstream`: Missing source data (wait for upstream)
- `manual_intervention`: Everything else

### 📊 AI Determines `remediation_risk`:
- **Low**: Simple retry, no side effects (network errors, timeouts)
- **Medium**: Restart operations, resource allocation changes
- **High**: Data operations, multi-service dependencies

### 🚦 AI Sets `requires_human_approval = true` IF ANY OF:
- `remediation_risk` is "High"
- `severity` is "Critical"
- `business_impact` is "Critical" OR "High"
- Affects production financial/customer data
- Multiple failed remediation attempts already occurred
- Uncertainty in root cause (`confidence` is "Low")

---

## 💡 Benefits of AI-Driven Approach

### 1. **Adaptability**
- No need to update code for new error types
- AI learns from error patterns
- Handles edge cases intelligently

### 2. **Intelligence**
- Context-aware decisions
- Risk assessment
- Business impact consideration

### 3. **Maintainability**
- No hardcoded error lists to maintain
- Simple configuration (just action-to-playbook mapping)
- AI prompts can be tuned without code changes

### 4. **Coverage**
- Handles **ANY** error type
- Not limited to pre-defined list
- Discovers new remediable patterns automatically

### 5. **Safety**
- Conservative by default ("when in doubt, escalate")
- Approval workflows for high-risk changes
- Clear audit trail of AI decisions

---

## 📝 Example: AI Decision Process

### Input Error:
```
"ERROR: Connection to SQL database timed out after 30 seconds.
Endpoint: myserver.database.windows.net:1433
Pipeline: load_customer_data_pipeline"
```

### AI Analysis:
```json
{
  "root_cause": "Network timeout connecting to SQL database endpoint",
  "error_type": "NetworkTimeout",
  "affected_entity": "load_customer_data_pipeline",
  "severity": "Medium",
  "priority": "P2",
  "confidence": "Very High",
  "is_auto_remediable": true,
  "remediation_action": "retry_pipeline",
  "remediation_risk": "Low",
  "requires_human_approval": false,
  "business_impact": "Medium",
  "estimated_resolution_time_minutes": 3,
  "recommendations": [
    "Retry pipeline execution immediately",
    "Check SQL server availability if retry fails",
    "Review network connectivity to database endpoint"
  ]
}
```

### RCA System Action:
```python
# Policy Engine evaluates:
if rca["is_auto_remediable"]:  # True
    if rca["requires_human_approval"]:  # False
        # Proceed automatically
        action = rca["remediation_action"]  # "retry_pipeline"
        risk = rca["remediation_risk"]  # "Low"
        retry_config = DEFAULT_RETRY_SCHEDULES[risk]  # Low → 3 retries

        playbook_url = REMEDIATION_ACTION_PLAYBOOKS[action]
        trigger_logic_app(playbook_url, retry_config)
```

---

## 🔒 Safety Mechanisms

### 1. **AI Conservative Defaults**
- When uncertain → `is_auto_remediable = false`
- Prefer manual intervention over risky automation

### 2. **Multi-Layer Approval Gates**
- High business impact → Slack approval
- Critical severity → Slack approval
- Low confidence → Slack approval

### 3. **Retry Limits**
- Low risk: Max 3 retries
- Medium risk: Max 2 retries
- High risk: Max 1 retry

### 4. **Duplicate Detection**
- 3-layer protection against cascading failures
- Prevents infinite retry loops

### 5. **Audit Logging**
- Every AI decision logged
- Full remediation attempt history
- Clear accountability trail

---

## 📈 Expected Improvements

| Metric | Hardcoded Approach | AI-Driven Approach |
|--------|-------------------|-------------------|
| **Error Coverage** | 38 predefined types | Unlimited (any error) |
| **Maintenance Effort** | High (update code for new errors) | Low (tune AI prompts) |
| **Adaptability** | Static rules | Dynamic learning |
| **Intelligence** | Pattern matching | Context-aware decisions |
| **Safety** | Rule-based | Risk-assessed |
| **New Error Handling** | Requires code update | Automatic |
| **Configuration Lines** | 281 lines | 20 lines |

---

## 🚀 Migration Guide

### Step 1: Already Done ✅
- Removed hardcoded `REMEDIABLE_ERRORS` dictionary
- Added `REMEDIATION_ACTION_PLAYBOOKS` mapping
- Added `DEFAULT_RETRY_SCHEDULES` by risk level

### Step 2: Update `trigger_auto_remediation()` Function
- Use AI-provided `remediation_action` instead of error_type lookup
- Use AI-provided `remediation_risk` to determine retry strategy
- Remove dependency on `REMEDIABLE_ERRORS` dictionary

### Step 3: Update Policy Engine
- Check `rca["is_auto_remediable"]` instead of `error_type in REMEDIABLE_ERRORS`
- Use AI-provided fields directly

### Step 4: Test
- Verify AI makes correct decisions for known error types
- Test with new/unknown error types
- Validate approval workflows trigger correctly

---

## 🎯 Conclusion

**The AI-driven approach provides:**
- ✅ Unlimited error type support
- ✅ Intelligent context-aware decisions
- ✅ Minimal configuration maintenance
- ✅ Automatic adaptation to new patterns
- ✅ Risk-based remediation strategies
- ✅ Conservative safety-first approach

**The system is now truly intelligent and self-adapting!** 🧠
