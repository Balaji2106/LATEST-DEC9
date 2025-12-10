# Apache Airflow Local Setup - Complete Guide

Step-by-step guide to install, configure, and test Apache Airflow locally with RCA integration.

---

## 🎯 What You'll Build

By the end of this guide, you'll have:
- ✅ Apache Airflow 2.x running locally
- ✅ Airflow webserver accessible at `http://localhost:8080`
- ✅ RCA integration configured
- ✅ Test DAG that sends failures to RCA system
- ✅ Everything running on your local machine

**Time needed:** 30-45 minutes

---

## 📋 Prerequisites

- **Python 3.8+** installed
- **pip** package manager
- **8GB RAM** minimum (Airflow is resource-intensive)
- **5GB disk space**
- **Terminal/Command Prompt** access

---

## 🚀 STEP 1: Install Apache Airflow

### Option A: Using pip (Recommended for Testing)

```bash
# 1. Create a directory for Airflow
mkdir ~/airflow-rca-test
cd ~/airflow-rca-test

# 2. Create Python virtual environment
python3 -m venv airflow-venv
source airflow-venv/bin/activate  # On Windows: airflow-venv\Scripts\activate

# 3. Set Airflow home directory
export AIRFLOW_HOME=$(pwd)/airflow  # On Windows: set AIRFLOW_HOME=%cd%\airflow

# 4. Install Airflow (version 2.8.0 - stable)
AIRFLOW_VERSION=2.8.0
PYTHON_VERSION="$(python --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

# 5. Install additional packages
pip install requests  # For RCA webhook integration
```

**Verify installation:**
```bash
airflow version
# Should show: 2.8.0
```

---

### Option B: Using Docker (Alternative)

If you prefer Docker:

```bash
# 1. Download docker-compose file
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.8.0/docker-compose.yaml'

# 2. Create directories
mkdir -p ./dags ./logs ./plugins ./config

# 3. Set Airflow UID
echo -e "AIRFLOW_UID=$(id -u)" > .env

# 4. Initialize database
docker compose up airflow-init

# 5. Start Airflow
docker compose up
```

**For this guide, we'll use Option A (pip install).**

---

## 🔧 STEP 2: Initialize Airflow Database

```bash
# Initialize the database (SQLite for local testing)
airflow db init

# You should see output like:
# DB: sqlite:////home/user/airflow-rca-test/airflow/airflow.db
# Database ready
```

**What this does:**
- Creates SQLite database at `$AIRFLOW_HOME/airflow.db`
- Sets up tables for DAGs, tasks, users, etc.

---

## 👤 STEP 3: Create Airflow Admin User

```bash
# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Use these credentials:
# Username: admin
# Password: admin
```

---

## 📁 STEP 4: Create RCA Integration Callback

Create the callback file that sends failures to RCA system.

### Create file: `$AIRFLOW_HOME/dags/rca_callbacks.py`

