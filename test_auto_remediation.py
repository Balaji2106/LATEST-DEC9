#!/usr/bin/env python3
"""
Test script for AI-driven auto-remediation
Simulates ADF and Databricks failures and sends them to the RCA system
"""

import requests
import json
import time
from datetime import datetime, timezone

# Configuration
RCA_BASE_URL = "http://localhost:8000"
RCA_API_KEY = "balaji-rca-secret-2025"

# Test scenarios
TEST_SCENARIOS = {
    "adf_network_timeout": {
        "endpoint": f"{RCA_BASE_URL}/adf-monitor",
        "payload": {
            "pipelineName": "load_customer_data_pipeline",
            "runId": f"test-run-{int(time.time())}",
            "status": "Failed",
            "errorCode": "NetworkTimeout",
            "errorMessage": "Connection to SQL database timed out after 30 seconds. Endpoint: myserver.database.windows.net:1433",
            "startTime": datetime.now(timezone.utc).isoformat(),
            "endTime": datetime.now(timezone.utc).isoformat(),
            "dataFactoryName": "test-adf-instance"
        },
        "expected_ai_decision": {
            "is_auto_remediable": True,
            "remediation_action": "retry_pipeline",
            "remediation_risk": "Low"
        }
    },

    "adf_throttling": {
        "endpoint": f"{RCA_BASE_URL}/adf-monitor",
        "payload": {
            "pipelineName": "process_transactions_pipeline",
            "runId": f"test-run-{int(time.time()) + 1}",
            "status": "Failed",
            "errorCode": "ThrottlingError",
            "errorMessage": "Request throttled by Azure service. Rate limit exceeded (429 Too Many Requests)",
            "startTime": datetime.now(timezone.utc).isoformat(),
            "endTime": datetime.now(timezone.utc).isoformat(),
            "dataFactoryName": "test-adf-instance"
        },
        "expected_ai_decision": {
            "is_auto_remediable": True,
            "remediation_action": "retry_pipeline",
            "remediation_risk": "Low"
        }
    },

    "databricks_driver_unreachable": {
        "endpoint": f"{RCA_BASE_URL}/databricks-monitor",
        "payload": {
            "job_name": "daily_etl_job",
            "job_id": "12345",
            "run_id": f"test-dbx-run-{int(time.time())}",
            "cluster_id": "test-cluster-001",
            "status": "FAILED",
            "error_message": "DRIVER_UNREACHABLE: Cannot reach Spark driver after multiple connection attempts",
            "start_time": int(time.time() * 1000),
            "end_time": int(time.time() * 1000),
            "cluster_details": {
                "cluster_name": "test-cluster",
                "spark_version": "11.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2"
            }
        },
        "expected_ai_decision": {
            "is_auto_remediable": True,
            "remediation_action": "restart_cluster",
            "remediation_risk": "Medium"
        }
    },

    "databricks_out_of_memory": {
        "endpoint": f"{RCA_BASE_URL}/databricks-monitor",
        "payload": {
            "job_name": "large_aggregation_job",
            "job_id": "67890",
            "run_id": f"test-dbx-run-{int(time.time()) + 2}",
            "cluster_id": "test-cluster-002",
            "status": "FAILED",
            "error_message": "OUT_OF_MEMORY: Container killed due to exceeding memory limits. Task attempted to allocate 15GB but only 8GB available.",
            "start_time": int(time.time() * 1000),
            "end_time": int(time.time() * 1000),
            "cluster_details": {
                "cluster_name": "test-cluster-small",
                "spark_version": "11.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2"
            }
        },
        "expected_ai_decision": {
            "is_auto_remediable": True,
            "remediation_action": "restart_cluster",
            "remediation_risk": "Medium"
        }
    },

    "databricks_library_install_failed": {
        "endpoint": f"{RCA_BASE_URL}/databricks-monitor",
        "payload": {
            "job_name": "ml_training_job",
            "job_id": "11111",
            "run_id": f"test-dbx-run-{int(time.time()) + 3}",
            "cluster_id": "test-cluster-003",
            "status": "FAILED",
            "error_message": "LIBRARY_INSTALLATION_FAILURE: Failed to install library 'scikit-learn==1.2.0'. Could not find a version matching requirement.",
            "start_time": int(time.time() * 1000),
            "end_time": int(time.time() * 1000),
            "cluster_details": {
                "cluster_name": "test-ml-cluster",
                "spark_version": "11.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2"
            }
        },
        "expected_ai_decision": {
            "is_auto_remediable": True,
            "remediation_action": "reinstall_libraries",
            "remediation_risk": "Medium"
        }
    },

    "adf_schema_mismatch": {
        "endpoint": f"{RCA_BASE_URL}/adf-monitor",
        "payload": {
            "pipelineName": "load_sales_data_pipeline",
            "runId": f"test-run-{int(time.time()) + 4}",
            "status": "Failed",
            "errorCode": "SchemaMismatch",
            "errorMessage": "Schema validation failed: Expected column 'customer_id' (INTEGER) but found VARCHAR. Source file structure changed.",
            "startTime": datetime.now(timezone.utc).isoformat(),
            "endTime": datetime.now(timezone.utc).isoformat(),
            "dataFactoryName": "test-adf-instance"
        },
        "expected_ai_decision": {
            "is_auto_remediable": False,
            "remediation_action": "manual_intervention",
            "remediation_risk": "High"
        }
    }
}


