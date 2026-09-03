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


if __name__ == "__main__":
    unittest.main()
