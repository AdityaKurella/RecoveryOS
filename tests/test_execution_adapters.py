"""
Unit Tests for Execution Adapters (Simulator & Razorpay Test Mode)
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.execution_adapters import SimulationExecutionAdapter, RazorpayTestModeAdapter


class TestExecutionAdapters(unittest.TestCase):

    def test_simulation_execution_adapter(self):
        adapter = SimulationExecutionAdapter()
        decision = {
            "failure_id": "FAIL_EXEC_001",
            "candidate_action": "PAYMENT_LINK",
            "estimated_recovery_probability": 0.85,
            "amount": 1000.0,
            "intervention_cost": 3.0,
        }
        res = adapter.execute_action(decision)
        self.assertEqual(res["execution_mode"], "SIMULATION")
        self.assertEqual(res["execution_status"], "EXECUTED_SIMULATION")

    def test_razorpay_test_mode_unauthenticated(self):
        adapter = RazorpayTestModeAdapter(key_id=None, key_secret=None)
        decision = {"payment_id": "pay_test_123", "candidate_action": "RETRY_NOW"}
        res = adapter.execute_action(decision)
        self.assertEqual(res["execution_mode"], "RAZORPAY_TEST_MODE")
        self.assertEqual(res["execution_status"], "TEST_MODE_UNAUTHENTICATED")

    def test_razorpay_test_mode_authenticated(self):
        adapter = RazorpayTestModeAdapter(key_id="rzp_test_key", key_secret="rzp_secret")
        decision = {"payment_id": "pay_test_123", "candidate_action": "RETRY_NOW"}
        res = adapter.execute_action(decision)
        self.assertEqual(res["execution_mode"], "RAZORPAY_TEST_MODE")
        self.assertEqual(res["execution_status"], "RAZORPAY_SANDBOX_DISPATCHED")


if __name__ == "__main__":
    unittest.main()
