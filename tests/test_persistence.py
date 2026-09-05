"""
Unit and Integration Tests for V3 Durable SQLite Persistence Engine
Tests idempotency deduplication across process restarts.
"""

import sys
import os
import unittest
from pathlib import Path
import tempfile

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.persistence import DurableStateStore


class TestDurableStateStore(unittest.TestCase):

    def setUp(self):
        # Create a temporary database file for testing process restarts
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.store = DurableStateStore(db_path=Path(self.temp_db_path))

    def tearDown(self):
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def test_record_and_check_duplicate_event(self):
        event_id = "EVT_TEST_PERSIST_001"
        self.assertFalse(self.store.is_duplicate_event(event_id))

        decision_rec = {
            "decision_id": "DEC_PERSIST_001",
            "event_id": event_id,
            "candidate_action": "PAYMENT_LINK",
            "estimated_recovery_probability": 0.85,
            "expected_net_recovery": 422.0,
            "policy_result": "ALLOW",
        }

        self.store.record_event_and_decision(event_id, "FAIL_001", "PAY_001", "CUST_001", decision_rec)
        self.assertTrue(self.store.is_duplicate_event(event_id))

    def test_process_restart_durability(self):
        """Simulates process crash and restart to verify state persists."""
        event_id = "EVT_RESTART_001"
        decision_rec = {
            "decision_id": "DEC_RESTART_001",
            "event_id": event_id,
            "candidate_action": "UPDATE_PAYMENT_METHOD",
            "expected_net_recovery": 750.0,
        }

        # First application instance records decision
        self.store.record_event_and_decision(event_id, "FAIL_RES", "PAY_RES", "CUST_RES", decision_rec)

        # Simulate restart: instantiate NEW store reading same DB file
        new_store_after_restart = DurableStateStore(db_path=Path(self.temp_db_path))
        self.assertTrue(new_store_after_restart.is_duplicate_event(event_id))

        cached = new_store_after_restart.get_event_record(event_id)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["candidate_action"], "UPDATE_PAYMENT_METHOD")
        self.assertEqual(cached["expected_net_recovery"], 750.0)

    def test_is_duplicate_failure_and_get_failure_record(self):
        event_id = "EVT_FAIL_DUP_01"
        failure_id = "FAIL_DUP_ID_100"
        decision_rec = {
            "decision_id": "DEC_FAIL_DUP_01",
            "event_id": event_id,
            "failure_id": failure_id,
            "candidate_action": "RETRY_NOW",
            "policy_result": "ALLOW",
        }
        self.store.record_event_and_decision(event_id, failure_id, "PAY_01", "CUST_01", decision_rec)
        self.assertTrue(self.store.is_duplicate_failure(failure_id))
        cached = self.store.get_failure_record(failure_id)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["candidate_action"], "RETRY_NOW")

    def test_audit_trail_retrieval_across_restart(self):
        event_id = "EVT_AUDIT_TRAIL_01"
        failure_id = "FAIL_AUDIT_01"
        decision_rec = {
            "decision_id": "DEC_AUDIT_01",
            "event_id": event_id,
            "failure_id": failure_id,
            "candidate_action": "PAYMENT_LINK",
            "policy_result": "ALLOW",
            "expected_net_recovery": 1200.0,
        }
        self.store.record_event_and_decision(event_id, failure_id, "PAY_AUDIT", "CUST_AUDIT", decision_rec)

        # Reopen database instance
        new_store = DurableStateStore(db_path=Path(self.temp_db_path))
        audit = new_store.get_audit_trail(limit=10)
        self.assertTrue(len(audit) >= 1)
        match = next((item for item in audit if item.get("decision_id") == "DEC_AUDIT_01"), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["candidate_action"], "PAYMENT_LINK")


if __name__ == "__main__":
    unittest.main()
