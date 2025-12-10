# Airflow DAGs

This directory contains Airflow DAG definitions for testing RCA system integration.

## Directory Structure

```
airflow/
├── dags/              # Airflow DAG files
│   └── prod_etl_failure_test.py
└── README.md          # This file
```

## DAGs

### prod_etl_failure_test.py
Production-like ETL failure scenarios for testing RCA generation.

**Contains 8 realistic failure scenarios:**
1. Database connection timeout
2. S3 file not found
3. Data quality validation failure
4. External API timeout
5. Out of memory error
6. Schema mismatch error
7. Permission denied error
8. Duplicate key violation

## Setup

### Configure Airflow to Use These DAGs

**Option 1: Set AIRFLOW_HOME (Recommended for development)**
```bash
export AIRFLOW_HOME=$PWD/airflow
airflow db init
airflow scheduler &
airflow webserver --port 8080 &
```

**Option 2: Symlink to Existing Airflow**
```bash
ln -s $PWD/airflow/dags/prod_etl_failure_test.py ~/airflow/dags/
```

**Option 3: Copy to Existing Airflow**
```bash
cp airflow/dags/*.py ~/airflow/dags/
```

## Testing

### Test Individual Tasks
```bash
airflow tasks test prod_etl_failure_test validate_data_quality 2025-12-10
airflow tasks test prod_etl_failure_test extract_from_database 2025-12-10
```

### Trigger Entire DAG
```bash
airflow dags trigger prod_etl_failure_test
```

## Integration

All DAG failures automatically send webhooks to the RCA system at:
- **Webhook URL:** `http://localhost:8000/airflow-monitor`

The RCA system will:
1. Receive failure notification
2. Classify error type
3. Generate intelligent RCA
4. Create JIRA ticket
5. Send Slack notification
6. Display in dashboard

## See Also

- [Airflow Setup Guide](../docs/AIRFLOW_LOCAL_SETUP_GUIDE.md)
- [Integration Guide](../docs/AIRFLOW_INTEGRATION_SETUP.md)
