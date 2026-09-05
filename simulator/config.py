"""
RecoveryOS V2 — Centralized Configuration & Policy Settings
"""

import os
from typing import Dict, List, Set, Any, Optional
from pathlib import Path

# Repository Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = DATA_DIR / "recovery_probability"
MODEL_PATH = MODEL_DIR / "counterfactual_model.pkl.gz"

# Razorpay Integration Config
RAZORPAY_WEBHOOK_SECRET: Optional[str] = os.getenv("RAZORPAY_WEBHOOK_SECRET")
RAZORPAY_KEY_ID: Optional[str] = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET: Optional[str] = os.getenv("RAZORPAY_KEY_SECRET")

# System & Policy Versions
MODEL_VERSION = "M10F_v1"
FEATURE_VERSION = "M10F_v1"
POLICY_VERSION = "V3.1"
SYSTEM_NAME = "RecoveryOS V3.1"

# Candidate Actions
ACTIVE_ACTIONS: List[str] = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
]

ALL_ACTIONS: List[str] = ACTIVE_ACTIONS + ["STOP"]

# Intervention Costs (INR ₹)
ACTION_COSTS: Dict[str, float] = {
    "RETRY_NOW": 2.00,
    "WAIT_AND_RETRY": 2.00,
    "SEND_REMINDER": 1.00,
    "PAYMENT_LINK": 3.00,
    "UPDATE_PAYMENT_METHOD": 3.00,
    "STOP": 0.00,
}

# Economic & Portfolio Defaults
DEFAULT_PORTFOLIO_CAPACITY: int = 100
MIN_EXPECTED_NET_THRESHOLD: float = 0.0
MIN_AUTONOMOUS_NET_THRESHOLD: float = 50.0

# Safety & Bounded Autonomy Guardrails
HIGH_VALUE_THRESHOLD: float = 10000.0  # ₹10,000
HIGH_VALUE_MIN_PROBABILITY: float = 0.70  # Requires >= 70% confidence for high value
MAX_RETRY_ATTEMPTS: int = 3

# Failure Reason Compatibility Rules
INCOMPATIBLE_ACTION_RULES: Dict[str, List[str]] = {
    "CARD_EXPIRED": ["RETRY_NOW", "WAIT_AND_RETRY"],
}


class SystemConfig:
    """Inspectable system configuration container."""
    def __init__(self, capacity: int = DEFAULT_PORTFOLIO_CAPACITY):
        self.capacity = capacity
        self.action_costs = ACTION_COSTS
        self.model_version = MODEL_VERSION
        self.feature_version = FEATURE_VERSION
        self.policy_version = POLICY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_name": SYSTEM_NAME,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "policy_version": self.policy_version,
            "portfolio_capacity": self.capacity,
            "action_costs": self.action_costs,
            "high_value_threshold": HIGH_VALUE_THRESHOLD,
            "high_value_min_prob": HIGH_VALUE_MIN_PROBABILITY,
            "max_retry_attempts": MAX_RETRY_ATTEMPTS,
            "min_autonomous_net_threshold": MIN_AUTONOMOUS_NET_THRESHOLD,
            "razorpay_test_api_configured": bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET")),
        }
