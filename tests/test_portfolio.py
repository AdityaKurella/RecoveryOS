"""
Unit Tests for Milestone 3 Portfolio Optimization Engine
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.portfolio_optimizer import PortfolioOptimizer


class TestPortfolioOptimizer(unittest.TestCase):

    def test_capacity_k_enforcement(self):
        # Create 10 failure candidate rows
        rows = []
        for i in range(1, 11):
            fid = f"FAIL_{i:03d}"
            rows.append({
                "failure_id": fid,
                "customer_id": f"CUST_{i:03d}",
                "amount": 1000.0,
                "failure_reason": "INSUFFICIENT_FUNDS",
                "candidate_action": "RETRY_NOW",
                "estimated_recovery_probability": 0.8,
                "intervention_cost": 2.0,
                "expected_gross_recovery": 800.0,
                "expected_net_recovery": 798.0 - i,  # Varying net recovery
                "rank": 1,
            })
        candidate_df = pd.DataFrame(rows)

        # Set capacity K = 5
        optimizer = PortfolioOptimizer(capacity=5)
        portfolio_df = optimizer.optimize_portfolio(candidate_df)

        selected_active = portfolio_df[portfolio_df["portfolio_status"] == "SELECTED_IN_CAPACITY"]
        fallback_stop = portfolio_df[portfolio_df["portfolio_status"] == "EXCEEDED_CAPACITY_FALLBACK_STOP"]

        self.assertEqual(len(selected_active), 5)
        self.assertEqual(len(fallback_stop), 5)

        # Verify top 5 net recoveries were selected
        selected_nets = selected_active["expected_net_recovery"].tolist()
        self.assertEqual(selected_nets, [797.0, 796.0, 795.0, 794.0, 793.0])

    def test_max_actions_per_customer_limit(self):
        rows = [
            {"failure_id": "FAIL_001", "customer_id": "CUST_C1", "amount": 1000.0, "candidate_action": "PAYMENT_LINK", "estimated_recovery_probability": 0.8, "intervention_cost": 3.0, "expected_gross_recovery": 800.0, "expected_net_recovery": 797.0, "rank": 1},
            {"failure_id": "FAIL_002", "customer_id": "CUST_C1", "amount": 1000.0, "candidate_action": "PAYMENT_LINK", "estimated_recovery_probability": 0.8, "intervention_cost": 3.0, "expected_gross_recovery": 800.0, "expected_net_recovery": 796.0, "rank": 1},
        ]
        candidate_df = pd.DataFrame(rows)

        # Restrict customer C1 to max 1 action
        optimizer = PortfolioOptimizer(capacity=10, max_actions_per_customer=1)
        portfolio_df = optimizer.optimize_portfolio(candidate_df)

        selected_active = portfolio_df[portfolio_df["portfolio_status"] == "SELECTED_IN_CAPACITY"]
        self.assertEqual(len(selected_active), 1)
        self.assertEqual(selected_active.iloc[0]["failure_id"], "FAIL_001")

    def test_max_budget_cumulative_constraint(self):
        # Create 5 failure rows each costing ₹3.0 (total ₹15.0 if all selected)
        rows = []
        for i in range(1, 6):
            rows.append({
                "failure_id": f"FAIL_BUDGET_{i:03d}",
                "customer_id": f"CUST_{i:03d}",
                "amount": 1000.0,
                "candidate_action": "PAYMENT_LINK",
                "estimated_recovery_probability": 0.8,
                "intervention_cost": 3.0,
                "expected_gross_recovery": 800.0,
                "expected_net_recovery": 797.0 - i,
                "rank": 1,
            })
        candidate_df = pd.DataFrame(rows)

        # Set max_budget = ₹7.0 (allows max 2 actions @ ₹3.0 each = ₹6.0)
        optimizer = PortfolioOptimizer(capacity=10, max_budget=7.0)
        portfolio_df = optimizer.optimize_portfolio(candidate_df)

        selected_active = portfolio_df[portfolio_df["portfolio_status"] == "SELECTED_IN_CAPACITY"]
        self.assertEqual(len(selected_active), 2)
        total_cost = selected_active["intervention_cost"].sum()
        self.assertEqual(total_cost, 6.0)
        self.assertLessEqual(total_cost, 7.0)

    def test_empty_portfolio(self):
        optimizer = PortfolioOptimizer(capacity=10)
        res = optimizer.optimize_portfolio(pd.DataFrame())
        self.assertTrue(res.empty)

    def test_single_failure_capacity_zero(self):
        candidate_df = pd.DataFrame([{
            "failure_id": "FAIL_SINGLE_001",
            "customer_id": "CUST_001",
            "amount": 1000.0,
            "candidate_action": "PAYMENT_LINK",
            "estimated_recovery_probability": 0.8,
            "intervention_cost": 3.0,
            "expected_gross_recovery": 800.0,
            "expected_net_recovery": 797.0,
            "rank": 1,
        }])
        optimizer = PortfolioOptimizer(capacity=0)
        res = optimizer.optimize_portfolio(candidate_df)
        self.assertEqual(len(res), 1)
        self.assertEqual(res.iloc[0]["portfolio_status"], "EXCEEDED_CAPACITY_FALLBACK_STOP")
        self.assertFalse(res.iloc[0]["portfolio_selected"])
        self.assertEqual(res.iloc[0]["candidate_action"], "STOP")

    def test_budget_zero_forces_fallback_stop(self):
        candidate_df = pd.DataFrame([{
            "failure_id": "FAIL_B0",
            "customer_id": "CUST_B0",
            "amount": 1000.0,
            "candidate_action": "PAYMENT_LINK",
            "estimated_recovery_probability": 0.8,
            "intervention_cost": 3.0,
            "expected_gross_recovery": 800.0,
            "expected_net_recovery": 797.0,
            "rank": 1,
        }])
        optimizer = PortfolioOptimizer(capacity=10, max_budget=0.0)
        res = optimizer.optimize_portfolio(candidate_df)
        self.assertEqual(len(res), 1)
        self.assertEqual(res.iloc[0]["portfolio_status"], "EXCEEDED_CAPACITY_FALLBACK_STOP")
        self.assertFalse(res.iloc[0]["portfolio_selected"])

    def test_capacity_exceeds_available_cases(self):
        candidate_df = pd.DataFrame([{
            "failure_id": "FAIL_EXCEED_01",
            "customer_id": "CUST_01",
            "amount": 1000.0,
            "candidate_action": "RETRY_NOW",
            "estimated_recovery_probability": 0.8,
            "intervention_cost": 2.0,
            "expected_gross_recovery": 800.0,
            "expected_net_recovery": 798.0,
            "rank": 1,
        }])
        optimizer = PortfolioOptimizer(capacity=100)
        res = optimizer.optimize_portfolio(candidate_df)
        self.assertEqual(len(res), 1)
        self.assertTrue(res.iloc[0]["portfolio_selected"])
        self.assertEqual(res.iloc[0]["portfolio_status"], "SELECTED_IN_CAPACITY")

    def test_unconstrained_stop_decisions_handling(self):
        candidate_df = pd.DataFrame([{
            "failure_id": "FAIL_STOP_01",
            "customer_id": "CUST_01",
            "amount": 10.0,
            "candidate_action": "STOP",
            "estimated_recovery_probability": 0.0,
            "intervention_cost": 0.0,
            "expected_gross_recovery": 0.0,
            "expected_net_recovery": 0.0,
            "rank": 1,
        }])
        optimizer = PortfolioOptimizer(capacity=10)
        res = optimizer.optimize_portfolio(candidate_df)
        self.assertEqual(len(res), 1)
        self.assertEqual(res.iloc[0]["portfolio_status"], "UNCONSTRAINED_STOP")
        self.assertEqual(res.iloc[0]["candidate_action"], "STOP")


if __name__ == "__main__":
    unittest.main()
