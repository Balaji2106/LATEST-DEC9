"""
Databricks Cluster Failure Detection and Classification

This module analyzes job/cluster failures to:
1. Detect if failure is cluster-related
2. Classify cluster error types
3. Provide remediation hints
"""
import logging
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("cluster_failure_detector")


@dataclass
class ClusterFailureAnalysis:
    """Result of cluster failure analysis"""
    is_cluster_failure: bool
    error_category: Optional[str] = None
    termination_code: Optional[str] = None
    severity: str = "Medium"
    is_remediable: bool = False
    typical_cause: Optional[str] = None
    remediation_hint: Optional[str] = None
    confidence: float = 0.0  # 0.0 to 1.0


# ============================================================================
# CLUSTER ERROR TAXONOMY
# ============================================================================

CLUSTER_ERROR_CATEGORIES = {
    # Infrastructure/Cloud Provider Errors
    "DRIVER_UNREACHABLE": {
        "category": "InfrastructureFailure",
        "severity": "High",
        "remediable": True,
        "typical_cause": "Cloud provider issue or network connectivity problem",
        "remediation_hint": "Retry cluster start or switch to on-demand instances",
        "keywords": ["driver.*unreachable", "driver.*not.*responding", "driver.*failed.*start",
                     "DRIVER_UNREACHABLE", "DRIVER_UNRESPONSIVE"],
    },

    "CLOUD_PROVIDER_SHUTDOWN": {
        "category": "SpotInstancePreemption",
        "severity": "Medium",
        "remediable": True,
        "typical_cause": "Spot/preemptible instance reclaimed by cloud provider",
        "remediation_hint": "Use on-demand instances or retry with spot instances",
        "keywords": ["spot.*instance.*terminated", "preempt", "cloud.*provider.*shutdown",
                     "CLOUD_PROVIDER_SHUTDOWN", "instance.*reclaim", "infrastructure.*issue",
                     "cloud.*infrastructure"],
    },

    "CLOUD_PROVIDER_LAUNCH_FAILURE": {
        "category": "InfrastructureFailure",
        "severity": "High",
        "remediable": True,
        "typical_cause": "Cloud provider unable to provision requested resources",
        "remediation_hint": "Retry or use different instance type/region",
        "keywords": ["launch.*failure", "provisioning.*failed", "instance.*launch.*failed",
                     "CLOUD_PROVIDER_LAUNCH_FAILURE", "capacity.*unavailable",
                     "failed.*to.*provision", "cloud.*provider.*failed"],
    },

    # Resource Exhaustion
    "OUT_OF_MEMORY": {
        "category": "ResourceExhaustion",
        "severity": "High",
        "remediable": True,
        "typical_cause": "Driver or executor ran out of memory",
        "remediation_hint": "Increase driver/executor memory or use larger instance type",
        "keywords": ["out.*of.*memory", "OutOfMemoryError", "OOM", "java.lang.OutOfMemoryError",
                     "memory.*limit.*exceeded", "heap.*space"],
    },

    "OUT_OF_DISK": {
        "category": "ResourceExhaustion",
        "severity": "High",
        "remediable": True,
        "typical_cause": "Cluster ran out of disk space",
        "remediation_hint": "Clear temp files, increase disk size, or enable auto-scaling",
        "keywords": ["out.*of.*disk", "disk.*full", "no.*space.*left", "disk.*quota.*exceeded"],
    },

    # Configuration Errors
    "INIT_SCRIPT_FAILURE": {
        "category": "ConfigurationError",
        "severity": "High",
        "remediable": True,
        "typical_cause": "Cluster initialization script failed",
        "remediation_hint": "Check init script logs, fix script errors, or remove problematic init script",
        "keywords": ["init.*script.*fail", "initialization.*fail", "bootstrap.*fail",
                     "INIT_SCRIPT_FAILURE", "cluster.*init.*fail", "init.*script.*exit",
                     "script.*exited.*with.*code"],
    },

    "LIBRARY_INSTALLATION_FAILURE": {
        "category": "ConfigurationError",
        "severity": "Medium",
        "remediable": True,
        "typical_cause": "Failed to install required libraries on cluster",
        "remediation_hint": "Check library compatibility, fix dependencies, or use cluster pools with pre-installed libraries",
        "keywords": ["library.*install.*fail", "package.*install.*fail", "pip.*install.*fail",
                     "maven.*fail", "dependency.*resolution.*fail"],
    },

    "INVALID_CLUSTER_CONFIG": {
        "category": "ConfigurationError",
        "severity": "High",
        "remediable": True,
        "typical_cause": "Invalid cluster configuration (Spark conf, instance type, etc)",
        "remediation_hint": "Review and fix cluster configuration settings",
        "keywords": ["invalid.*configuration", "invalid.*spark.*conf", "unsupported.*instance.*type",
                     "invalid.*runtime.*version"],
    },

    # Network Issues
    "NETWORK_FAILURE": {
        "category": "NetworkError",
        "severity": "Medium",
        "remediable": True,
        "typical_cause": "Network connectivity issues between driver and executors",
        "remediation_hint": "Check VPC/network settings, retry cluster start",
        "keywords": ["network.*timeout", "connection.*refused", "network.*unreachable",
                     "heartbeat.*timeout", "rpc.*timeout"],
    },

    # Permission Issues
    "PERMISSION_DENIED": {
        "category": "PermissionError",
        "severity": "High",
        "remediable": True,
        "typical_cause": "Insufficient permissions to access resources (storage, secrets, etc)",
        "remediation_hint": "Grant required permissions to cluster service principal/identity",
        "keywords": ["permission.*denied", "access.*denied", "unauthorized", "forbidden",
                     "insufficient.*permission"],
    },

    # Timeouts
    "CLUSTER_START_TIMEOUT": {
        "category": "TimeoutError",
        "severity": "Medium",
        "remediable": True,
        "typical_cause": "Cluster took too long to start (init scripts, large libraries)",
        "remediation_hint": "Optimize init scripts, use cluster pools, or increase timeout",
        "keywords": ["cluster.*start.*timeout", "startup.*timeout", "cluster.*creation.*timeout",
                     "cluster.*startup.*timed.*out", "timed.*out.*after.*minutes"],
    },

    "IDLE_TIMEOUT": {
        "category": "NormalTermination",
        "severity": "Low",
        "remediable": False,
        "typical_cause": "Cluster auto-terminated due to inactivity (expected behavior)",
        "remediation_hint": "No action needed - normal auto-termination",
        "keywords": ["inactivity", "idle.*timeout", "auto.*terminat.*idle"],
    },

    # Generic Cluster Failures
    "CLUSTER_TERMINATION_UNKNOWN": {
        "category": "UnknownClusterFailure",
        "severity": "High",
        "remediable": False,
        "typical_cause": "Cluster terminated for unknown reason",
        "remediation_hint": "Check cluster event logs and Databricks support logs",
        "keywords": ["cluster.*terminat", "cluster.*shut.*down", "cluster.*fail"],
    },
}


