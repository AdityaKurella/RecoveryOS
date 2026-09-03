"""
Unit and Integration Tests for Milestone 1 Counterfactual Value Engine
Uses Python standard unittest library.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure simulator package is importable
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.value_engine import CounterfactualValueEngine, ACTIONS, ACTION_COSTS


class DummyModel:
    """Mock model returning pre-set probabilities for testing."""
    def __init__(self, prob_map=None):
        self.prob_map = prob_map or {}

    def predict_proba(self, X):
        probs = []
        for _, row in X.iterrows():
            action = row["candidate_action"]
            prob = self.prob_map.get(action, 0.5)
            probs.append([1.0 - prob, prob])
        return np.array(probs)


class TestCounterfactualValueEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CounterfactualValueEngine()

    def test_1_prob_zero_expected_gross_zero(self):
        res = self.engine.evaluate_candidate_action(amount=1000.0, candidate_action="RETRY_NOW", probability=0.0)
        self.assertEqual(res["expected_gross_recovery"], 0.0)
        self.assertEqual(res["expected_net_recovery"], -2.0)  # gross (0) - cost (2.0)

    def test_2_prob_one_expected_gross_full_amount(self):
        res = self.engine.evaluate_candidate_action(amount=1000.0, candidate_action="RETRY_NOW", probability=1.0)
        self.assertEqual(res["expected_gross_recovery"], 1000.0)
        self.assertEqual(res["expected_net_recovery"], 998.0)  # gross (1000) - cost (2.0)

    def test_3_expected_net_calculation(self):
        res = self.engine.evaluate_candidate_action(amount=500.0, candidate_action="PAYMENT_LINK", probability=0.8)
        self.assertEqual(res["expected_gross_recovery"], 400.0)
        self.assertEqual(res["intervention_cost"], 3.0)
        self.assertEqual(res["expected_net_recovery"], 397.0)

    def test_4_stop_zero_cost_and_zero_gross(self):
        res = self.engine.evaluate_candidate_action(amount=1000.0, candidate_action="STOP", probability=0.5)
        self.assertEqual(res["intervention_cost"], 0.0)
        self.assertEqual(res["expected_gross_recovery"], 0.0)
        self.assertEqual(res["expected_net_recovery"], 0.0)
        self.assertEqual(res["estimated_recovery_probability"], 0.0)

    def test_5_negative_probability_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate_candidate_action(amount=100.0, candidate_action="RETRY_NOW", probability=-0.1)

    def test_6_probability_greater_than_one_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate_candidate_action(amount=100.0, candidate_action="RETRY_NOW", probability=1.05)

    def test_7_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate_candidate_action(amount=-50.0, candidate_action="RETRY_NOW", probability=0.5)

    def test_8_candidate_actions_completeness_and_six_rows(self):
        df = pd.DataFrame([{
            "failure_id": "FAIL_TEST_001",
            "customer_id": "CUST_001",
            "subscription_id": "SUB_001",
            "amount": 100.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "behavior_profile": "normal",
            "account_age_days": 30,
            "successful_payments": 1,
            "failed_payments": 0,
            "total_payments": 1,
            "payment_success_rate": 1.0,
            "historical_recovery_rate": 0.5,
            "engagement_score": 0.8,
        }])

        dummy_model = DummyModel()
        model_features = [
            "amount", "account_age_days", "successful_payments", "failed_payments",
            "total_payments", "payment_success_rate", "historical_recovery_rate",
            "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
        ]

        candidate_df = self.engine.generate_candidate_table(df, dummy_model, model_features)
        self.assertEqual(len(candidate_df), 6)
        actions_found = set(candidate_df["candidate_action"])
        self.assertEqual(actions_found, set(ACTIONS))

    def test_9_10_deterministic_ranking_and_stop_selected_when_loss_making(self):
        df = pd.DataFrame([{
            "failure_id": "FAIL_LOSS_001",
            "customer_id": "CUST_001",
            "amount": 1.0,  # Small amount ₹1.0
            "failure_reason": "INSUFFICIENT_FUNDS",
            "behavior_profile": "normal",
        }])

        # All active actions have low probability, gross recovery < cost
        prob_map = {
            "RETRY_NOW": 0.1,             # gross=0.1, cost=2 -> net=-1.9
            "WAIT_AND_RETRY": 0.1,        # gross=0.1, cost=2 -> net=-1.9
            "SEND_REMINDER": 0.1,         # gross=0.1, cost=1 -> net=-0.9
            "PAYMENT_LINK": 0.1,          # gross=0.1, cost=3 -> net=-2.9
            "UPDATE_PAYMENT_METHOD": 0.1, # gross=0.1, cost=3 -> net=-2.9
        }
        dummy_model = DummyModel(prob_map=prob_map)
        model_features = ["amount", "candidate_action"]

        candidate_df = self.engine.generate_candidate_table(df, dummy_model, model_features)
        best_df = self.engine.select_best_decisions(candidate_df)

        # STOP (net = 0.0) MUST be selected as rank 1!
        self.assertEqual(best_df.iloc[0]["candidate_action"], "STOP")
        self.assertEqual(best_df.iloc[0]["expected_net_recovery"], 0.0)

    def test_11_data_isolation_rejects_true_probability_in_features(self):
        df = pd.DataFrame([{
            "failure_id": "FAIL_ISO_001",
            "amount": 100.0,
            "true_recovery_probability": 0.95,  # Leak attempt!
        }])
        dummy_model = DummyModel()
        with self.assertRaises(ValueError):
            self.engine.generate_candidate_table(df, dummy_model, ["amount"])

    def test_12_deterministic_multi_tier_tie_breaking_precision(self):
        """
        Verifies that when two candidate actions produce identical expected_net_recovery,
        ties are broken deterministically by:
        1. expected_net_recovery DESC
        2. expected_gross_recovery DESC
        3. estimated_recovery_probability DESC
        4. amount DESC
        5. candidate_action ASC
        """
        df = pd.DataFrame([{
            "failure_id": "FAIL_TIE_001",
            "customer_id": "CUST_001",
            "amount": 100.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "behavior_profile": "normal",
        }])

        # Action 1: PAYMENT_LINK (cost = 3.0), prob = 0.80 -> gross = 80.0, net = 77.0
        # Action 2: RETRY_NOW (cost = 2.0), prob = 0.79 -> gross = 79.0, net = 77.0
        # Both produce net = 77.0. Tier 2 (gross recovery: 80.0 vs 79.0) MUST break tie in favor of PAYMENT_LINK.
        prob_map = {
            "RETRY_NOW": 0.79,
            "WAIT_AND_RETRY": 0.1,
            "SEND_REMINDER": 0.1,
            "PAYMENT_LINK": 0.80,
            "UPDATE_PAYMENT_METHOD": 0.1,
        }
        dummy_model = DummyModel(prob_map=prob_map)
        model_features = ["amount", "candidate_action"]

        candidate_df = self.engine.generate_candidate_table(df, dummy_model, model_features)

        self.assertEqual(candidate_df.iloc[0]["candidate_action"], "PAYMENT_LINK")
        self.assertEqual(candidate_df.iloc[1]["candidate_action"], "RETRY_NOW")

        # Test alphabetical tie-breaker (Tier 5 candidate_action ASC) when net, gross, prob, amount are identical
        # Action A: RETRY_NOW (cost=2.0, prob=0.5 -> net=8.0) vs Action B: WAIT_AND_RETRY (cost=2.0, prob=0.5 -> net=8.0)
        df_alpha = pd.DataFrame([{
            "failure_id": "FAIL_TIE_ALPHA",
            "customer_id": "CUST_001",
            "amount": 20.0,
            "failure_reason": "NETWORK_ERROR",
            "behavior_profile": "normal",
        }])
        prob_alpha = {
            "RETRY_NOW": 0.5,       # gross=10.0, cost=2.0 -> net=8.0
            "WAIT_AND_RETRY": 0.5,  # gross=10.0, cost=2.0 -> net=8.0
            "SEND_REMINDER": 0.1,
            "PAYMENT_LINK": 0.1,
            "UPDATE_PAYMENT_METHOD": 0.1,
        }
        dummy_alpha_model = DummyModel(prob_map=prob_alpha)
        candidate_alpha_df = self.engine.generate_candidate_table(df_alpha, dummy_alpha_model, model_features)

        # RETRY_NOW comes before WAIT_AND_RETRY alphabetically
        self.assertEqual(candidate_alpha_df.iloc[0]["candidate_action"], "RETRY_NOW")
        self.assertEqual(candidate_alpha_df.iloc[1]["candidate_action"], "WAIT_AND_RETRY")


if __name__ == "__main__":
    unittest.main()
