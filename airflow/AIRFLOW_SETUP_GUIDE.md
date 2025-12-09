# Complete Airflow Setup Guide with RCA Integration

Step-by-step guide to install Apache Airflow and integrate with RCA system.

---

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- 4GB RAM minimum (8GB recommended)
- Linux/macOS/WSL (Windows)

---

## 🚀 Quick Start (3 Commands)

```bash
# 1. Install Airflow
./airflow/setup_airflow.sh

# 2. Start Airflow
./airflow/start_airflow.sh

# 3. Access Airflow UI
# Open browser: http://localhost:8080
# Username: admin
# Password: admin
```

---

## 📦 STEP 1: Install Apache Airflow

### Option A: Using Setup Script (Recommended)

```bash
cd /home/user/LATEST-DEC9
chmod +x airflow/setup_airflow.sh
./airflow/setup_airflow.sh
```

### Option B: Manual Installation

```bash
# Set Airflow home directory
export AIRFLOW_HOME=~/airflow

# Install Airflow (version 2.8.0)
AIRFLOW_VERSION=2.8.0
PYTHON_VERSION="$(python --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

# Install additional providers
pip install apache-airflow-providers-http
pip install apache-airflow-providers-postgres
pip install pandas  # For data processing in DAGs
```

---

## ⚙️ STEP 2: Configure Airflow

### Initialize Airflow Database

```bash
export AIRFLOW_HOME=~/airflow
airflow db init
```

### Create Admin User

```bash
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

### Update airflow.cfg

Edit `~/airflow/airflow.cfg`:

```ini
[core]
# Your Airflow home
dags_folder = /home/user/LATEST-DEC9/airflow/dags
plugins_folder = /home/user/LATEST-DEC9/airflow/plugins

# Load examples (set to False for production)
load_examples = False

# Parallelism
parallelism = 32
dag_concurrency = 16
max_active_runs_per_dag = 3

[webserver]
# Webserver settings
base_url = http://localhost:8080
web_server_host = 0.0.0.0
web_server_port = 8080

# Enable RBAC
rbac = True

[scheduler]
# How often to scan for new DAGs
dag_dir_list_interval = 30

[api]
# Enable API
auth_backends = airflow.api.auth.backend.basic_auth

[logging]
# Logging level
logging_level = INFO
```

---

## 🔗 STEP 3: Setup RCA Integration

### Update RCA Callback Configuration

Edit `airflow/dags/rca_callbacks.py`:

```python
# Update these values for your environment:

RCA_WEBHOOK_URL = "http://your-rca-app-url:8000/airflow-monitor"
AIRFLOW_BASE_URL = "http://your-airflow-url:8080"
```

### Copy DAGs to Airflow

```bash
# Link DAGs directory (recommended for development)
ln -s /home/user/LATEST-DEC9/airflow/dags ~/airflow/dags

