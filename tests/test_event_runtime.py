"""
Unit and Integration Tests for Event-Driven Runtime, Safety & Idempotency Engine
"""

import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.event_runtime import EventDrivenRuntime, IdempotencyManager, SafetyPolicyEngine
from simulator.value_engine import CounterfactualValueEngine


class MockModel:
    def predict_proba(self, X):
        # Always predict probability 0.85 for active actions
        return np.array([[0.15, 0.85] for _ in range(len(X))])


class TestEventDrivenRuntime(unittest.TestCase):

    def setUp(self):
        self.runtime = EventDrivenRuntime()
        self.model = MockModel()
        self.model_features = [
            "amount", "account_age_days", "successful_payments", "failed_payments",
            "total_payments", "payment_success_rate", "historical_recovery_rate",
            "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
        ]

    def test_normal_event_processing(self):
        event = {
            "event_id": "EVT_1001",
            "failure_id": "FAIL_1001",
            "payment_id": "PAY_1001",
            "customer_id": "CUST_1001",
            "amount": 500.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "behavior_profile": "normal",
            "account_age_days": 100,
            "successful_payments": 5,
            "failed_payments": 1,
            "total_payments": 6,
            "payment_success_rate": 0.83,
            "historical_recovery_rate": 0.5,
            "engagement_score": 0.8,
            "payment_status": "FAILED",
        }

        res = self.runtime.process_payment_failed_event(event, self.model, self.model_features)
        self.assertEqual(res["status"], "SUCCESS")
        rec = res["record"]
        self.assertTrue(rec["decision_id"].startswith("DEC_"))
        self.assertTrue(rec["execution_id"].startswith("EXEC_"))
        self.assertTrue(rec["outcome_id"].startswith("OUT_"))
        self.assertEqual(rec["policy_result"], "ALLOW")

    def test_duplicate_event_rejection(self):
        event = {
            "event_id": "EVT_DUP_001",
            "failure_id": "FAIL_DUP_001",
            "payment_id": "PAY_DUP_001",
            "customer_id": "CUST_DUP_001",
            "amount": 300.0,
            "failure_reason": "NETWORK_ERROR",
            "behavior_profile": "normal",
            "account_age_days": 50,
            "successful_payments": 2,
            "failed_payments": 0,
            "total_payments": 2,
            "payment_success_rate": 1.0,
            "historical_recovery_rate": 0.5,
            "engagement_score": 0.7,
            "payment_status": "FAILED",
        }

        # First ingestion
        res1 = self.runtime.process_payment_failed_event(event, self.model, self.model_features)
        self.assertEqual(res1["status"], "SUCCESS")

        # Second ingestion with same event_id
        res2 = self.runtime.process_payment_failed_event(event, self.model, self.model_features)
        self.assertEqual(res2["status"], "REJECTED_DUPLICATE_EVENT")

    def test_already_recovered_payment_rejection(self):
        event = {
            "event_id": "EVT_REC_001",
            "failure_id": "FAIL_REC_001",
            "payment_id": "PAY_REC_001",
            "customer_id": "CUST_REC_001",
            "amount": 200.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "behavior_profile": "normal",
            "account_age_days": 20,
            "successful_payments": 1,
            "failed_payments": 0,
            "total_payments": 1,
            "payment_success_rate": 1.0,
            "historical_recovery_rate": 0.5,
            "engagement_score": 0.8,
            "payment_status": "SUCCESS",  # Already recovered!
        }

        res = self.runtime.process_payment_failed_event(event, self.model, self.model_features)
        self.assertEqual(res["status"], "REJECTED_ALREADY_RECOVERED")

    def test_high_value_low_confidence_human_escalation(self):
        policy_engine = SafetyPolicyEngine()
        decision = {
            "candidate_action": "PAYMENT_LINK",
            "amount": 15000.0,  # > ₹10,000 threshold
            "estimated_recovery_probability": 0.50,  # < 0.70 confidence threshold
            "expected_net_recovery": 7497.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "failed_payments": 1,
        }

        policy_res = policy_engine.evaluate_policy(decision)
        self.assertEqual(policy_res["policy_result"], "HUMAN")
        self.assertIn("HIGH_VALUE_LOW_CONFIDENCE_HUMAN", policy_res["policy_checks"])

    def test_stale_payment_event_rejection(self):
        policy_engine = SafetyPolicyEngine()
        stale_decision = {
            "candidate_action": "PAYMENT_LINK",
            "amount": 500.0,
            "estimated_recovery_probability": 0.85,
            "expected_net_recovery": 422.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "event_age_days": 45,  # > 30 days stale!
        }

        policy_res = policy_engine.evaluate_policy(stale_decision)
        self.assertEqual(policy_res["policy_result"], "STOP")
        self.assertIn("STALE_EVENT_BLOCKED", policy_res["policy_checks"])


if __name__ == "__main__":
    unittest.main()