```bash
# Create dags directory if it doesn't exist
mkdir -p $AIRFLOW_HOME/dags

# Create the callback file
cat > $AIRFLOW_HOME/dags/rca_callbacks.py << 'EOF'
"""
RCA System Integration Callbacks for Airflow
Sends task failures to RCA system for automatic analysis
"""
import json
import requests
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - CHANGE THESE FOR YOUR ENVIRONMENT
# ============================================================================

# RCA webhook URL (local testing)
RCA_WEBHOOK_URL = "http://localhost:8000/airflow-monitor"

# Airflow webserver URL (for log links)
AIRFLOW_BASE_URL = "http://localhost:8080"

# Enable/disable RCA integration
RCA_ENABLED = True

# ============================================================================
# CALLBACK FUNCTION
# ============================================================================

def send_to_rca(context: Dict) -> None:
    """
    Send Airflow task failure to RCA system.

    Args:
        context: Airflow task context dictionary
    """
    if not RCA_ENABLED:
        logger.info("RCA integration disabled, skipping webhook")
        return

    try:
        # Extract task information
        task_instance = context.get('task_instance')
        exception = context.get('exception')
        dag = context.get('dag')
        dag_run = context.get('dag_run')

        # Build payload for RCA system
        payload = {
            "dag_id": dag.dag_id if dag else "unknown",
            "task_id": task_instance.task_id if task_instance else "unknown",
            "run_id": dag_run.run_id if dag_run else "unknown",
            "execution_date": str(context.get('execution_date')),
            "logical_date": str(context.get('logical_date')),
            "try_number": task_instance.try_number if task_instance else 1,
            "max_tries": task_instance.max_tries if task_instance else 1,
            "operator": task_instance.operator if task_instance else "unknown",
            "pool": task_instance.pool if task_instance else "default_pool",
            "queue": task_instance.queue if task_instance else "default",
            "state": str(task_instance.state) if task_instance else "failed",
            "exception": str(exception) if exception else "No exception details",
            "error": str(exception) if exception else None,
            "log_url": task_instance.log_url if task_instance else None,
            "timestamp": datetime.utcnow().isoformat(),
            "airflow_base_url": AIRFLOW_BASE_URL
        }

        # Send webhook
        logger.info(f"🔔 Sending failure notification to RCA system")
        logger.info(f"   DAG: {payload['dag_id']}")
        logger.info(f"   Task: {payload['task_id']}")
        logger.info(f"   Exception: {payload['exception'][:100]}...")

        response = requests.post(
            RCA_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ RCA webhook successful!")
            logger.info(f"   Response: {result}")
        else:
            logger.error(f"❌ RCA webhook failed!")
            logger.error(f"   Status: {response.status_code}")
            logger.error(f"   Response: {response.text}")

    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Could not connect to RCA system at {RCA_WEBHOOK_URL}")
        logger.error(f"   Make sure RCA app is running!")
    except Exception as e:
        logger.error(f"❌ Exception sending to RCA system: {e}")
        # Don't raise - we don't want RCA integration to break the DAG


def on_failure_callback(context: Dict) -> None:
    """
    Airflow failure callback that sends to RCA system.

    Use this in your DAG's default_args:
    default_args = {
        'on_failure_callback': on_failure_callback,
    }
    """
    logger.info("=" * 80)
    logger.info("TASK FAILURE CALLBACK TRIGGERED")
    logger.info("=" * 80)
    send_to_rca(context)
    logger.info("=" * 80)
EOF

echo "✅ Created rca_callbacks.py"
```

---

## 📝 STEP 5: Create Test DAG

Create a test DAG that will fail and trigger RCA integration.

### Create file: `$AIRFLOW_HOME/dags/test_rca_integration.py`

```bash
cat > $AIRFLOW_HOME/dags/test_rca_integration.py << 'EOF'
"""
Test DAG for RCA Integration
This DAG intentionally fails to test RCA webhook
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from rca_callbacks import on_failure_callback

# Default arguments for all tasks
default_args = {
    'owner': 'rca-test',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,  # Airflow will retry once before sending to RCA
    'retry_delay': timedelta(seconds=30),
    'on_failure_callback': on_failure_callback,  # ← RCA Integration
}

# Define DAG
with DAG(
    'test_rca_integration',
    default_args=default_args,
    description='Test DAG to verify RCA integration works',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['test', 'rca'],
) as dag:

    # Test 1: Connection Error
    def test_connection_error():
        """Simulates a connection error"""
        raise ConnectionError("Unable to connect to database server at 192.168.1.100:5432")

    task1 = PythonOperator(
        task_id='test_connection_error',
        python_callable=test_connection_error,
    )

    # Test 2: Timeout Error
    def test_timeout():
        """Simulates a timeout error"""
        raise TimeoutError("Task execution exceeded 300 second timeout")

    task2 = PythonOperator(
        task_id='test_timeout',
        python_callable=test_timeout,
    )

    # Test 3: File Not Found
    def test_file_not_found():
        """Simulates a file not found error"""
        raise FileNotFoundError("Input file not found: /data/input/2025-12-09.csv")

    task3 = PythonOperator(
        task_id='test_file_not_found',
        python_callable=test_file_not_found,
    )

    # Test 4: Generic API Error
    def test_api_error():
        """Simulates an API error"""
        raise Exception("API Error: Service unavailable (503) - External data service is down")

    task4 = PythonOperator(
        task_id='test_api_error',
        python_callable=test_api_error,
    )

    # Tasks run independently (no dependencies)
    # You can trigger each one separately to test different error types
EOF

echo "✅ Created test_rca_integration.py"
```

---

## ▶️ STEP 6: Start Airflow

You need to run TWO processes:

### Terminal 1: Start Airflow Webserver

```bash
# Activate virtual environment
cd ~/airflow-rca-test
source airflow-venv/bin/activate
export AIRFLOW_HOME=$(pwd)/airflow

# Start webserver
airflow webserver --port 8080
```

