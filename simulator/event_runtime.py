"""
RecoveryOS V2 — Milestone 4, 5, 6, 7: Event-Driven Runtime, Safety, Idempotency & Audit Engine

Processes payment.failed events end-to-end:
Event Ingestion -> Idempotency Check -> Context Lookup -> Feature Building -> Value Engine
-> Portfolio Optimization -> Policy Safety Check -> Execution Simulation -> Outcome Audit
"""

import sys
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.config import (
    SystemConfig,
    ACTION_COSTS,
    HIGH_VALUE_THRESHOLD,
    HIGH_VALUE_MIN_PROBABILITY,
    MIN_AUTONOMOUS_NET_THRESHOLD,
    MAX_RETRY_ATTEMPTS,
    INCOMPATIBLE_ACTION_RULES,
)
from simulator.value_engine import CounterfactualValueEngine


from simulator.persistence import DurableStateStore


class IdempotencyManager:
    """Stores processed events, decisions, and executions with durable SQLite persistence."""
    def __init__(self, db_store: Optional[DurableStateStore] = None):
        self.durable_store = db_store or DurableStateStore()
        self.processed_events: Dict[str, Dict[str, Any]] = {}
        self.processed_failures: Dict[str, Dict[str, Any]] = {}
        self.executed_decisions: Dict[str, Dict[str, Any]] = {}

    def is_duplicate_event(self, event_id: str) -> bool:
        if event_id in self.processed_events:
            return True
        return self.durable_store.is_duplicate_event(event_id)

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        if event_id in self.processed_events:
            return self.processed_events[event_id]
        return self.durable_store.get_event_record(event_id)

    def is_duplicate_failure(self, failure_id: str) -> bool:
        return failure_id in self.processed_failures

    def is_decision_executed(self, decision_id: str) -> bool:
        return decision_id in self.executed_decisions

    def record_event(self, event_id: str, record: Dict[str, Any]):
        self.processed_events[event_id] = record
        fid = str(record.get("failure_id", ""))
        pid = str(record.get("payment_id", ""))
        cid = str(record.get("customer_id", ""))
        self.durable_store.record_event_and_decision(event_id, fid, pid, cid, record)

    def record_failure(self, failure_id: str, record: Dict[str, Any]):
        self.processed_failures[failure_id] = record

    def record_execution(self, decision_id: str, record: Dict[str, Any]):
        self.executed_decisions[decision_id] = record
        exec_id = str(record.get("execution_id", ""))
        fid = str(record.get("failure_id", ""))
        status = str(record.get("execution_status", ""))
        result = str(record.get("execution_result", ""))
        self.durable_store.record_execution(exec_id, decision_id, fid, status, result, record)