# ============================================================================
# DETECTION FUNCTIONS
# ============================================================================

def is_cluster_related_error(error_message: str, run_details: Optional[Dict] = None) -> ClusterFailureAnalysis:
    """
    Analyze if job/task failure is caused by cluster issues.

    Args:
        error_message: Error message from job failure
        run_details: Optional full run details from Databricks API

    Returns:
        ClusterFailureAnalysis with detection results
    """
    if not error_message:
        return ClusterFailureAnalysis(
            is_cluster_failure=False,
            confidence=0.0
        )

    error_message_lower = error_message.lower()

    # Check against all known cluster error patterns
    for error_code, config in CLUSTER_ERROR_CATEGORIES.items():
        keywords = config.get("keywords", [])

        for pattern in keywords:
            if re.search(pattern, error_message_lower, re.IGNORECASE):
                logger.info(f"🎯 Cluster failure detected: {error_code} (matched pattern: '{pattern}')")

                return ClusterFailureAnalysis(
                    is_cluster_failure=True,
                    error_category=config["category"],
                    termination_code=error_code,
                    severity=config["severity"],
                    is_remediable=config["remediable"],
                    typical_cause=config["typical_cause"],
                    remediation_hint=config["remediation_hint"],
                    confidence=0.9  # High confidence from pattern match
                )

    # Check run_details for cluster-specific fields
    if run_details:
        # Check if termination_reason exists (strong signal of cluster issue)
        state = run_details.get("state", {})
        termination_reason = state.get("termination_reason") or run_details.get("termination_reason")

        if termination_reason:
            code = termination_reason.get("code", "").upper()
            term_type = termination_reason.get("type", "").upper()

            if code and code in CLUSTER_ERROR_CATEGORIES:
                config = CLUSTER_ERROR_CATEGORIES[code]
                logger.info(f"🎯 Cluster failure detected from termination_reason: {code}")

                return ClusterFailureAnalysis(
                    is_cluster_failure=True,
                    error_category=config["category"],
                    termination_code=code,
                    severity=config["severity"],
                    is_remediable=config["remediable"],
                    typical_cause=config["typical_cause"],
                    remediation_hint=config["remediation_hint"],
                    confidence=1.0  # Highest confidence from API field
                )

            # Check if type indicates cluster failure
            if "cloud" in term_type.lower() or "infrastructure" in term_type.lower():
                logger.info(f"🎯 Cluster failure detected from termination_type: {term_type}")
                return ClusterFailureAnalysis(
                    is_cluster_failure=True,
                    error_category="InfrastructureFailure",
                    termination_code=code or "UNKNOWN",
                    severity="High",
                    is_remediable=True,
                    typical_cause=f"Cloud/Infrastructure issue: {term_type}",
                    remediation_hint="Retry cluster start or check cloud provider status",
                    confidence=0.85
                )

        # Check cluster_instance state
        cluster_instance = run_details.get("cluster_instance", {})
        if cluster_instance:
            cluster_state = cluster_instance.get("state")
            if cluster_state in ["TERMINATING", "TERMINATED", "ERROR", "UNKNOWN"]:
                logger.info(f"🎯 Cluster failure suspected from cluster state: {cluster_state}")
                return ClusterFailureAnalysis(
                    is_cluster_failure=True,
                    error_category="ClusterStateError",
                    severity="High",
                    is_remediable=True,
                    typical_cause=f"Cluster in {cluster_state} state",
                    remediation_hint="Check cluster health and restart if needed",
                    confidence=0.7
                )

    # No cluster failure detected
    logger.info("ℹ️  No cluster failure patterns detected - likely application/code error")
    return ClusterFailureAnalysis(
        is_cluster_failure=False,
        confidence=0.8  # Confident it's NOT a cluster issue
    )