**Expected output:**
```
[DATE] {webserver.py:###} INFO - Starting the web server on port 8080
[DATE] {webserver.py:###} INFO - Running the Gunicorn Server with: ...
```

**Leave this running!**

### Terminal 2: Start Airflow Scheduler

Open a **NEW terminal window**:

```bash
# Activate virtual environment
cd ~/airflow-rca-test
source airflow-venv/bin/activate
export AIRFLOW_HOME=$(pwd)/airflow

# Start scheduler
airflow scheduler
```

**Expected output:**
```
[DATE] {scheduler.py:###} INFO - Starting the scheduler
[DATE] {scheduler.py:###} INFO - Processing files in: .../dags
```

**Leave this running too!**

---

## 🌐 STEP 7: Access Airflow UI

1. **Open browser:** http://localhost:8080
2. **Login:**
   - Username: `admin`
   - Password: `admin`
3. **You should see:** Airflow dashboard with your DAG listed

---

## ✅ STEP 8: Verify DAG is Loaded

In the Airflow UI:

1. **Check DAGs page** - You should see:
   - `test_rca_integration` DAG
   - Tags: `test`, `rca`
   - Schedule: `None` (manual trigger)

2. **If DAG is missing:**
   - Check scheduler logs for errors
   - Verify file is in `$AIRFLOW_HOME/dags/` directory
   - Check for Python syntax errors

---

## 🧪 STEP 9: Start Your RCA App

Before testing, make sure RCA app is running:

### Terminal 3: Start RCA App

```bash
cd /home/user/LATEST-DEC9/genai_rca_assistant
python main.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify RCA is accessible:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

---

## 🚀 STEP 10: Test the Integration!

### Test Flow:
```
1. Trigger DAG in Airflow
2. Task fails
3. Callback sends webhook to RCA
4. RCA creates ticket
5. Verify in RCA dashboard
```

### Steps:

1. **Go to Airflow UI:** http://localhost:8080

2. **Find DAG:** `test_rca_integration`

3. **Click on the DAG name** to open DAG details

4. **Trigger a specific task:**
   - Click "Graph" view
   - Click on task: `test_connection_error`
   - Click "Run" → "Run Task"
   - Click "Run" to confirm

5. **Watch the task fail:**
   - Task should turn red (failed) after ~30 seconds
   - Airflow retries once, then fails completely

6. **Check Airflow logs:**
   - Click the failed task
   - Click "Log" button
   - You should see:
     ```
     ================================================================================
     TASK FAILURE CALLBACK TRIGGERED
     ================================================================================
     🔔 Sending failure notification to RCA system
        DAG: test_rca_integration
        Task: test_connection_error
        Exception: Unable to connect to database server...
     ✅ RCA webhook successful!
        Response: {...}
     ================================================================================
     ```

7. **Check RCA App Logs:**

   In Terminal 3 (RCA app), you should see:
   ```
   INFO:     POST /airflow-monitor
   🔍 ANALYZING ERROR: ConnectionError
   ✅ Error classified: ConnectionError (NetworkError)
   🎫 Ticket created: AIRFLOW-20251209-abc123
   ```

8. **Check RCA Dashboard:**
   - Open: http://localhost:8000/dashboard
   - Login with your RCA credentials
   - You should see new ticket:
     - Title: `Airflow: test_rca_integration.test_connection_error`
     - Error Type: `ConnectionError`
     - Category: `NetworkError`
     - Recommendation: `Retry task (3 attempts)`

---

## 📊 Expected Results

### Successful Integration:

**Airflow Task Log:**
```
[2025-12-09 10:30:00] Task failed: ConnectionError: Unable to connect...
[2025-12-09 10:30:01] 🔔 Sending failure notification to RCA system
[2025-12-09 10:30:02] ✅ RCA webhook successful!
```

**RCA App Log:**
```
INFO: Airflow task failure received
INFO: DAG: test_rca_integration, Task: test_connection_error
INFO: Error classified: ConnectionError
INFO: Ticket created: AIRFLOW-20251209-abc123
```

**RCA Dashboard:**
```
New Ticket:
- ID: AIRFLOW-20251209-abc123
- Pipeline: test_rca_integration
- Task: test_connection_error
- Error: ConnectionError - Unable to connect to database server
- Severity: Medium
- Recommendation: Retry task with backoff (max 3 attempts)
```

---

## 🔍 Troubleshooting

### Problem 1: DAG not showing in UI

**Solution:**
```bash
# Check if file exists
ls -la $AIRFLOW_HOME/dags/test_rca_integration.py

