"""
API Integration Unit Tests for FastAPI Service
"""

import sys
import time
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from api.main import app

client = TestClient(app)


class TestFastAPIEndpoints(unittest.TestCase):

    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_loaded"])

    def test_v2_config_endpoint(self):
        response = client.get("/api/v2/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("action_costs", data)
        self.assertEqual(data["portfolio_capacity"], 100)

    def test_v2_events_failure_endpoint(self):
        unique_id = f"EVT_API_{int(time.time()*1000)}"
        payload = {
            "event_id": unique_id,
            "failure_id": f"FAIL_{unique_id}",
            "payment_id": f"PAY_{unique_id}",
            "customer_id": "CUST_TEST_API_001",
            "amount": 1250.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "behavior_profile": "normal",
        }
        response = client.post("/api/v2/events/failure", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertTrue(data["record"]["decision_id"].startswith("DEC_"))

    def test_v2_decisions_endpoint(self):
        response = client.get("/api/v2/decisions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("decisions", data)
        self.assertIn("decisions_count", data)

    def test_v1_legacy_overview_endpoint(self):
        response = client.get("/api/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_failures", data)
        self.assertIn("overall_recovery_rate", data)

    def test_v2_events_malformed_payload_returns_422(self):
        malformed_payload = {
            "event_id": "EVT_BAD_001",
            "failure_id": "FAIL_BAD_001",
            "payment_id": "PAY_BAD_001",
            "customer_id": "CUST_BAD_001",
            "amount": -100.0,  # Invalid negative amount!
            "failure_reason": "INSUFFICIENT_FUNDS",
        }
        response = client.post("/api/v2/events/failure", json=malformed_payload)
        self.assertEqual(response.status_code, 422)

    def test_v2_test_razorpay_order_endpoint(self):
        import os
        os.environ["RAZORPAY_KEY_ID"] = "rzp_test_TYFLOQq6CuJpRw"
        os.environ["RAZORPAY_KEY_SECRET"] = "bnvDurReCAcvXigTa2sTIaxl"
        response = client.post("/api/v2/test/razorpay-order?amount=2500.0")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertTrue(data["order_id"].startswith("order_"))
        self.assertEqual(data["amount_inr"], 2500.0)


if __name__ == "__main__":
    unittest.main()
