"""
Test DAG for RCA Integration

This DAG demonstrates how to integrate with the RCA system.
It includes tasks that intentionally fail to test auto-remediation.
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from rca_callbacks import on_failure_callback

# Default arguments for the DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,  # Airflow will retry once before sending to RCA
    'retry_delay': timedelta(minutes=2),
    'on_failure_callback': on_failure_callback,  # ← RCA Integration
}

# Create the DAG
with DAG(
    dag_id='test_rca_integration',
    default_args=default_args,
    description='Test DAG to verify RCA system integration',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['test', 'rca', 'monitoring'],
) as dag:

    # Task 1: Success task (baseline)
    def task_success():
        """This task always succeeds"""
        print("✅ Task completed successfully!")
        return "success"

    success_task = PythonOperator(
        task_id='success_task',
        python_callable=task_success,
        doc_md="""
        ### Success Task
        This task always succeeds to verify normal operation.
        """,
    )

    # Task 2: Connection Error (Auto-remediable)
    def task_connection_error():
        """Simulates a connection error - should trigger auto-remediation"""
        import time
        time.sleep(1)  # Simulate some work
        raise ConnectionError(
            "Unable to connect to database server db.example.com:5432 - "
            "Connection refused. This is a test error for RCA system."
        )

    connection_error_task = PythonOperator(
        task_id='test_connection_error',
        python_callable=task_connection_error,
        doc_md="""
        ### Connection Error Test
        This task simulates a connection error that should be auto-remediable.

        **Expected RCA Behavior:**
        - Error classified as: `AirflowConnectionError`
        - Auto-remediable: Yes
        - Action: `retry_task`
        - Risk: Low
        """,
    )

    # Task 3: Timeout Error
    def task_timeout_error():
        """Simulates a timeout error"""
        import time
        time.sleep(1)
        raise TimeoutError(
            "Task execution timed out after 300 seconds while waiting for API response"
        )

    timeout_error_task = PythonOperator(
        task_id='test_timeout_error',
        python_callable=task_timeout_error,
        doc_md="""
        ### Timeout Error Test
        This task simulates a timeout error.

        **Expected RCA Behavior:**
        - Error classified as: `AirflowTimeoutError`
        - Auto-remediable: Yes
        - Action: `retry_task`
        - Risk: Low
        """,
    )

    # Task 4: File Not Found (Data dependency issue)
    def task_file_not_found():
        """Simulates missing data file"""
        import time
        time.sleep(1)
        raise FileNotFoundError(
            "Input file not found: /data/input/customer_data_2025-01-01.csv - "
            "Upstream pipeline may not have completed yet"
        )

    file_not_found_task = PythonOperator(
        task_id='test_file_not_found',
        python_callable=task_file_not_found,
        doc_md="""
        ### File Not Found Test
        This task simulates a missing input file.

        **Expected RCA Behavior:**
        - Error classified as: `FileNotFound`
        - Auto-remediable: Yes
        - Action: `retry_task`
        - Risk: Low
        - Suggestion: Check upstream pipeline
        """,
    )

    # Task 5: API Error
    def task_api_error():
        """Simulates external API error"""
        import time
        time.sleep(1)
        raise Exception(
            "API Error: External service returned 503 Service Unavailable. "
            "Endpoint: https://api.example.com/v1/data"
        )

    api_error_task = PythonOperator(
        task_id='test_api_error',
        python_callable=task_api_error,
        doc_md="""
        ### API Error Test
        This task simulates an external API failure.

        **Expected RCA Behavior:**
        - Error classified as: `APIError`
        - Auto-remediable: Yes
        - Action: `retry_task`
        - Risk: Medium
        """,
    )

    # Task 6: Database Error
    def task_database_error():
        """Simulates database connection pool exhaustion"""
        import time
        time.sleep(1)
        raise Exception(
            "DatabaseError: Connection pool exhausted - all 20 connections in use. "
            "Database: postgres://prod-db:5432/analytics"
        )

    database_error_task = PythonOperator(
        task_id='test_database_error',
        python_callable=task_database_error,
        doc_md="""
        ### Database Error Test
        This task simulates a database connection issue.

        **Expected RCA Behavior:**
        - Error classified as: `DatabaseError`
        - Auto-remediable: Yes
        - Action: `retry_task`
        - Risk: Medium
        """,
    )

    # Task 7: Manual Intervention Required (Not auto-remediable)
    def task_data_quality_error():
        """Simulates data quality issue - requires manual fix"""
        import time
        time.sleep(1)
        raise ValueError(
            "Data quality validation failed: Column 'age' contains negative values. "
            "Invalid records: 127. This requires data correction."
        )

    data_quality_task = PythonOperator(
        task_id='test_data_quality_error',
        python_callable=task_data_quality_error,
        doc_md="""
        ### Data Quality Error Test
        This task simulates a data quality issue that requires manual intervention.

        **Expected RCA Behavior:**
        - Error classified as: Application/DataQualityError
        - Auto-remediable: NO
        - Action: `manual_intervention`
        - Risk: High
        - Requires: Human review and data correction
        """,
    )

    # Task 8: Bash command that fails
    bash_error_task = BashOperator(
        task_id='test_bash_command_error',
        bash_command='echo "Running command..." && exit 1',  # Intentional failure
        doc_md="""
        ### Bash Command Error Test
        This task tests Bash operator failure handling.
        """,
    )

    # Task dependencies (run independently, no dependencies)
    # You can run each task individually to test specific error types

    # Note: Tasks are independent - you can trigger them individually
    # via Airflow UI or CLI to test specific error scenarios

# DAG documentation
dag.doc_md = """
# RCA Integration Test DAG

This DAG tests the integration between Airflow and the RCA (Root Cause Analysis) system.

## Purpose
- Verify RCA webhook connectivity
- Test error classification
- Validate auto-remediation triggers
- Demonstrate different error types

## How to Use

### 1. Trigger Entire DAG
```bash
airflow dags trigger test_rca_integration
```

### 2. Trigger Specific Task (Recommended for testing)
```bash
# Test connection error
airflow tasks test test_rca_integration test_connection_error 2025-01-01

# Test timeout error
airflow tasks test test_rca_integration test_timeout_error 2025-01-01

# Test file not found
airflow tasks test test_rca_integration test_file_not_found 2025-01-01
```

### 3. Check RCA System
After triggering tasks, check:
1. RCA app logs: `grep "AIRFLOW" /var/log/rca-app.log`
2. RCA dashboard: http://your-rca-app.com/dashboard
3. Tickets created with error analysis

## Expected Results

| Task | Error Type | Auto-Remediable? | Action |
|------|-----------|------------------|--------|
| test_connection_error | ConnectionError | Yes | retry_task |
| test_timeout_error | TimeoutError | Yes | retry_task |
| test_file_not_found | FileNotFound | Yes | retry_task |
| test_api_error | APIError | Yes | retry_task |
| test_database_error | DatabaseError | Yes | retry_task |
| test_data_quality_error | ValueError | NO | manual_intervention |

## Monitoring

- **Airflow Logs**: Check task logs in Airflow UI
- **RCA Tickets**: View tickets in RCA dashboard
- **Auto-Remediation**: Check if Logic App triggered (for auto-remediable errors)

## Tags
- test
- rca
- monitoring
"""
