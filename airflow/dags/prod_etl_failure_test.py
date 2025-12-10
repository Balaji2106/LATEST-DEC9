"""
Production-like ETL Failure Scenarios for RCA Testing
Simulates real-world data pipeline failures
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests

# RCA Webhook Configuration
RCA_WEBHOOK_URL = "http://localhost:8000/airflow-monitor"

def airflow_failure_callback(context):
    """Send failure notification to RCA system"""
    try:
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

        response = requests.post(RCA_WEBHOOK_URL, json=payload, timeout=10)
        print(f"RCA webhook response: {response.status_code}")
    except Exception as e:
        print(f"Failed to send RCA webhook: {e}")

# Realistic ETL Failure Scenarios

def database_connection_failure():
    """Simulates database connection timeout - common in production"""
    import psycopg2
    try:
        # Attempt to connect to non-existent database
        conn = psycopg2.connect(
            host="prod-analytics-db.internal.company.com",
            database="warehouse",
            user="etl_service",
            password="dummy",
            connect_timeout=5
        )
    except Exception as e:
        raise ConnectionError(f"Failed to connect to production database: {e}")

def s3_file_not_found():
    """Simulates missing source file in S3 - common ETL issue"""
    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client('s3')
    try:
        # Try to read file that doesn't exist
        s3.head_object(
            Bucket='prod-data-lake-raw',
            Key='daily_transactions/2025/12/10/transactions.parquet'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            raise FileNotFoundError(
                "Source file not found: s3://prod-data-lake-raw/daily_transactions/2025/12/10/transactions.parquet. "
                "Upstream system may have failed to deliver data."
            )
        raise

def data_quality_validation_failure():
    """Simulates data quality check failure - critical for production"""
    import pandas as pd

    # Simulate loading data
    df = pd.DataFrame({
        'customer_id': [1, 2, None, 4, 5],  # NULL value
        'transaction_amount': [100.50, -50.00, 200.00, 300.00, 0],  # Negative value
        'transaction_date': ['2025-12-10'] * 5
    })

    # Data quality checks
    null_count = df['customer_id'].isnull().sum()
    negative_amounts = (df['transaction_amount'] < 0).sum()

    if null_count > 0 or negative_amounts > 0:
        raise ValueError(
            f"Data Quality Validation Failed: "
            f"{null_count} NULL customer_ids found, "
            f"{negative_amounts} negative transaction amounts detected. "
            f"Data integrity compromised. Pipeline halted."
        )

def api_timeout_error():
    """Simulates external API timeout - common in real-time ETL"""
    import requests
    try:
        # Simulate API call with very short timeout
        response = requests.get(
            'https://api.external-vendor.com/v1/customer-data',
            timeout=0.001,  # Will timeout
            headers={'Authorization': 'Bearer prod-token-12345'}
        )
    except requests.exceptions.Timeout:
        raise TimeoutError(
            "External API timeout after 30 seconds. "
            "Vendor API (api.external-vendor.com) not responding. "
            "Check vendor status and network connectivity."
        )

def memory_exceeded_error():
    """Simulates out of memory error during large data processing"""
    import numpy as np
    try:
        # Try to allocate huge array (will fail)
        large_array = np.zeros((100000, 100000), dtype=np.float64)
    except MemoryError:
        raise MemoryError(
            "Out of memory error during data transformation. "
            "Current task requires 80GB RAM but only 16GB available. "
            "Consider partitioning data or increasing worker memory."
        )

def schema_mismatch_error():
    """Simulates schema evolution issue - common in production"""
    expected_schema = ['customer_id', 'name', 'email', 'signup_date', 'plan_type']
    actual_schema = ['customer_id', 'full_name', 'email_address', 'created_at']  # Changed

    missing_cols = set(expected_schema) - set(actual_schema)
    extra_cols = set(actual_schema) - set(expected_schema)

    raise ValueError(
        f"Schema Mismatch Error: Source table schema has changed. "
        f"Missing columns: {missing_cols}. "
        f"Unexpected columns: {extra_cols}. "
        f"ETL pipeline expects stable schema. Update mapping or fix source."
    )

def permission_denied_error():
    """Simulates permission/access denied error"""
    raise PermissionError(
        "Access Denied: Service account 'etl-prod-sa@company.iam' does not have "
        "permission to write to GCS bucket 'gs://prod-analytics-warehouse/fact_tables/'. "
        "Required permission: storage.objects.create. Contact DevOps team."
    )

def duplicate_key_error():
    """Simulates primary key constraint violation"""
    raise Exception(
        "psycopg2.IntegrityError: duplicate key value violates unique constraint "
        '"fact_transactions_pkey". Key (transaction_id)=(TXN-2025-12-10-00123) already exists. '
        "Possible duplicate data in source or incremental load logic error."
    )

# DAG Definition
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 10),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # No retries for testing
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': airflow_failure_callback,
}

dag = DAG(
    'prod_etl_failure_test',
    default_args=default_args,
    description='Production-like ETL failure scenarios for RCA testing',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['testing', 'rca', 'etl', 'production-simulation'],
)

# Create tasks for each failure scenario
task_db_connection = PythonOperator(
    task_id='extract_from_database',
    python_callable=database_connection_failure,
    dag=dag,
)

task_s3_missing = PythonOperator(
    task_id='load_from_s3',
    python_callable=s3_file_not_found,
    dag=dag,
)

task_data_quality = PythonOperator(
    task_id='validate_data_quality',
    python_callable=data_quality_validation_failure,
    dag=dag,
)

task_api_timeout = PythonOperator(
    task_id='fetch_external_api',
    python_callable=api_timeout_error,
    dag=dag,
)

task_memory = PythonOperator(
    task_id='transform_large_dataset',
    python_callable=memory_exceeded_error,
    dag=dag,
)

task_schema = PythonOperator(
    task_id='validate_schema',
    python_callable=schema_mismatch_error,
    dag=dag,
)

task_permission = PythonOperator(
    task_id='write_to_warehouse',
    python_callable=permission_denied_error,
    dag=dag,
)

task_duplicate = PythonOperator(
    task_id='insert_to_database',
    python_callable=duplicate_key_error,
    dag=dag,
)

# Set task dependencies (parallel for testing)
# You can trigger individual tasks to test specific failure scenarios
