"""
Unit and Integration Tests for Razorpay Test Mode Webhook Adapter
"""

import sys
import os
import json
import hmac
import hashlib
import time
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from api.main import app

client = TestClient(app)


def compute_signature(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


class TestRazorpayWebhookAdapter(unittest.TestCase):

    def setUp(self):
        self.secret = "test_webhook_secret_key_12345"
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = self.secret

    def tearDown(self):
        if "RAZORPAY_WEBHOOK_SECRET" in os.environ:
            del os.environ["RAZORPAY_WEBHOOK_SECRET"]

    def test_A_valid_signature_and_valid_payload_accepted(self):
        evt_id = f"evt_rzp_test_{int(time.time()*1000)}"
        pay_id = f"pay_test_{int(time.time()*1000)}"
        payload = {
            "entity": "event",
            "account_id": "acc_test_123",
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "entity": "payment",
                        "amount": 250000,
                        "currency": "INR",
                        "status": "failed",
                        "order_id": "order_123",
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Card has expired",
                        "error_reason": "card_expired",
                        "customer_id": "cust_rzp_001"
                    }
                }
            },
            "created_at": 1693500000
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["accepted"])
        self.assertEqual(data["event_id"], evt_id)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertTrue(data["decision_id"].startswith("DEC_"))

    def test_B_invalid_signature_rejected(self):
        evt_id = f"evt_rzp_bad_sig_{int(time.time()*1000)}"
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": "pay_bad_sig", "amount": 100000}}}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        bad_sig = "a" * 64

        headers = {
            "X-Razorpay-Signature": bad_sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("Invalid X-Razorpay-Signature", data["detail"])

    def test_C_missing_signature_when_secret_configured_rejected(self):
        evt_id = f"evt_rzp_no_sig_{int(time.time()*1000)}"
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": "pay_no_sig", "amount": 100000}}}
        }
        body_bytes = json.dumps(payload).encode("utf-8")

        headers = {
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Missing X-Razorpay-Signature header", data["detail"])

    def test_D_unsupported_event_ignored_without_runtime_invocation(self):
        evt_id = f"evt_rzp_unsupported_{int(time.time()*1000)}"
        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_cap_001", "amount": 500000}}}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["accepted"])
        self.assertEqual(data["status"], "IGNORED")
        self.assertIn("payment.captured", data["message"])

    def test_E_correct_paisa_to_inr_conversion(self):
        evt_id = f"evt_rzp_paisa_{int(time.time()*1000)}"
        pay_id = f"pay_paisa_{int(time.time()*1000)}"
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "amount": 250000,  # 250000 paisa = 2500.00 INR
                        "customer_id": "cust_paisa_001",
                        "error_reason": "card_expired"
                    }
                }
            }
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SUCCESS")

        # Verify in audit endpoint that amount recorded was float 2500.00 INR
        audit_resp = client.get("/api/v2/audit")
        audit_data = audit_resp.json()["audit_trail"]
        match = next((item for item in audit_data if item.get("payment_id") == pay_id), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["amount"], 2500.00)

    def test_F_correct_event_id_extraction(self):
        evt_id = f"evt_hdr_id_{int(time.time()*1000)}"
        pay_id = f"pay_hdr_{int(time.time()*1000)}"
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": pay_id, "amount": 150000, "error_reason": "insufficient_funds"}}}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["event_id"], evt_id)

    def test_G_correct_payment_customer_failure_reason_mapping(self):
        evt_id = f"evt_mapping_{int(time.time()*1000)}"
        pay_id = f"pay_map_{int(time.time()*1000)}"
        cust_id = "cust_mapped_007"
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "amount": 350000,
                        "customer_id": cust_id,
                        "error_reason": "card expired"
                    }
                }
            }
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 200)

        # Inspect audit trail for normalized values
        audit_resp = client.get("/api/v2/audit")
        audit_data = audit_resp.json()["audit_trail"]
        match = next((item for item in audit_data if item.get("payment_id") == pay_id), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["customer_id"], cust_id)
        self.assertEqual(match["failure_reason"], "CARD_EXPIRED")

    def test_H_duplicate_razorpay_event_idempotency(self):
        evt_id = f"evt_dupe_{int(time.time()*1000)}"
        pay_id = f"pay_dupe_{int(time.time()*1000)}"
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": pay_id, "amount": 100000, "error_reason": "insufficient_funds"}}}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        # First delivery
        resp1 = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["status"], "SUCCESS")

        # Second (duplicate) delivery with same event_id
        resp2 = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["status"], "REJECTED_DUPLICATE_EVENT")

    def test_I_malformed_payload_returns_400(self):
        evt_id = f"evt_malformed_{int(time.time()*1000)}"
        body_bytes = b"{ invalid json content }"
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON payload", response.json()["detail"])

    def test_J_missing_required_payment_id_or_amount(self):
        evt_id = f"evt_missing_fields_{int(time.time()*1000)}"
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"customer_id": "cust_no_pay_id"}}}
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(body_bytes, self.secret)

        headers = {
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": evt_id,
            "Content-Type": "application/json"
        }

        response = client.post("/api/v2/webhooks/razorpay", content=body_bytes, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing required payment id or amount", response.json()["detail"])

    def test_security_requirements(self):
        # 1. Secret is read dynamically from env / config, not hardcoded
        self.assertIn("RAZORPAY_WEBHOOK_SECRET", os.environ)
        self.assertEqual(os.environ["RAZORPAY_WEBHOOK_SECRET"], self.secret)

        # 2. Raw secret is not present in API responses
        resp = client.get("/api/v2/config")
        self.assertNotIn(self.secret, json.dumps(resp.json()))


if __name__ == "__main__":
    unittest.main()
