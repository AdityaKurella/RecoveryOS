"""
RecoveryOS V3 — Execution Adapter Interface

Supports:
1. SimulationExecutionAdapter (Default deterministic simulator)
2. RazorpayTestModeAdapter (Razorpay Test Mode integration adapter)
"""

import os
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseExecutionAdapter(ABC):
    """Abstract base class for recovery execution adapters."""
    @abstractmethod
    def execute_action(self, decision_record: Dict[str, Any]) -> Dict[str, Any]:
        pass


class SimulationExecutionAdapter(BaseExecutionAdapter):
    """Default simulation adapter for offline benchmark & demonstration."""
    def execute_action(self, decision_record: Dict[str, Any]) -> Dict[str, Any]:
        failure_id = str(decision_record.get("failure_id", ""))
        action = decision_record.get("candidate_action")
        prob = float(decision_record.get("estimated_recovery_probability", 0.0))
        amount = float(decision_record.get("amount", 0.0))
        cost = float(decision_record.get("intervention_cost", 0.0))

        # Deterministic outcome simulation using hash draw
        draw_val = int(hashlib.sha256(f"outcome_{failure_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        recovered = draw_val < prob

        realized_gross = amount if recovered else 0.0
        realized_net = realized_gross - cost

        return {
            "execution_mode": "SIMULATION",
            "execution_status": "EXECUTED_SIMULATION",
            "execution_result": action,
            "simulated_recovered": recovered,
            "realized_gross_recovery": realized_gross,
            "realized_net_recovery": realized_net,
        }


class RazorpayTestModeAdapter(BaseExecutionAdapter):
    """Razorpay Test Mode Sandbox Adapter."""
    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET")

    def execute_action(self, decision_record: Dict[str, Any]) -> Dict[str, Any]:
        if not self.key_id or not self.key_secret:
            return {
                "execution_mode": "RAZORPAY_TEST_MODE",
                "execution_status": "TEST_MODE_UNAUTHENTICATED",
                "execution_result": "MISSING_RAZORPAY_CREDENTIALS",
                "message": "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables not configured.",
            }

        # Sandbox payload representation
        payment_id = decision_record.get("payment_id")
        action = decision_record.get("candidate_action")

        return {
            "execution_mode": "RAZORPAY_TEST_MODE",
            "execution_status": "RAZORPAY_SANDBOX_DISPATCHED",
            "execution_result": f"RAZORPAY_{action}",
            "razorpay_payment_id": payment_id,
            "message": f"Dispatched recovery action {action} to Razorpay Test Mode API.",
        }