# Check for syntax errors
python $AIRFLOW_HOME/dags/test_rca_integration.py

# Check scheduler logs
tail -f $AIRFLOW_HOME/logs/scheduler/latest/*.log
```

### Problem 2: Callback not triggering

**Check callback is registered:**
```bash
# In Airflow UI, go to DAG → Code view
# Look for: 'on_failure_callback': on_failure_callback
```

**Verify callback file:**
```bash
ls -la $AIRFLOW_HOME/dags/rca_callbacks.py
python -c "from rca_callbacks import on_failure_callback; print('OK')"
```

### Problem 3: RCA webhook fails

**Check RCA app is running:**
```bash
curl http://localhost:8000/health
```

**Check callback configuration:**
```bash
# Edit callback file
nano $AIRFLOW_HOME/dags/rca_callbacks.py

# Verify:
RCA_WEBHOOK_URL = "http://localhost:8000/airflow-monitor"  # ← Must match RCA URL
RCA_ENABLED = True  # ← Must be True
```

**Test webhook manually:**
```bash
curl -X POST http://localhost:8000/airflow-monitor \
  -H "Content-Type: application/json" \
  -d '{
    "dag_id": "test",
    "task_id": "test",
    "exception": "Test error"
  }'
```

### Problem 4: Connection refused

**Ensure both are running:**
- ✅ Airflow webserver (port 8080)
- ✅ Airflow scheduler
- ✅ RCA app (port 8000)

**Check ports:**
```bash
netstat -an | grep 8080  # Should show LISTEN
netstat -an | grep 8000  # Should show LISTEN
```

---

## 🎯 Testing Different Error Types

Trigger each task separately to test different error classifications:

| Task | Error Type | Expected RCA Classification |
|------|-----------|---------------------------|
| `test_connection_error` | ConnectionError | NetworkError → Retry (3x) |
| `test_timeout` | TimeoutError | TimeoutError → Retry with extended timeout (2x) |
| `test_file_not_found` | FileNotFoundError | DataError → Check upstream and retry (2x) |
| `test_api_error` | API Error | ExternalServiceError → Retry with backoff (3x) |

---

## 🛑 Stopping Airflow

When done testing:

1. **Stop webserver:** Press `Ctrl+C` in Terminal 1
2. **Stop scheduler:** Press `Ctrl+C` in Terminal 2
3. **Stop RCA app:** Press `Ctrl+C` in Terminal 3

---

## 📁 File Structure

After setup, you should have:

```
~/airflow-rca-test/
├── airflow-venv/              # Python virtual environment
├── airflow/
│   ├── airflow.db             # SQLite database
│   ├── airflow.cfg            # Airflow configuration
│   ├── dags/
│   │   ├── rca_callbacks.py   # ← RCA integration callback
│   │   └── test_rca_integration.py  # ← Test DAG
│   ├── logs/                  # Airflow logs
│   └── plugins/               # Airflow plugins
```

---

## 🚀 Next Steps

After successful testing:

1. **Create production DAGs** with RCA integration
2. **Deploy to production** Airflow environment
3. **Configure production webhook URL** in `rca_callbacks.py`
4. **Monitor RCA dashboard** for automatic issue detection

---

## 📚 Quick Reference

### Start Airflow (Every Time)

```bash
# Terminal 1: Webserver
cd ~/airflow-rca-test
source airflow-venv/bin/activate
export AIRFLOW_HOME=$(pwd)/airflow
airflow webserver --port 8080

# Terminal 2: Scheduler
cd ~/airflow-rca-test
source airflow-venv/bin/activate
export AIRFLOW_HOME=$(pwd)/airflow
airflow scheduler

# Terminal 3: RCA App
cd /home/user/LATEST-DEC9/genai_rca_assistant
python main.py
```

### URLs

- **Airflow UI:** http://localhost:8080
- **RCA Dashboard:** http://localhost:8000/dashboard
- **RCA API:** http://localhost:8000/docs

### Credentials

- **Airflow:** admin / admin
- **RCA:** (your credentials)

---

**You're all set! Test the integration and verify tickets are created in RCA! 🎉**