def send_webhook(scenario_name, scenario_data):
    """Send webhook to RCA system and analyze response"""

    print(f"\n{'='*80}")
    print(f"🧪 TEST SCENARIO: {scenario_name}")
    print(f"{'='*80}")

    endpoint = scenario_data["endpoint"]
    payload = scenario_data["payload"]
    expected = scenario_data["expected_ai_decision"]

    print(f"\n📤 Sending webhook to: {endpoint}")
    print(f"📋 Payload:")
    print(json.dumps(payload, indent=2))

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": RCA_API_KEY
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)

        print(f"\n📥 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"\n📊 Response:")
            print(json.dumps(result, indent=2))

            ticket_id = result.get("ticket_id")
            if ticket_id:
                print(f"\n🎫 Ticket Created: {ticket_id}")

                # Wait a moment for AI analysis
                print("\n⏳ Waiting 3 seconds for AI analysis...")
                time.sleep(3)

                # Fetch ticket details to see AI decision
                ticket_response = requests.get(
                    f"{RCA_BASE_URL}/api/tickets/{ticket_id}",
                    headers=headers
                )

                if ticket_response.status_code == 200:
                    ticket_data = ticket_response.json().get("ticket", {})
                    rca_result = ticket_data.get("rca_result")

                    if rca_result:
                        if isinstance(rca_result, str):
                            try:
                                rca = json.loads(rca_result)
                            except:
                                rca = {}
                        else:
                            rca = rca_result

                        print(f"\n🤖 AI DECISION:")
                        print(f"   Auto-remediable: {rca.get('is_auto_remediable')}")
                        print(f"   Action: {rca.get('remediation_action')}")
                        print(f"   Risk: {rca.get('remediation_risk')}")
                        print(f"   Requires Approval: {rca.get('requires_human_approval')}")
                        print(f"   Business Impact: {rca.get('business_impact')}")

                        print(f"\n✅ EXPECTED:")
                        print(f"   Auto-remediable: {expected['is_auto_remediable']}")
                        print(f"   Action: {expected['remediation_action']}")
                        print(f"   Risk: {expected['remediation_risk']}")

                        # Verify expectations
                        matches = (
                            rca.get('is_auto_remediable') == expected['is_auto_remediable'] and
                            rca.get('remediation_action') == expected['remediation_action']
                        )

                        if matches:
                            print(f"\n✅ TEST PASSED: AI decision matches expectations")
                        else:
                            print(f"\n⚠️  TEST WARNING: AI decision differs from expectations")
                            print(f"   This may be acceptable if AI reasoning is sound")

                        print(f"\n💡 Root Cause:")
                        print(f"   {rca.get('root_cause', 'N/A')}")

                        recommendations = rca.get('recommendations', [])
                        if recommendations:
                            print(f"\n📝 Recommendations:")
                            for i, rec in enumerate(recommendations, 1):
                                print(f"   {i}. {rec}")

                        # Check remediation status
                        remediation_status = ticket_data.get("remediation_status")
                        if remediation_status:
                            print(f"\n🔄 Remediation Status: {remediation_status}")

        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print(f"\n❌ CONNECTION ERROR: Could not connect to RCA system at {RCA_BASE_URL}")
        print(f"   Make sure the RCA application is running:")
        print(f"   cd genai_rca_assistant && python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")

    print(f"\n{'='*80}\n")


def main():
    """Run all test scenarios"""

    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              🧪 AI-Driven Auto-Remediation Test Suite                        ║
║                                                                              ║
║  This script simulates real failures and tests the AI-driven remediation    ║
║  decision-making process.                                                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

RCA System: {RCA_BASE_URL}
API Key: {RCA_API_KEY[:20]}...

Test Scenarios:
  1. ADF Network Timeout (Expected: Auto-remediable)
  2. ADF Throttling Error (Expected: Auto-remediable)
  3. Databricks Driver Unreachable (Expected: Auto-remediable)
  4. Databricks Out of Memory (Expected: Auto-remediable)
  5. Databricks Library Install Failed (Expected: Auto-remediable)
  6. ADF Schema Mismatch (Expected: Manual intervention)

""")

    input("Press Enter to start tests...")

    # Run test scenarios
    for scenario_name, scenario_data in TEST_SCENARIOS.items():
        send_webhook(scenario_name, scenario_data)
        time.sleep(2)  # Small delay between tests

    print(f"\n{'='*80}")
    print(f"✅ ALL TESTS COMPLETED!")
    print(f"{'='*80}\n")
    print(f"View tickets in dashboard: {RCA_BASE_URL}/dashboard")
    print(f"(Login with default credentials if needed)")


if __name__ == "__main__":
    main()
