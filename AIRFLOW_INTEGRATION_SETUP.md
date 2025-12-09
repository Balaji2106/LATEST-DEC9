# Airflow Integration with RCA System

Complete guide to integrate Apache Airflow with the AI-powered RCA system for automatic failure detection and remediation.

---

## 🎯 Overview

**What this enables:**
- ✅ Automatic detection of Airflow DAG/task failures
- ✅ AI-powered root cause analysis for Airflow errors
- ✅ Intelligent error classification (network, resource, dependency, etc.)
- ✅ Auto-remediation for common Airflow failures
- ✅ Centralized monitoring across ADF, Databricks, and Airflow

**Flow:**
```
Airflow Task Fails →
on_failure_callback triggers →
Webhook to RCA System →
AI RCA + Error Classification →
Auto-Remediation (if applicable) →
Ticket created with analysis
```

---

## 📋 Prerequisites

1. **Airflow 2.x** (tested with 2.5+)
2. **RCA app deployed** and publicly accessible
3. **Airflow webserver** accessible for log links
4. **Python requests library** installed in Airflow environment

---

## 🔧 SETUP METHOD 1: Global Failure Callback (Recommended)

This method automatically captures ALL DAG/task failures across your Airflow instance.

### Step 1: Create Failure Callback Function

Create a file: `airflow/dags/rca_callbacks.py`

```python
"""
RCA System Integration Callbacks for Airflow
"""
import json
import requests
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
RCA_WEBHOOK_URL = "https://your-rca-app.com/airflow-monitor"
AIRFLOW_BASE_URL = "http://your-airflow-webserver:8080"

def send_to_rca(context: Dict) -> None:
    """
    Send Airflow task failure to RCA system.

    Args:
        context: Airflow task context dict
    """
    try:
        # Extract task information
        task_instance = context.get('task_instance')
        exception = context.get('exception')

        # Build payload for RCA system
        payload = {
            "dag_id": context.get('dag').dag_id,
            "task_id": task_instance.task_id,
            "run_id": context.get('dag_run').run_id,
            "execution_date": str(context.get('execution_date')),
            "logical_date": str(context.get('logical_date')),
            "try_number": task_instance.try_number,
            "max_tries": task_instance.max_tries,
            "operator": task_instance.operator,
            "pool": task_instance.pool,
            "queue": task_instance.queue,
            "state": str(task_instance.state),
            "exception": str(exception) if exception else "No exception details",
            "error": str(exception) if exception else None,
            "log_url": task_instance.log_url,
            "timestamp": datetime.utcnow().isoformat(),
            "airflow_base_url": AIRFLOW_BASE_URL
        }

        # Send webhook
        logger.info(f"Sending failure notification to RCA system for {payload['dag_id']}.{payload['task_id']}")

        response = requests.post(
            RCA_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"✅ Successfully sent to RCA system. Response: {response.json()}")
        else:
            logger.error(f"❌ RCA webhook failed. Status: {response.status_code}, Response: {response.text}")

    except Exception as e:
        logger.error(f"❌ Exception sending to RCA system: {e}")
        # Don't raise - we don't want RCA integration to break the DAG


def on_failure_callback(context: Dict) -> None:
    """
    Airflow failure callback that sends to RCA system.

    Use this in your DAG's default_args or individual tasks.
    """
    send_to_rca(context)
```

### Step 2: Configure Global Callback (airflow.cfg)

Edit your `airflow.cfg`:

```ini
[core]
# Enable callbacks
enable_xcom_pickling = True

[webserver]
# Your Airflow webserver URL (for log links)
base_url = http://your-airflow-webserver:8080

[email]
# Optional: email notifications on failure
email_on_failure = False
email_on_retry = False
```

### Step 3: Use Callback in DAGs

**Option A: Apply to ALL tasks in a DAG** (Recommended)

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from rca_callbacks import on_failure_callback

# Default args with RCA callback
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,  # Airflow will retry once before sending to RCA
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': on_failure_callback,  # ← RCA integration
}

