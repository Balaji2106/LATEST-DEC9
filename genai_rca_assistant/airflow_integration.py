"""
Airflow Integration Module

Handles Airflow DAG/task failure webhooks and auto-remediation
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger("airflow_integration")


# ============================================================================
# AIRFLOW ERROR CLASSIFICATION
# ============================================================================

AIRFLOW_REMEDIABLE_ERRORS = {
    # Connection/Network Errors
    "ConnectionError": {
        "action": "retry_task",
        "max_retries": 3,
        "backoff_seconds": [30, 60, 120],
        "category": "NetworkError",
        "severity": "Medium",
        "typical_cause": "Network connectivity issue or service unavailable",
        "keywords": ["connection.*error", "connection.*refused", "connection.*timeout",
                     "unable.*to.*connect", "network.*unreachable"]
    },

    "TimeoutError": {
        "action": "retry_task_with_extended_timeout",
        "max_retries": 2,
        "backoff_seconds": [60, 120],
        "category": "TimeoutError",
        "severity": "Medium",
        "typical_cause": "Task execution exceeded timeout limit",
        "keywords": ["timeout", "timed.*out", "execution.*timeout", "task.*timeout"]
    },

    # Resource Errors
    "OutOfMemory": {
        "action": "retry_with_more_resources",
        "max_retries": 2,
        "backoff_seconds": [60, 120],
        "category": "ResourceExhaustion",
        "severity": "High",
        "typical_cause": "Task ran out of memory",
        "keywords": ["out.*of.*memory", "OutOfMemoryError", "memory.*error", "OOM"]
    },

    # Dependency Errors
    "SensorTimeout": {
        "action": "check_upstream_and_retry",
        "max_retries": 2,
        "backoff_seconds": [300, 600],  # Longer backoff for sensors
        "category": "DependencyError",
        "severity": "Medium",
        "typical_cause": "Sensor timed out waiting for upstream dependency",
        "keywords": ["sensor.*timeout", "sensor.*fail", "waiting.*for.*file", "waiting.*for.*data"]
    },

    # Data Errors
    "FileNotFound": {
        "action": "check_upstream_and_retry",
        "max_retries": 2,
        "backoff_seconds": [60, 120],
        "category": "DataError",
        "severity": "Medium",
        "typical_cause": "Expected input file not found",
        "keywords": ["file.*not.*found", "no.*such.*file", "path.*does.*not.*exist"]
    },

    # API/External Service Errors
    "APIError": {
        "action": "retry_task",
        "max_retries": 3,
        "backoff_seconds": [30, 60, 120],
        "category": "ExternalServiceError",
        "severity": "Medium",
        "typical_cause": "External API returned error or unavailable",
        "keywords": ["API.*error", "API.*failed", "service.*unavailable", "503.*error", "502.*error"]
    },

    # Authentication Errors
    "AuthenticationError": {
        "action": "check_credentials",
        "max_retries": 0,  # Don't retry auth errors
        "backoff_seconds": [],
        "category": "AuthenticationError",
        "severity": "High",
        "typical_cause": "Invalid or expired credentials",
        "keywords": ["authentication.*failed", "invalid.*credentials", "unauthorized", "401.*error", "403.*error"]
    },

    # Database Errors
    "DatabaseError": {
        "action": "retry_task",
        "max_retries": 3,
        "backoff_seconds": [30, 60, 120],
        "category": "DatabaseError",
        "severity": "High",
        "typical_cause": "Database connection or query error",
        "keywords": ["database.*error", "connection.*pool.*exhausted", "deadlock", "lock.*timeout"]
    },

    # Databricks Errors (when running Databricks jobs from Airflow)
    "DatabricksSubmitRunError": {
        "action": "retry_databricks_job",
        "max_retries": 2,
        "backoff_seconds": [60, 120],
        "category": "DatabricksError",
        "severity": "High",
        "typical_cause": "Databricks job submission or execution failed",
        "keywords": ["databricks.*error", "databricks.*submit.*failed", "databricks.*run.*failed",
                     "cluster.*start.*failed"]
    },
}


def classify_airflow_error(error_message: str) -> Optional[Dict]:
    """
    Classify Airflow error and determine if it's remediable.

    Args:
        error_message: Error message from Airflow task failure

    Returns:
        Dictionary with error classification and remediation info, or None
    """
    import re

    if not error_message:
        return None

    error_lower = error_message.lower()

    # Check against known error patterns
    for error_type, config in AIRFLOW_REMEDIABLE_ERRORS.items():
        keywords = config.get("keywords", [])

        for pattern in keywords:
            if re.search(pattern, error_lower, re.IGNORECASE):
                logger.info(f"🎯 Airflow error classified: {error_type} (matched pattern: '{pattern}')")

                return {
                    "error_type": error_type,
                    "action": config["action"],
                    "max_retries": config["max_retries"],
                    "backoff_seconds": config["backoff_seconds"],
                    "category": config["category"],
                    "severity": config["severity"],
                    "typical_cause": config["typical_cause"],
                    "is_remediable": config["max_retries"] > 0
                }

    # No match found
    logger.info("ℹ️  Airflow error not classified - likely application-specific error")
    return None


def get_airflow_log_url(airflow_base_url: str, dag_id: str, run_id: str, task_id: str, try_number: int = 1) -> str:
    """
    Generate Airflow task log URL.

    Args:
        airflow_base_url: Base URL of Airflow webserver
        dag_id: DAG ID
        run_id: DAG run ID
        task_id: Task ID
        try_number: Task try number

    Returns:
        URL to task logs in Airflow UI
    """
    # Airflow 2.x format
    return f"{airflow_base_url}/dags/{dag_id}/grid?dag_run_id={run_id}&task_id={task_id}&tab=logs&try_number={try_number}"


def get_airflow_dag_url(airflow_base_url: str, dag_id: str) -> str:
    """
    Generate Airflow DAG URL.

    Args:
        airflow_base_url: Base URL of Airflow webserver
        dag_id: DAG ID

    Returns:
        URL to DAG in Airflow UI
    """
    return f"{airflow_base_url}/dags/{dag_id}/grid"


# ============================================================================
# AIRFLOW-SPECIFIC REMEDIATION LOGIC
# ============================================================================

def should_retry_airflow_task(error_classification: Dict, current_try: int) -> bool:
    """
    Determine if Airflow task should be retried based on error classification.

    Args:
        error_classification: Result from classify_airflow_error()
        current_try: Current try number from Airflow

    Returns:
        True if task should be retried, False otherwise
    """
    if not error_classification or not error_classification.get("is_remediable"):
        return False

    max_retries = error_classification.get("max_retries", 0)

    # Check if we've exceeded max retries
    if current_try >= max_retries:
        logger.info(f"Max retries ({max_retries}) reached for this error type")
        return False

    return True


def build_airflow_context_for_rca(payload: Dict, error_classification: Optional[Dict] = None) -> str:
    """
    Build enriched error context for AI RCA.

    Args:
        payload: Airflow webhook payload
        error_classification: Optional error classification result

    Returns:
        Enriched error message with Airflow context
    """
    dag_id = payload.get("dag_id", "Unknown")
    task_id = payload.get("task_id", "Unknown")
    run_id = payload.get("run_id", "Unknown")
    operator = payload.get("operator", "Unknown")
    try_number = payload.get("try_number", 1)
    max_tries = payload.get("max_tries", 1)
    exception = payload.get("exception", "No exception details")

    context = f"""
🔴 AIRFLOW TASK FAILURE DETECTED

DAG Information:
- DAG ID: {dag_id}
- Task ID: {task_id}
- Run ID: {run_id}
- Operator: {operator}
- Try Number: {try_number}/{max_tries}

Error Details:
{exception}
"""

    if error_classification:
        context += f"""
Error Classification:
- Type: {error_classification.get('error_type')}
- Category: {error_classification.get('category')}
- Severity: {error_classification.get('severity')}
- Typical Cause: {error_classification.get('typical_cause')}
- Remediable: {'Yes' if error_classification.get('is_remediable') else 'No'}
- Suggested Action: {error_classification.get('action')}
"""

    # Add log URL if available
    log_url = payload.get("log_url")
    if log_url:
        context += f"\nTask Logs: {log_url}\n"

    return context
