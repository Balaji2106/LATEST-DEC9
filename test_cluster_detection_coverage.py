#!/usr/bin/env python3
"""
Test script to verify cluster failure detection coverage
Tests all infrastructure, start, and termination failure scenarios
"""
import sys
sys.path.insert(0, '/home/user/LATEST-DEC9/genai_rca_assistant')

from cluster_failure_detector import is_cluster_related_error

def test_failure_scenarios():
    """Test all cluster failure scenarios"""

    test_cases = {
        "CLUSTER START FAILURES": [
            ("Driver failed to start", "DRIVER_UNREACHABLE"),
            ("Cloud provider failed to provision instance", "CLOUD_PROVIDER_LAUNCH_FAILURE"),
            ("Cluster startup timed out after 30 minutes", "CLUSTER_START_TIMEOUT"),
            ("Init script exited with code 1", "INIT_SCRIPT_FAILURE"),
            ("Unable to launch cluster: capacity unavailable in region", "CLOUD_PROVIDER_LAUNCH_FAILURE"),
            ("Cluster initialization failed during bootstrap", "INIT_SCRIPT_FAILURE"),
        ],

        "UNEXPECTED TERMINATION FAILURES": [
            ("Cluster terminated unexpectedly", "CLUSTER_TERMINATION_UNKNOWN"),
            ("Spot instance preempted by cloud provider", "CLOUD_PROVIDER_SHUTDOWN"),
            ("Driver became unreachable during job execution", "DRIVER_UNREACHABLE"),
            ("Cloud provider shutdown the instance", "CLOUD_PROVIDER_SHUTDOWN"),
            ("Instance reclaimed by cloud provider", "CLOUD_PROVIDER_SHUTDOWN"),
        ],

        "INFRASTRUCTURE FAILURES": [
            ("Driver not responding after 300 seconds", "DRIVER_UNREACHABLE"),
            ("Network timeout connecting to executor", "NETWORK_FAILURE"),
            ("RPC timeout during task execution", "NETWORK_FAILURE"),
            ("Heartbeat timeout from executor", "NETWORK_FAILURE"),
            ("Cloud provider infrastructure issue", "CLOUD_PROVIDER_SHUTDOWN"),
        ],

        "RESOURCE EXHAUSTION": [
            ("OutOfMemoryError: Java heap space", "OUT_OF_MEMORY"),
            ("java.lang.OutOfMemoryError: GC overhead limit exceeded", "OUT_OF_MEMORY"),
            ("Disk quota exceeded on /databricks/driver", "OUT_OF_DISK"),
            ("No space left on device", "OUT_OF_DISK"),
        ],

        "CONFIGURATION ERRORS": [
            ("Invalid Spark configuration: spark.driver.memory=invalid", "INVALID_CLUSTER_CONFIG"),
            ("Library installation failed: package not found", "LIBRARY_INSTALLATION_FAILURE"),
            ("pip install failed: dependency conflict", "LIBRARY_INSTALLATION_FAILURE"),
            ("Init script failed with exit code 127", "INIT_SCRIPT_FAILURE"),
        ],

        "PERMISSION ERRORS": [
            ("Permission denied: Unable to access s3://bucket/data/", "PERMISSION_DENIED"),
            ("Access denied to Azure Storage account", "PERMISSION_DENIED"),
            ("Forbidden: Insufficient permissions", "PERMISSION_DENIED"),
            ("Unauthorized access to secrets", "PERMISSION_DENIED"),
        ],
    }

    print("=" * 100)
    print("CLUSTER FAILURE DETECTION COVERAGE TEST")
    print("=" * 100)

    total_tests = 0
    detected = 0

    for category, cases in test_cases.items():
        print(f"\n{'=' * 100}")
        print(f"📂 {category}")
        print('=' * 100)

        for error_msg, expected_code in cases:
            total_tests += 1
            analysis = is_cluster_related_error(error_msg)

            if analysis.is_cluster_failure:
                detected += 1
                status = "✅ DETECTED"
                actual_code = analysis.termination_code
                confidence = f"{analysis.confidence * 100:.0f}%"

                # Check if detected code matches expected
                if actual_code == expected_code:
                    match_status = "✓ CORRECT"
                else:
                    match_status = f"⚠ Got {actual_code}, Expected {expected_code}"
            else:
                status = "❌ MISSED"
                actual_code = "N/A"
                confidence = "N/A"
                match_status = "✗ FAILED"

            print(f"\n{total_tests}. Error: {error_msg[:70]}")
            print(f"   {status}")
            if analysis.is_cluster_failure:
                print(f"   Code: {actual_code}")
                print(f"   Category: {analysis.error_category}")
                print(f"   Confidence: {confidence}")
                print(f"   {match_status}")

    print("\n" + "=" * 100)
    print(f"📊 DETECTION SUMMARY")
    print("=" * 100)
    print(f"Total Test Cases: {total_tests}")
    print(f"Detected: {detected}")
    print(f"Missed: {total_tests - detected}")
    print(f"Detection Rate: {(detected/total_tests)*100:.1f}%")
    print("=" * 100)

    # Test with API termination reason (100% confidence)
    print("\n" + "=" * 100)
    print("🔬 TESTING API TERMINATION REASON DETECTION (100% Confidence)")
    print("=" * 100)

    api_test_cases = [
        {
            "error": "Generic error message",
            "run_details": {
                "state": {
                    "termination_reason": {
                        "code": "DRIVER_UNREACHABLE",
                        "type": "CLOUD_FAILURE"
                    }
                }
            },
            "expected": "DRIVER_UNREACHABLE"
        },
        {
            "error": "Job failed",
            "run_details": {
                "state": {
                    "termination_reason": {
                        "code": "CLOUD_PROVIDER_SHUTDOWN",
                        "type": "CLOUD_FAILURE"
                    }
                }
            },
            "expected": "CLOUD_PROVIDER_SHUTDOWN"
        }
    ]

    for i, test_case in enumerate(api_test_cases, 1):
        analysis = is_cluster_related_error(test_case["error"], test_case["run_details"])

        print(f"\n{i}. API Termination Code: {test_case['expected']}")
        print(f"   Detection: {'✅ DETECTED' if analysis.is_cluster_failure else '❌ MISSED'}")
        print(f"   Detected Code: {analysis.termination_code}")
        print(f"   Confidence: {analysis.confidence * 100:.0f}%")
        print(f"   Status: {'✓ CORRECT' if analysis.termination_code == test_case['expected'] else '✗ WRONG'}")

if __name__ == "__main__":
    test_failure_scenarios()
