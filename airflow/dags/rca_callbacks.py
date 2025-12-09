"""
RCA System Integration Callbacks for Airflow

This module provides callback functions to send Airflow task/DAG failures
to the RCA system for automatic root cause analysis and remediation.
"""
import json
import requests
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# ===================================================================
# CONFIGURATION - Update these values for your environment
# ===================================================================

# RCA System webhook endpoint
RCA_WEBHOOK_URL = "http://localhost:8000/airflow-monitor"  # Change to your RCA app URL

# Airflow webserver base URL (for log links)
AIRFLOW_BASE_URL = "http://localhost:8080"  # Change to your Airflow URL

# Timeout for webhook calls
WEBHOOK_TIMEOUT = 10  # seconds


def send_to_rca(context: Dict) -> None:
    """
    Send Airflow task failure to RCA system for analysis and auto-remediation.

    Args:
        context: Airflow task context dictionary containing task instance,
                 execution details, and exception information.

    This function is called automatically when a task fails if configured
    in DAG's default_args or individual task's on_failure_callback.
    """
    try:
        # Extract task information from context
        task_instance = context.get('task_instance')
        exception = context.get('exception')
        dag = context.get('dag')
        dag_run = context.get('dag_run')

        if not task_instance:
            logger.warning("No task_instance in context, skipping RCA notification")
            return

        # Build comprehensive payload for RCA system
        payload = {
            # DAG Information
            "dag_id": dag.dag_id if dag else "Unknown",
            "dag_display_name": dag.description if dag and hasattr(dag, 'description') else None,

            # Task Information
            "task_id": task_instance.task_id,
            "operator": task_instance.operator,

            # Execution Information
            "run_id": dag_run.run_id if dag_run else "Unknown",
            "execution_date": str(context.get('execution_date')),
            "logical_date": str(context.get('logical_date')),
            "data_interval_start": str(context.get('data_interval_start')) if context.get('data_interval_start') else None,
            "data_interval_end": str(context.get('data_interval_end')) if context.get('data_interval_end') else None,

            # Task Instance Details
            "try_number": task_instance.try_number,
            "max_tries": task_instance.max_tries,
            "pool": task_instance.pool,
            "queue": task_instance.queue,
            "state": str(task_instance.state),
            "duration": task_instance.duration,
            "start_date": str(task_instance.start_date) if task_instance.start_date else None,
            "end_date": str(task_instance.end_date) if task_instance.end_date else None,

            # Error Information
            "exception": str(exception) if exception else "No exception details",
            "error": str(exception) if exception else None,
            "exception_type": type(exception).__name__ if exception else None,

            # URLs
            "log_url": task_instance.log_url if hasattr(task_instance, 'log_url') else None,
            "airflow_base_url": AIRFLOW_BASE_URL,

            # Metadata
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": task_instance.hostname if hasattr(task_instance, 'hostname') else None,
            "executor_config": str(task_instance.executor_config) if hasattr(task_instance, 'executor_config') else None,
        }

        # Log the failure notification
        logger.info(
            f"📤 Sending failure notification to RCA system: "
            f"DAG={payload['dag_id']}, Task={payload['task_id']}, "
            f"Run={payload['run_id']}, Try={payload['try_number']}/{payload['max_tries']}"
        )
        logger.debug(f"RCA Payload: {json.dumps(payload, indent=2)}")

        # Send webhook to RCA system
        response = requests.post(
            RCA_WEBHOOK_URL,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Airflow-RCA-Integration/1.0'
            },
            timeout=WEBHOOK_TIMEOUT
        )

        # Handle response
        if response.status_code == 200:
            response_data = response.json() if response.text else {}
            logger.info(
                f"✅ Successfully sent to RCA system. "
                f"Status: {response.status_code}, "
                f"Response: {response_data}"
            )

            # Log ticket ID if returned
            ticket_id = response_data.get('ticket_id')
            if ticket_id:
                logger.info(f"🎫 RCA Ticket created: {ticket_id}")
        else:
            logger.error(
                f"❌ RCA webhook failed. "
                f"Status: {response.status_code}, "
                f"Response: {response.text}"
            )

    except requests.exceptions.Timeout:
        logger.error(f"⏱️  RCA webhook timeout after {WEBHOOK_TIMEOUT}s. URL: {RCA_WEBHOOK_URL}")
    except requests.exceptions.ConnectionError:
        logger.error(f"🔌 Cannot connect to RCA system at {RCA_WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Exception sending to RCA system: {type(e).__name__}: {e}")
        # Don't raise - we don't want RCA integration failure to break the DAG


def on_failure_callback(context: Dict) -> None:
    """
    Standard Airflow failure callback that sends to RCA system.

    Use this in your DAG's default_args or individual task configuration:

    Example 1 - Apply to all tasks in DAG:
        default_args = {
            'owner': 'data-team',
            'on_failure_callback': on_failure_callback,
        }

    Example 2 - Apply to specific task:
        my_task = PythonOperator(
            task_id='process_data',
            python_callable=my_function,
            on_failure_callback=on_failure_callback,
        )

    Args:
        context: Airflow task context (automatically provided)
    """
    send_to_rca(context)


def on_success_callback(context: Dict) -> None:
    """
    Optional: Callback for successful task completion.

    Can be used to notify RCA system of successful remediation retries.

    Args:
        context: Airflow task context (automatically provided)
    """
    task_instance = context.get('task_instance')
    if task_instance and task_instance.try_number > 1:
        # Task succeeded after retry - potentially auto-remediation success
        logger.info(
            f"✅ Task {task_instance.task_id} succeeded after retry "
            f"(attempt {task_instance.try_number})"
        )
        # Optionally send success notification to RCA
        # send_success_to_rca(context)


def on_retry_callback(context: Dict) -> None:
    """
    Optional: Callback when task is retrying.

    Args:
        context: Airflow task context (automatically provided)
    """
    task_instance = context.get('task_instance')
    exception = context.get('exception')

    if task_instance:
        logger.info(
            f"🔄 Task {task_instance.task_id} is retrying "
            f"(attempt {task_instance.try_number}/{task_instance.max_tries}). "
            f"Reason: {exception}"
        )