def extract_cluster_context_from_error(error_message: str, run_details: Optional[Dict] = None) -> Dict:
    """
    Extract cluster-related context from error message and run details.

    Returns:
        Dictionary with cluster context for RCA
    """
    analysis = is_cluster_related_error(error_message, run_details)

    context = {
        "is_cluster_failure": analysis.is_cluster_failure,
        "error_category": analysis.error_category,
        "termination_code": analysis.termination_code,
        "severity": analysis.severity,
        "is_remediable": analysis.is_remediable,
        "typical_cause": analysis.typical_cause,
        "remediation_hint": analysis.remediation_hint,
        "detection_confidence": analysis.confidence,
    }

    # Add cluster details from run_details if available
    if run_details:
        cluster_instance = run_details.get("cluster_instance", {})
        cluster_spec = run_details.get("cluster_spec", {})

        context.update({
            "cluster_id": cluster_instance.get("cluster_id"),
            "cluster_state": cluster_instance.get("state"),
            "driver_node_type": cluster_spec.get("driver_node_type_id"),
            "worker_node_type": cluster_spec.get("node_type_id"),
            "num_workers": cluster_spec.get("num_workers"),
            "autoscale": cluster_spec.get("autoscale"),
            "spark_version": cluster_spec.get("spark_version"),
        })

    return context


def get_cluster_error_summary(analysis: ClusterFailureAnalysis) -> str:
    """
    Generate human-readable summary of cluster error.

    Args:
        analysis: ClusterFailureAnalysis result

    Returns:
        Formatted summary string
    """
    if not analysis.is_cluster_failure:
        return "Not a cluster failure - likely application or data error"

    summary = f"""
🔴 CLUSTER FAILURE DETECTED

Error Type: {analysis.termination_code or 'UNKNOWN'}
Category: {analysis.error_category}
Severity: {analysis.severity}
Remediable: {'Yes' if analysis.is_remediable else 'No'}

Typical Cause:
{analysis.typical_cause or 'Unknown'}

Recommended Action:
{analysis.remediation_hint or 'Manual investigation required'}

Confidence: {analysis.confidence * 100:.0f}%
"""
    return summary.strip()


# ============================================================================
# TESTING FUNCTIONS
# ============================================================================

def test_cluster_detection():
    """Test cluster failure detection with sample error messages"""
    test_cases = [
        "Driver not responding after 300 seconds",
        "OutOfMemoryError: Java heap space exceeded",
        "Cloud provider shutdown - spot instance preempted",
        "Init script failed with exit code 1",
        "Library installation failed: package numpy==1.19.0 not found",
        "Network timeout connecting to executor 192.168.1.5",
        "Permission denied: Unable to access s3://bucket/data/",
        "KeyError: 'column_name' not found in DataFrame",  # NOT cluster error
        "Division by zero in transformation",  # NOT cluster error
    ]

    print("=" * 80)
    print("CLUSTER FAILURE DETECTION TEST")
    print("=" * 80)

    for i, error_msg in enumerate(test_cases, 1):
        print(f"\n{i}. Error: {error_msg}")
        analysis = is_cluster_related_error(error_msg)

        if analysis.is_cluster_failure:
            print(f"   ✅ CLUSTER FAILURE: {analysis.error_category}")
            print(f"   Code: {analysis.termination_code}")
            print(f"   Severity: {analysis.severity}")
            print(f"   Hint: {analysis.remediation_hint}")
        else:
            print(f"   ℹ️  NOT A CLUSTER FAILURE")

        print(f"   Confidence: {analysis.confidence * 100:.0f}%")


if __name__ == "__main__":
    # Run tests
    test_cluster_detection()