# OR copy DAGs (for production)
cp -r /home/user/LATEST-DEC9/airflow/dags/* ~/airflow/dags/
```

---

## 🎯 STEP 4: Start Airflow

### Option A: Using Start Script (Recommended)

```bash
./airflow/start_airflow.sh
```

### Option B: Manual Start (Two Terminal Windows)

**Terminal 1 - Start Webserver:**
```bash
export AIRFLOW_HOME=~/airflow
airflow webserver --port 8080
```

**Terminal 2 - Start Scheduler:**
```bash
export AIRFLOW_HOME=~/airflow
airflow scheduler
```

### Option C: Background Mode

```bash
# Start webserver in background
airflow webserver --port 8080 --daemon

# Start scheduler in background
airflow scheduler --daemon
```

---

## 🧪 STEP 5: Test RCA Integration

### 1. Access Airflow UI

Open browser: `http://localhost:8080`
- Username: `admin`
- Password: `admin`

### 2. Verify DAGs Loaded

You should see these DAGs:
- ✅ `test_rca_integration` - Test DAG for RCA
- ✅ `customer_data_etl_pipeline` - Example production DAG

### 3. Test Connection Error

```bash
# Run specific test task
airflow tasks test test_rca_integration test_connection_error 2025-01-01
```

**Expected Output:**
```
[2025-01-09 10:00:00] INFO - Task exited with return code 1
[2025-01-09 10:00:00] INFO - 📤 Sending failure notification to RCA system
[2025-01-09 10:00:00] INFO - ✅ Successfully sent to RCA system
[2025-01-09 10:00:00] INFO - 🎫 RCA Ticket created: AIRFLOW-20250109-abc123
```

### 4. Check RCA System

**RCA App Logs:**
```bash
# Check if webhook received
grep "AIRFLOW" /var/log/rca-app.log
```

**RCA Dashboard:**
```
Open: http://your-rca-app:8000/dashboard
Look for: New ticket with error analysis
```

### 5. Test Other Error Types

```bash
# Test timeout error
airflow tasks test test_rca_integration test_timeout_error 2025-01-01

# Test file not found
airflow tasks test test_rca_integration test_file_not_found 2025-01-01

# Test API error
airflow tasks test test_rca_integration test_api_error 2025-01-01
```

---

## 📊 STEP 6: Monitor and Verify

### Check Airflow Logs

```bash
# Scheduler logs
tail -f ~/airflow/logs/scheduler/latest/*.log | grep RCA

# Task logs (in Airflow UI)
# Go to: DAG > Task > Logs
```

### Check Task Execution

```bash
# List DAG runs
airflow dags list-runs -d test_rca_integration

# List task instances
airflow tasks list test_rca_integration
```

### Verify RCA Integration

```bash
# Test RCA webhook manually
curl -X POST http://localhost:8000/airflow-monitor \
  -H "Content-Type: application/json" \
  -d '{
    "dag_id": "test_dag",
    "task_id": "test_task",
    "run_id": "manual__2025-01-09",
    "execution_date": "2025-01-09T10:00:00",
    "exception": "Test error for verification"
  }'
```

---

## 🔧 Troubleshooting

### Problem: DAGs Not Showing Up

**Solution:**
```bash
# Check DAGs folder
ls -la ~/airflow/dags/

# Refresh DAGs in Airflow
airflow dags list

# Check for import errors
python ~/airflow/dags/test_rca_integration_dag.py
```

### Problem: RCA Webhook Failing

**Check 1: Is RCA app running?**
```bash
curl http://localhost:8000/health
```

**Check 2: Is URL correct in rca_callbacks.py?**
```bash
grep "RCA_WEBHOOK_URL" ~/airflow/dags/rca_callbacks.py
```

**Check 3: Network connectivity**
```bash
ping your-rca-server
telnet your-rca-server 8000
```

### Problem: Import Error - requests module not found

**Solution:**
```bash
# Install in Airflow environment
pip install requests
```

### Problem: Airflow command not found

**Solution:**
```bash
# Add to PATH
export PATH=$PATH:~/.local/bin

# OR reinstall Airflow
pip install --user apache-airflow
```

---

## 📁 Directory Structure After Setup

```
~/airflow/
├── airflow.cfg                  # Airflow configuration
├── airflow.db                   # SQLite database (development)
├── dags/                        # Your DAGs (linked or copied)
│   ├── rca_callbacks.py        # RCA integration callbacks
│   ├── test_rca_integration_dag.py
│   └── example_production_dag.py
├── logs/                        # Airflow logs
│   ├── scheduler/
│   └── dag_id/
└── plugins/                     # Airflow plugins
```

---

## 🎨 Using RCA Integration in Your DAGs

### Method 1: Apply to All Tasks in DAG

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from rca_callbacks import on_failure_callback

default_args = {
    'owner': 'your-team',
    'on_failure_callback': on_failure_callback,  # ← RCA Integration
    'retries': 2,
}

with DAG('my_dag', default_args=default_args, ...) as dag:
    # All tasks will send failures to RCA
    task1 = PythonOperator(...)
    task2 = PythonOperator(...)
```

### Method 2: Apply to Specific Tasks Only

```python
from airflow.operators.python import PythonOperator
from rca_callbacks import on_failure_callback

critical_task = PythonOperator(
    task_id='critical_process',
    python_callable=my_function,
    on_failure_callback=on_failure_callback,  # Only this task
)

non_critical_task = PythonOperator(
    task_id='non_critical',
    python_callable=another_function,
    # No callback - failures not sent to RCA
)
```

---

## 🚀 Production Deployment

### 1. Use PostgreSQL/MySQL for Metadata DB

```bash
# Install PostgreSQL provider
pip install apache-airflow-providers-postgres

# Update airflow.cfg
[database]
sql_alchemy_conn = postgresql+psycopg2://user:pass@localhost/airflow
```

### 2. Use CeleryExecutor for Scaling

```bash
# Install Celery
pip install apache-airflow[celery]
pip install redis

# Update airflow.cfg
[core]
executor = CeleryExecutor

[celery]
broker_url = redis://localhost:6379/0
result_backend = db+postgresql://user:pass@localhost/airflow
```

### 3. Setup Environment Variables

```bash
# Add to ~/.bashrc or /etc/environment
export AIRFLOW_HOME=~/airflow
export AIRFLOW__CORE__DAGS_FOLDER=/home/user/LATEST-DEC9/airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
```

### 4. Setup Systemd Services

Create `/etc/systemd/system/airflow-webserver.service`:
```ini
[Unit]
Description=Airflow webserver daemon
After=network.target

[Service]
Environment="AIRFLOW_HOME=/home/airflow/airflow"
User=airflow
Group=airflow
Type=simple
ExecStart=/usr/local/bin/airflow webserver
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/airflow-scheduler.service`:
```ini
[Unit]
Description=Airflow scheduler daemon
After=network.target

[Service]
Environment="AIRFLOW_HOME=/home/airflow/airflow"
User=airflow
Group=airflow
Type=simple
ExecStart=/usr/local/bin/airflow scheduler
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable airflow-webserver
sudo systemctl enable airflow-scheduler
sudo systemctl start airflow-webserver
sudo systemctl start airflow-scheduler
```

---

## 📈 Expected Results

After successful setup:
- ✅ Airflow UI accessible at http://localhost:8080
- ✅ Test DAGs visible in UI
- ✅ Task failures sent to RCA system
- ✅ RCA tickets created with AI analysis
- ✅ Auto-remediation triggered for remediable errors
- ✅ Monitoring dashboard shows Airflow failures

---

## 📞 Support

### Airflow Documentation
- Official Docs: https://airflow.apache.org/docs/
- Installation: https://airflow.apache.org/docs/apache-airflow/stable/installation/
- Tutorials: https://airflow.apache.org/docs/apache-airflow/stable/tutorial/

### RCA Integration Issues
- Check RCA app logs
- Verify webhook URL in rca_callbacks.py
- Test webhook manually with curl
- Check network connectivity

### Common Commands

```bash
# Restart Airflow
pkill -f airflow
airflow webserver --daemon
airflow scheduler --daemon

# Clear task state
airflow tasks clear dag_id -t task_id

# Trigger DAG manually
airflow dags trigger my_dag

# View logs
airflow tasks logs dag_id task_id execution_date
```

---

**Your Airflow + RCA integration is ready! 🚀**