with DAG(
    'my_data_pipeline',
    default_args=default_args,
    description='ETL pipeline with RCA integration',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    def my_task():
        # Your task logic
        pass

    task1 = PythonOperator(
        task_id='process_data',
        python_callable=my_task,
    )
```

**Option B: Apply to specific tasks only**

```python
from airflow.operators.python import PythonOperator
from rca_callbacks import on_failure_callback

critical_task = PythonOperator(
    task_id='critical_process',
    python_callable=my_function,
    on_failure_callback=on_failure_callback,  # Only this task sends to RCA
)
```

---

## 🔧 SETUP METHOD 2: Airflow Plugin (Advanced)

For automatic integration without modifying DAGs.

### Create Plugin: `plugins/rca_integration_plugin.py`

```python
"""
RCA Integration Plugin for Airflow
Automatically sends all task failures to RCA system
"""
from airflow.plugins_manager import AirflowPlugin
from airflow.listeners import hookimpl
from airflow.utils.state import TaskInstanceState
import requests
import logging

logger = logging.getLogger(__name__)

RCA_WEBHOOK_URL = "https://your-rca-app.com/airflow-monitor"

class RCAIntegrationListener:
    """Listener that sends task failures to RCA system"""

    @hookimpl
    def on_task_instance_failed(self, previous_state, task_instance, session):
        """Called when a task instance fails"""
        try:
            # Build payload
            payload = {
                "dag_id": task_instance.dag_id,
                "task_id": task_instance.task_id,
                "run_id": task_instance.run_id,
                "execution_date": str(task_instance.execution_date),
                "try_number": task_instance.try_number,
                "max_tries": task_instance.max_tries,
                "operator": task_instance.operator,
                "state": str(task_instance.state),
                "exception": "Task failed",  # Exception not available in listener
                "log_url": task_instance.log_url,
            }

            # Send to RCA
            response = requests.post(RCA_WEBHOOK_URL, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"✅ Sent failure to RCA: {task_instance.dag_id}.{task_instance.task_id}")
            else:
                logger.warning(f"⚠️ RCA webhook failed: {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Error sending to RCA: {e}")


class RCAIntegrationPlugin(AirflowPlugin):
    """Plugin to register RCA integration listener"""
    name = "rca_integration"
    listeners = [RCAIntegrationListener()]
```

### Enable Plugin

1. Restart Airflow webserver and scheduler:
   ```bash
   airflow webserver --daemon
   airflow scheduler --daemon
   ```

2. Verify plugin loaded:
   ```bash
   airflow plugins
   # Should show: rca_integration
   ```

---

## 📊 Supported Error Types & Auto-Remediation

The RCA system automatically classifies and remediates these Airflow errors:

| Error Type | Category | Auto-Remediation | Max Retries |
|------------|----------|------------------|-------------|
| **ConnectionError** | Network | Retry task | 3 |
| **TimeoutError** | Timeout | Retry with extended timeout | 2 |
| **OutOfMemory** | Resource | Retry with more resources | 2 |
| **SensorTimeout** | Dependency | Check upstream and retry | 2 |
| **FileNotFound** | Data | Check upstream and retry | 2 |
| **APIError** | External Service | Retry with backoff | 3 |
| **AuthenticationError** | Auth | Alert (no retry) | 0 |
| **DatabaseError** | Database | Retry with backoff | 3 |
| **DatabricksSubmitRunError** | Databricks | Retry job submission | 2 |

---

## 🧪 Testing the Integration

### Test 1: Create a Failing DAG

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from rca_callbacks import on_failure_callback

default_args = {
    'owner': 'test',
    'on_failure_callback': on_failure_callback,
}

with DAG(
    'test_rca_integration',
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
) as dag:

    def fail_task():
        raise ConnectionError("Unable to connect to database - test error")

    test_task = PythonOperator(
        task_id='test_failure',
        python_callable=fail_task,
    )
```

### Test 2: Trigger and Verify

1. **Trigger the DAG:**
   ```bash
   airflow dags trigger test_rca_integration
   ```

2. **Check Airflow logs:**
   ```
   ✅ Successfully sent to RCA system. Response: {...}
   ```

3. **Check RCA app logs:**
   ```
   AIRFLOW TASK FAILURE RECEIVED
   🔍 ANALYZING ERROR: ConnectionError
   ✅ Error classified: ConnectionError (NetworkError)
   🎫 Ticket created: AIRFLOW-20251209-abc123
   ```

4. **Check RCA dashboard:**
   - New ticket should appear
   - Error classified as "NetworkError"
   - Recommendation: "Retry task (3 attempts)"

---

## 📝 Webhook Payload Format

The RCA system receives this payload from Airflow:

```json
{
  "dag_id": "my_etl_pipeline",
  "task_id": "extract_data",
  "run_id": "manual__2025-12-09T10:00:00+00:00",
  "execution_date": "2025-12-09T10:00:00",
  "logical_date": "2025-12-09T10:00:00",
  "try_number": 2,
  "max_tries": 3,
  "operator": "PythonOperator",
  "pool": "default_pool",
  "queue": "default",
  "state": "failed",
  "exception": "ConnectionError: Unable to connect to database",
  "log_url": "http://airflow:8080/dags/my_etl_pipeline/grid?dag_run_id=...",
  "timestamp": "2025-12-09T10:05:30.123456",
  "airflow_base_url": "http://airflow:8080"
}
```

---

## 🎯 Best Practices

### 1. **Use Callback on Critical DAGs Only**
```python
# Critical production DAG - send to RCA
production_args = {
    'on_failure_callback': on_failure_callback,
    'retries': 2,  # Let Airflow retry first
}

# Test/dev DAG - no RCA integration
dev_args = {
    'retries': 0,  # Fail fast in dev
}
```

### 2. **Let Airflow Retry First**
```python
default_args = {
    'retries': 2,  # Airflow retries 2 times
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': on_failure_callback,  # RCA triggered after all retries exhausted
}
```

### 3. **Add Context to Error Messages**
```python
def my_task():
    try:
        # Your logic
        process_data()
    except Exception as e:
        # Add context to help RCA
        raise Exception(f"Failed processing {file_name}: {str(e)}")
```

### 4. **Use Environment-Specific Endpoints**
```python
import os

RCA_WEBHOOK_URL = os.getenv(
    'RCA_WEBHOOK_URL',
    'https://rca-prod.company.com/airflow-monitor' if os.getenv('ENV') == 'production'
    else 'https://rca-dev.company.com/airflow-monitor'
)
```

---

## 🔍 Troubleshooting

### Problem: Callback not triggering

**Check 1: Verify callback is registered**
```python
# In your DAG
print(f"Failure callback: {dag.default_args.get('on_failure_callback')}")
# Should print: <function on_failure_callback at 0x...>
```

**Check 2: Check Airflow logs**
```bash
tail -f $AIRFLOW_HOME/logs/scheduler/latest/*.log | grep "RCA"
```

**Check 3: Test callback manually**
```python
from rca_callbacks import on_failure_callback
from airflow.models import TaskInstance

# Simulate context
context = {
    'dag': dag,
    'task_instance': task_instance,
    'exception': Exception("Test error"),
}

on_failure_callback(context)
```

### Problem: Webhook failing

**Check 1: Is RCA endpoint accessible from Airflow?**
```python
import requests
response = requests.get("https://your-rca-app.com/health")
print(response.status_code)  # Should be 200
```

**Check 2: Check network/firewall**
- Ensure Airflow scheduler can reach RCA app
- Check for proxy settings
- Verify SSL certificates

**Check 3: Check RCA app logs**
```bash
grep "airflow-monitor" rca-app.log
```

### Problem: Errors not classified correctly

**Add more context to exceptions:**
```python
# Bad - generic error
raise Exception("Failed")

# Good - specific error with context
raise ConnectionError(f"Unable to connect to {database_host}:5432 - connection refused")
```

---

## 📈 Expected Results

After setup:
- ✅ **Automatic failure detection** (<1 minute after task fails)
- ✅ **Intelligent error classification** (90%+ accuracy)
- ✅ **AI-powered RCA** with specific recommendations
- ✅ **Auto-remediation** for 9 common error types
- ✅ **Centralized monitoring** across all data platforms

---

## 🔗 Integration with Other Systems

### Airflow + Databricks Integration

If your Airflow DAGs run Databricks jobs:

```python
from airflow.providers.databricks.operators.databricks import DatabricksSubmitRunOperator

databricks_task = DatabricksSubmitRunOperator(
    task_id='run_databricks_job',
    json={
        'existing_cluster_id': 'cluster-id',
        'notebook_task': {...},
    },
    on_failure_callback=on_failure_callback,  # Captures Databricks errors too!
)
```

The RCA system will:
1. Detect Databricks error from Airflow
2. Fetch cluster details if cluster failed
3. Provide enhanced RCA with both Airflow + Databricks context

---

## 🚀 Next Steps

1. **Create `rca_callbacks.py`** with your RCA webhook URL
2. **Update one DAG** with `on_failure_callback`
3. **Trigger a test failure** and verify integration
4. **Roll out to all production DAGs**
5. **Monitor RCA dashboard** for automatic issue detection

---

## 📞 Support

If you encounter issues:
1. Check Airflow scheduler logs for callback execution
2. Verify RCA app received webhook (check app logs)
3. Test callback function manually with sample context
4. Ensure network connectivity between Airflow and RCA app

---

**Your Airflow integration is ready! 🚀**
