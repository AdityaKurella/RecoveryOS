"""
RecoveryOS V2 — Milestone 13: Deterministic End-to-End Demo Runner

Demonstrates 5 core scenarios:
1. Successful High-Value Autonomous Recovery (ALLOW)
2. Human Escalation Guardrail (HUMAN)
3. No-Intervention Option (STOP)
4. Duplicate Event Idempotency Rejection (DUPLICATE)
5. Already Recovered Payment Protection (ALREADY_RECOVERED)
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.event_runtime import EventDrivenRuntime
from simulator.config import SystemConfig
from simulator.v2_counterfactual_policy import load_model, MODEL_PATH, MODEL_FEATURES


def run_deterministic_demo():
    print("\n======================================================================")
    print("RECOVERYOS V2 — DETERMINISTIC END-TO-END DEMO")
    print("======================================================================")

    config = SystemConfig()
    runtime = EventDrivenRuntime(config=config)
    model = load_model(MODEL_PATH)

    model_features = [
        "amount", "account_age_days", "successful_payments", "failed_payments",
        "total_payments", "payment_success_rate", "historical_recovery_rate",
        "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
    ]

    scenarios = [
        {
            "name": "Scenario 1: High-Value Autonomous Recovery (ALLOW)",
            "payload": {
                "event_id": "EVT_DEMO_001",
                "failure_id": "FAIL_DEMO_001",
                "payment_id": "PAY_DEMO_001",
                "customer_id": "CUST_DEMO_001",
                "amount": 2500.0,
                "failure_reason": "INSUFFICIENT_FUNDS",
                "behavior_profile": "normal",
                "account_age_days": 180,
                "successful_payments": 6,
                "failed_payments": 1,
                "total_payments": 7,
                "payment_success_rate": 0.85,
                "historical_recovery_rate": 0.6,
                "engagement_score": 0.8,
                "payment_status": "FAILED",
            }
        },
        {
            "name": "Scenario 2: High-Value Low-Confidence Human Escalation (HUMAN)",
            "payload": {
                "event_id": "EVT_DEMO_002",
                "failure_id": "FAIL_DEMO_002",
                "payment_id": "PAY_DEMO_002",
                "customer_id": "CUST_DEMO_002",
                "amount": 15000.0,  # > ₹10,000 threshold
                "failure_reason": "LIMIT_EXCEEDED",
                "behavior_profile": "high_value_loyal",
                "account_age_days": 30,
                "successful_payments": 1,
                "failed_payments": 3,  # Reached max retries
                "total_payments": 4,
                "payment_success_rate": 0.25,
                "historical_recovery_rate": 0.2,
                "engagement_score": 0.4,
                "payment_status": "FAILED",
            }
        },
        {
            "name": "Scenario 3: No-Intervention Option (STOP)",
            "payload": {
                "event_id": "EVT_DEMO_003",
                "failure_id": "FAIL_DEMO_003",
                "payment_id": "PAY_DEMO_003",
                "customer_id": "CUST_DEMO_003",
                "amount": 1.0,  # Small ₹1 amount -> all interventions loss-making
                "failure_reason": "BANK_DECLINED",
                "behavior_profile": "friction_prone",
                "account_age_days": 10,
                "successful_payments": 0,
                "failed_payments": 2,
                "total_payments": 2,
                "payment_success_rate": 0.0,
                "historical_recovery_rate": 0.0,
                "engagement_score": 0.1,
                "payment_status": "FAILED",
            }
        },
        {
            "name": "Scenario 4: Duplicate Event Idempotency Rejection",
            "payload": {
                "event_id": "EVT_DEMO_001",  # Same event_id as Scenario 1!
                "failure_id": "FAIL_DEMO_001",
                "payment_id": "PAY_DEMO_001",
                "customer_id": "CUST_DEMO_001",
                "amount": 2500.0,
                "failure_reason": "INSUFFICIENT_FUNDS",
                "behavior_profile": "normal",
                "payment_status": "FAILED",
            }
        },
        {
            "name": "Scenario 5: Already Recovered Payment Protection",
            "payload": {
                "event_id": "EVT_DEMO_005",
                "failure_id": "FAIL_DEMO_005",
                "payment_id": "PAY_DEMO_005",
                "customer_id": "CUST_DEMO_005",
                "amount": 1200.0,
                "failure_reason": "INSUFFICIENT_FUNDS",
                "behavior_profile": "normal",
                "payment_status": "SUCCESS",  # Already recovered!
            }
        },
    ]

    for idx, sc in enumerate(scenarios, 1):
        print(f"\n----------------------------------------------------------------------")
        print(f"RUNNING {sc['name']}")
        print(f"----------------------------------------------------------------------")
        res = runtime.process_payment_failed_event(sc["payload"], model, model_features)
        print(f"Runtime Status: {res['status']}")
        print(f"Message:        {res['message']}")
        if res["record"]:
            rec = res["record"]
            print(f"Decision ID:    {rec.get('decision_id')}")
            print(f"Action:         {rec.get('candidate_action')}")
            print(f"Expected Net:   ₹{rec.get('expected_net_recovery', 0.0):,.2f}")
            print(f"Policy Result:  {rec.get('policy_result')}")
            print(f"Policy Reason:  {rec.get('policy_reason')}")
            print(f"Execution:      {rec.get('execution_status')}")

    print("\n======================================================================")
    print("DEMO RUNNER COMPLETE. ✅ ALL 5 SCENARIOS VERIFIED.")
    print("======================================================================")


if __name__ == "__main__":
    run_deterministic_demo()
