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


import tempfile
import os
from simulator.persistence import DurableStateStore


class TestEventDrivenRuntime(unittest.TestCase):

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        store = DurableStateStore(db_path=Path(self.temp_path))
        self.runtime = EventDrivenRuntime(config=None)
        self.runtime.idempotency = IdempotencyManager(db_store=store)
        self.model = MockModel()
        self.model_features = [
            "amount", "account_age_days", "successful_payments", "failed_payments",
            "total_payments", "payment_success_rate", "historical_recovery_rate",
            "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
        ]

    def tearDown(self):
        try:
            if os.path.exists(self.temp_path):
                os.remove(self.temp_path)
        except Exception:
            pass

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

    def test_duplicate_failure_id_rejection(self):
        event1 = {
            "event_id": "EVT_F1",
            "failure_id": "FAIL_SHARED_100",
            "payment_id": "PAY_F1",
            "customer_id": "CUST_F1",
            "amount": 400.0,
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
        event2 = {
            "event_id": "EVT_F2_DIFFERENT",
            "failure_id": "FAIL_SHARED_100",  # Same failure ID under different event_id!
            "payment_id": "PAY_F1",
            "customer_id": "CUST_F1",
            "amount": 400.0,
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

        res1 = self.runtime.process_payment_failed_event(event1, self.model, self.model_features)
        self.assertEqual(res1["status"], "SUCCESS")

        res2 = self.runtime.process_payment_failed_event(event2, self.model, self.model_features)
        self.assertEqual(res2["status"], "REJECTED_DUPLICATE_EVENT")
        self.assertIn("FAIL_SHARED_100", res2["message"])

    def test_execution_adapter_injection(self):
        class DummyAdapter:
            execution_mode = "CUSTOM_TEST_MODE"
            def execute_action(self, decision_record):
                return {
                    "execution_mode": "CUSTOM_TEST_MODE",
                    "execution_status": "CUSTOM_EXECUTED",
                    "execution_result": "DUMMY_SUCCESS",
                }

        runtime_custom = EventDrivenRuntime(execution_adapter=DummyAdapter())
        runtime_custom.idempotency = IdempotencyManager(db_store=self.runtime.idempotency.durable_store)

        event = {
            "event_id": "EVT_CUSTOM_ADAPTER",
            "failure_id": "FAIL_CUSTOM_ADAPTER",
            "payment_id": "PAY_CUSTOM",
            "customer_id": "CUST_CUSTOM",
            "amount": 400.0,
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

        res = runtime_custom.process_payment_failed_event(event, self.model, self.model_features)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["record"]["execution_status"], "CUSTOM_EXECUTED")
        self.assertEqual(res["record"]["execution_mode"], "CUSTOM_TEST_MODE")

    def test_concurrent_duplicate_failure_attempts(self):
        import concurrent.futures

        class CountingAdapter:
            execution_mode = "COUNTING_SIMULATION"
            def __init__(self):
                self.call_count = 0
            def execute_action(self, decision_record):
                self.call_count += 1
                return {
                    "execution_mode": "COUNTING_SIMULATION",
                    "execution_status": "EXECUTED_SIMULATION",
                    "execution_result": decision_record.get("candidate_action"),
                }

        adapter = CountingAdapter()
        runtime_conc = EventDrivenRuntime(execution_adapter=adapter)
        runtime_conc.idempotency = IdempotencyManager(db_store=self.runtime.idempotency.durable_store)

        def worker(evt_idx):
            evt = {
                "event_id": f"EVT_CONC_{evt_idx}",
                "failure_id": "FAIL_CONCURRENT_999",  # Identical failure_id across all threads!
                "payment_id": "PAY_CONC",
                "customer_id": "CUST_CONC",
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
            return runtime_conc.process_payment_failed_event(evt, self.model, self.model_features)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successes = [r for r in results if r["status"] == "SUCCESS"]
        duplicates = [r for r in results if r["status"] == "REJECTED_DUPLICATE_EVENT"]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(duplicates), 4)
        self.assertEqual(adapter.call_count, 1)

    def test_adapter_non_invocation_on_stop_human_recovered_stale(self):
        class CountingAdapter:
            execution_mode = "COUNTING_SIMULATION"
            def __init__(self):
                self.call_count = 0
            def execute_action(self, decision_record):
                self.call_count += 1
                return {"execution_status": "EXECUTED_SIMULATION"}

        adapter = CountingAdapter()
        rt = EventDrivenRuntime(execution_adapter=adapter)
        rt.idempotency = IdempotencyManager(db_store=self.runtime.idempotency.durable_store)

        # 1. ALREADY_RECOVERED
        evt_rec = {
            "event_id": "EVT_NON_INV_1", "failure_id": "FAIL_NON_INV_1", "payment_id": "PAY_1", "customer_id": "C1",
            "amount": 500.0, "failure_reason": "INSUFFICIENT_FUNDS", "behavior_profile": "normal",
            "account_age_days": 50, "successful_payments": 1, "failed_payments": 0, "total_payments": 1,
            "payment_success_rate": 1.0, "historical_recovery_rate": 0.5, "engagement_score": 0.8,
            "payment_status": "RECOVERED"
        }
        res_rec = rt.process_payment_failed_event(evt_rec, self.model, self.model_features)
        self.assertEqual(res_rec["status"], "REJECTED_ALREADY_RECOVERED")
        self.assertEqual(adapter.call_count, 0)

        # 2. HUMAN escalation (high value, low confidence)
        evt_human = {
            "event_id": "EVT_NON_INV_2", "failure_id": "FAIL_NON_INV_2", "payment_id": "PAY_2", "customer_id": "C2",
            "amount": 15000.0, "failure_reason": "INSUFFICIENT_FUNDS", "behavior_profile": "normal",
            "account_age_days": 50, "successful_payments": 1, "failed_payments": 0, "total_payments": 1,
            "payment_success_rate": 1.0, "historical_recovery_rate": 0.5, "engagement_score": 0.8,
            "payment_status": "FAILED"
        }
        class LowProbModel:
            def predict_proba(self, X):
                return np.array([[0.5, 0.5] for _ in range(len(X))])
        res_human = rt.process_payment_failed_event(evt_human, LowProbModel(), self.model_features)
        self.assertEqual(res_human["record"]["policy_result"], "HUMAN")
        self.assertEqual(adapter.call_count, 0)

        # 3. STALE event (STOP)
        evt_stale = {
            "event_id": "EVT_NON_INV_3", "failure_id": "FAIL_NON_INV_3", "payment_id": "PAY_3", "customer_id": "C3",
            "amount": 500.0, "failure_reason": "INSUFFICIENT_FUNDS", "behavior_profile": "normal",
            "account_age_days": 50, "successful_payments": 1, "failed_payments": 0, "total_payments": 1,
            "payment_success_rate": 1.0, "historical_recovery_rate": 0.5, "engagement_score": 0.8,
            "event_age_days": 45, "payment_status": "FAILED"
        }
        res_stale = rt.process_payment_failed_event(evt_stale, self.model, self.model_features)
        self.assertEqual(res_stale["record"]["policy_result"], "STOP")
        self.assertEqual(adapter.call_count, 0)

    def test_persistence_restart_duplicate_failure_rejection(self):
        class CountingAdapter:
            execution_mode = "COUNTING_SIMULATION"
            def __init__(self):
                self.call_count = 0
            def execute_action(self, decision_record):
                self.call_count += 1
                return {"execution_status": "EXECUTED_SIMULATION"}

        adapter1 = CountingAdapter()
        rt1 = EventDrivenRuntime(execution_adapter=adapter1)
        rt1.idempotency = IdempotencyManager(db_store=self.runtime.idempotency.durable_store)

        evt1 = {
            "event_id": "EVT_PERSIST_RESTART_1",
            "failure_id": "FAIL_PERSIST_RESTART_1",
            "payment_id": "PAY_PR1",
            "customer_id": "CUST_PR1",
            "amount": 400.0,
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
        res1 = rt1.process_payment_failed_event(evt1, self.model, self.model_features)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(adapter1.call_count, 1)

        # Simulate Application Restart: Instantiate NEW runtime reading SAME db
        adapter2 = CountingAdapter()
        rt2 = EventDrivenRuntime(execution_adapter=adapter2)
        rt2.idempotency = IdempotencyManager(db_store=DurableStateStore(db_path=Path(self.temp_path)))

        evt2 = {
            "event_id": "EVT_PERSIST_RESTART_2_DIFF",
            "failure_id": "FAIL_PERSIST_RESTART_1",  # Same failure ID!
            "payment_id": "PAY_PR1",
            "customer_id": "CUST_PR1",
            "amount": 400.0,
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
        res2 = rt2.process_payment_failed_event(evt2, self.model, self.model_features)
        self.assertEqual(res2["status"], "REJECTED_DUPLICATE_EVENT")
        self.assertEqual(adapter2.call_count, 0)


if __name__ == "__main__":
    unittest.main()