class SafetyPolicyEngine:
    """Enforces policy safety guardrails and bounded autonomy boundaries."""
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or SystemConfig()

    def evaluate_policy(self, decision_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates safety rules on a candidate decision record.
        Returns: policy_result ('ALLOW', 'HUMAN', 'STOP'), policy_reason, policy_checks.
        """
        action = decision_record.get("candidate_action")
        amount = float(decision_record.get("amount", 0.0))
        prob = float(decision_record.get("estimated_recovery_probability", 0.0))
        expected_net = float(decision_record.get("expected_net_recovery", 0.0))
        failure_reason = str(decision_record.get("failure_reason", ""))
        attempt_count = int(decision_record.get("failed_payments", 1))

        checks = []

        # 1. STOP Action Check
        if action == "STOP":
            return {
                "policy_result": "STOP",
                "policy_reason": "No-intervention option selected.",
                "policy_checks": ["ACTION_STOP"],
            }

        # 2. Stale Event Detection Guardrail
        if decision_record.get("is_stale", False) or decision_record.get("event_age_days", 0) > 30:
            return {
                "policy_result": "STOP",
                "policy_reason": "Payment failure event is stale (> 30 days old). Autonomous execution blocked.",
                "policy_checks": ["STALE_EVENT_BLOCKED"],
            }

        # 2. Incompatible Action Rule Check
        if failure_reason in INCOMPATIBLE_ACTION_RULES:
            if action in INCOMPATIBLE_ACTION_RULES[failure_reason]:
                return {
                    "policy_result": "STOP",
                    "policy_reason": f"Action '{action}' is incompatible with failure reason '{failure_reason}'.",
                    "policy_checks": ["INCOMPATIBLE_ACTION_BLOCKED"],
                }

        # 3. Retry Limit Enforcement
        if attempt_count >= MAX_RETRY_ATTEMPTS and action in ["RETRY_NOW", "WAIT_AND_RETRY"]:
            return {
                "policy_result": "HUMAN",
                "policy_reason": f"Customer reached max retry attempts ({attempt_count}). Escalating to human review.",
                "policy_checks": ["MAX_RETRY_LIMIT_EXCEEDED"],
            }

        # 4. Minimum Expected Net Threshold for Autonomous Execution
        if expected_net < MIN_AUTONOMOUS_NET_THRESHOLD:
            return {
                "policy_result": "STOP",
                "policy_reason": f"Expected net recovery (₹{expected_net:.2f}) below autonomous threshold (₹{MIN_AUTONOMOUS_NET_THRESHOLD:.2f}).",
                "policy_checks": ["EXPECTED_NET_TOO_LOW"],
            }

        # 5. High-Value Escalation Guardrail
        if amount >= HIGH_VALUE_THRESHOLD and prob < HIGH_VALUE_MIN_PROBABILITY:
            return {
                "policy_result": "HUMAN",
                "policy_reason": f"High value payment (₹{amount:,.2f}) with probability {prob:.2f} < {HIGH_VALUE_MIN_PROBABILITY:.2f}. Escalating to human review.",
                "policy_checks": ["HIGH_VALUE_LOW_CONFIDENCE_HUMAN"],
            }

        # 6. Default ALLOW
        return {
            "policy_result": "ALLOW",
            "policy_reason": "All policy safety checks passed cleanly.",
            "policy_checks": ["ALL_SAFETY_CHECKS_PASSED"],
        }


class EventDrivenRuntime:
    """Engine orchestrating the complete event pipeline."""
    def __init__(self, value_engine: Optional[CounterfactualValueEngine] = None, config: Optional[SystemConfig] = None):
        self.value_engine = value_engine or CounterfactualValueEngine()
        self.policy_engine = SafetyPolicyEngine(config)
        self.idempotency = IdempotencyManager()
        self.audit_log: List[Dict[str, Any]] = []

    def process_payment_failed_event(
        self,
        event_payload: Dict[str, Any],
        model: Any,
        model_features: List[str]
    ) -> Dict[str, Any]:
        """
        Ingests a payment.failed event and processes it through the pipeline.
        """
        event_id = str(event_payload.get("event_id", f"EVT_{int(time.time()*1000)}"))
        failure_id = str(event_payload.get("failure_id", ""))
        payment_id = str(event_payload.get("payment_id", ""))
        customer_id = str(event_payload.get("customer_id", ""))
        payment_status = str(event_payload.get("payment_status", "FAILED"))

        # 1. Idempotency Protection Check
        if self.idempotency.is_duplicate_event(event_id):
            cached = self.idempotency.get_event(event_id)
            return {
                "status": "REJECTED_DUPLICATE_EVENT",
                "message": f"Event '{event_id}' has already been processed.",
                "record": cached,
            }

        if payment_status in ["SUCCESS", "RECOVERED"]:
            return {
                "status": "REJECTED_ALREADY_RECOVERED",
                "message": f"Payment '{payment_id}' is already recovered/successful.",
                "record": None,
            }

        # Build single-row DataFrame for candidate table generation
        df = pd.DataFrame([event_payload])

        # 2. Score candidate actions via Value Engine
        candidate_table = self.value_engine.generate_candidate_table(df, model, model_features)
        best_decision = self.value_engine.select_best_decisions(candidate_table).iloc[0].to_dict()

        # Generate unique decision_id
        dec_hash = hashlib.sha256(f"{failure_id}_{best_decision['candidate_action']}".encode()).hexdigest()[:12]
        decision_id = f"DEC_{dec_hash}"
        best_decision["decision_id"] = decision_id
        best_decision["event_id"] = event_id

        # 3. Evaluate Policy Safety
        policy_eval = self.policy_engine.evaluate_policy(best_decision)
        best_decision.update(policy_eval)

        # 4. Simulate Execution Adapter
        policy_res = policy_eval["policy_result"]
        exec_hash = hashlib.sha256(f"{decision_id}_{policy_res}".encode()).hexdigest()[:12]
        execution_id = f"EXEC_{exec_hash}"
        best_decision["execution_id"] = execution_id

        if policy_res == "ALLOW":
            execution_status = "EXECUTED_SIMULATION"
            execution_result = best_decision["candidate_action"]
        elif policy_res == "HUMAN":
            execution_status = "NOT_AUTONOMOUSLY_EXECUTED"
            execution_result = "HUMAN_ESCALATION"
        else:
            execution_status = "NOT_EXECUTED"
            execution_result = "STOPPED"

        best_decision["execution_status"] = execution_status
        best_decision["execution_result"] = execution_result

        # 5. Outcome Engine (Simulated Outcome Audit)
        out_hash = hashlib.sha256(f"{execution_id}_{failure_id}".encode()).hexdigest()[:12]
        outcome_id = f"OUT_{out_hash}"
        best_decision["outcome_id"] = outcome_id

        # Simulate outcome deterministically using hash
        if execution_status == "EXECUTED_SIMULATION":
            prob = best_decision["estimated_recovery_probability"]
            # SHA256 uniform float draw in [0, 1]
            draw_val = int(hashlib.sha256(f"outcome_{failure_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
            recovered = draw_val < prob
            realized_gross = float(best_decision["amount"]) if recovered else 0.0
            realized_net = realized_gross - float(best_decision["intervention_cost"])
        else:
            recovered = False
            realized_gross = 0.0
            realized_net = 0.0

        best_decision["simulated_recovered"] = recovered
        best_decision["realized_gross_recovery"] = realized_gross
        best_decision["realized_net_recovery"] = realized_net

        # Record in Idempotency and Audit Log
        self.idempotency.record_event(event_id, best_decision)
        self.idempotency.record_failure(failure_id, best_decision)
        self.idempotency.record_execution(decision_id, best_decision)
        self.audit_log.append(best_decision)

        return {
            "status": "SUCCESS",
            "message": "Payment failure event processed successfully.",
            "record": best_decision,
        }
