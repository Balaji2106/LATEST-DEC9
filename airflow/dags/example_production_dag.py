"""
Example Production DAG with RCA Integration

This demonstrates a realistic data pipeline with RCA monitoring.
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import pandas as pd
from rca_callbacks import on_failure_callback

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['data-team@company.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': on_failure_callback,  # RCA Integration
}

with DAG(
    dag_id='customer_data_etl_pipeline',
    default_args=default_args,
    description='Daily customer data ETL with RCA monitoring',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['production', 'etl', 'customer-data'],
) as dag:

    def extract_customer_data(**context):
        """Extract customer data from source system"""
        print("📥 Extracting customer data from source database...")

        # Simulated extraction
        # In production, this would connect to your actual database
        try:
            # Simulate database connection
            import time
            time.sleep(2)

            # Simulated data extraction
            data = {
                'customer_id': [1, 2, 3, 4, 5],
                'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
                'email': ['alice@example.com', 'bob@example.com',
                         'charlie@example.com', 'diana@example.com', 'eve@example.com'],
                'signup_date': ['2025-01-01'] * 5
            }

            df = pd.DataFrame(data)
            print(f"✅ Extracted {len(df)} customer records")

            # Push to XCom for next task
            context['task_instance'].xcom_push(key='customer_count', value=len(df))

            return len(df)

        except Exception as e:
            raise ConnectionError(f"Failed to extract customer data: {str(e)}")

    def transform_customer_data(**context):
        """Transform and validate customer data"""
        print("🔄 Transforming customer data...")

        # Pull record count from previous task
        record_count = context['task_instance'].xcom_pull(
            task_ids='extract_customer_data',
            key='customer_count'
        )

        print(f"Processing {record_count} records...")

        # Simulated transformation
        import time
        time.sleep(1)

        print("✅ Data transformation completed")
        return record_count

    def load_customer_data(**context):
        """Load customer data to data warehouse"""
        print("📤 Loading customer data to warehouse...")

        # Simulated load operation
        import time
        time.sleep(1)

        print("✅ Data loaded successfully to warehouse")
        return "success"

    def validate_data_quality(**context):
        """Run data quality checks"""
        print("🔍 Running data quality validations...")

        # Simulated validation
        import time
        time.sleep(1)

        # Example validation
        checks_passed = 10
        checks_failed = 0

        if checks_failed > 0:
            raise ValueError(
                f"Data quality validation failed: {checks_failed} checks failed. "
                "Manual review required."
            )

        print(f"✅ All {checks_passed} data quality checks passed")
        return "quality_checks_passed"

    def send_completion_notification(**context):
        """Send completion notification"""
        print("📧 Sending completion notification...")

        # Get metrics from previous tasks
        record_count = context['task_instance'].xcom_pull(
            task_ids='extract_customer_data',
            key='customer_count'
        )

        print(f"✅ Pipeline completed successfully. Processed {record_count} records.")
        return "notification_sent"

    # Define tasks
    extract = PythonOperator(
        task_id='extract_customer_data',
        python_callable=extract_customer_data,
    )

    transform = PythonOperator(
        task_id='transform_customer_data',
        python_callable=transform_customer_data,
    )

    load = PythonOperator(
        task_id='load_customer_data',
        python_callable=load_customer_data,
    )

    validate = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
    )

    notify = PythonOperator(
        task_id='send_completion_notification',
        python_callable=send_completion_notification,
    )

    # Define task dependencies (linear pipeline)
    extract >> transform >> load >> validate >> notify

# DAG documentation
dag.doc_md = """
# Customer Data ETL Pipeline

## Overview
Daily ETL pipeline to extract, transform, and load customer data from operational
database to data warehouse.

## Schedule
- **Frequency**: Daily
- **Time**: 2:00 AM UTC
- **SLA**: 1 hour

## Tasks
1. **extract_customer_data**: Extract from source DB
2. **transform_customer_data**: Clean and transform
3. **load_customer_data**: Load to warehouse
4. **validate_data_quality**: Run quality checks
5. **send_completion_notification**: Notify team

## RCA Integration
All tasks are monitored by the RCA system. If any task fails:
1. Failure sent to RCA system automatically
2. AI analyzes root cause
3. Auto-remediation triggered if applicable
4. Team notified via Slack/email

## Dependencies
- Source Database: PostgreSQL
- Target Warehouse: Snowflake/Redshift
- RCA System: Auto-remediation enabled

## Contacts
- Owner: Data Engineering Team
- On-Call: data-oncall@company.com
"""
