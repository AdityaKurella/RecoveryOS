"""
API Integration Unit Tests for FastAPI Service
"""

import sys
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
        payload = {
            "event_id": "EVT_TEST_API_001",
            "failure_id": "FAIL_TEST_API_001",
            "payment_id": "PAY_TEST_API_001",
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


if __name__ == "__main__":
    unittest.main()
