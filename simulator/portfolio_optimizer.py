"""
RecoveryOS V2 — Milestone 3: Portfolio Optimization Engine

Ranks candidate recovery decisions across the entire portfolio to maximize total expected net recovery
subject to intervention capacity constraints (K), budget constraints (B), and customer policy limits.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from simulator.config import DEFAULT_PORTFOLIO_CAPACITY, ACTION_COSTS


class PortfolioOptimizer:
    def __init__(
        self,
        capacity: int = DEFAULT_PORTFOLIO_CAPACITY,
        max_budget: Optional[float] = None,
        max_actions_per_customer: Optional[int] = None,
    ):
        self.capacity = capacity
        self.max_budget = max_budget
        self.max_actions_per_customer = max_actions_per_customer

    def optimize_portfolio(
        self,
        candidate_table_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Optimizes recovery across the entire portfolio under capacity K.

        Process:
        1. Takes the rank 1 (best unconstrained) candidate decision for each failure.
        2. Ranks active intervention decisions across the entire portfolio by expected_net_recovery DESC.
        3. Selects top K active interventions within capacity limit K (and budget limit B if set).
        4. Cases exceeding capacity K fall back to 'STOP' (or un-selected status).

        Returns DataFrame containing all failure decisions with columns:
        - failure_id, customer_id, amount, failure_reason, candidate_action
        - estimated_recovery_probability, intervention_cost, expected_gross_recovery, expected_net_recovery
        - portfolio_rank, portfolio_selected, portfolio_status
        """
        if candidate_table_df.empty:
            return pd.DataFrame()

        # 1. Filter rank 1 decisions per failure
        rank1_df = candidate_table_df[candidate_table_df["rank"] == 1].copy()

        # Separate active intervention decisions vs STOP decisions
        active_mask = rank1_df["candidate_action"] != "STOP"
        active_decisions = rank1_df[active_mask].copy()
        stop_decisions = rank1_df[~active_mask].copy()

        # Sort active decisions globally by expected_net_recovery DESC
        active_decisions = active_decisions.sort_values(
            by=[
                "expected_net_recovery",
                "expected_gross_recovery",
                "estimated_recovery_probability",
                "amount",
                "candidate_action",
            ],
            ascending=[False, False, False, False, True]
        ).reset_index(drop=True)

        # Apply customer-level action limits if specified
        selected_active_rows = []
        fallback_stop_rows = []
        customer_counts: Dict[str, int] = {}
        cum_cost = 0.0

        for _, row in active_decisions.iterrows():
            cid = str(row.get("customer_id", ""))
            cost = float(row["intervention_cost"])

            # Check customer limit
            if self.max_actions_per_customer is not None:
                if customer_counts.get(cid, 0) >= self.max_actions_per_customer:
                    fallback = row.copy()
                    fallback["candidate_action"] = "STOP"
                    fallback["estimated_recovery_probability"] = 0.0
                    fallback["intervention_cost"] = 0.0
                    fallback["expected_gross_recovery"] = 0.0
                    fallback["expected_net_recovery"] = 0.0
                    fallback_stop_rows.append(fallback)
                    continue

            # Check budget limit
            if self.max_budget is not None and (cum_cost + cost) > self.max_budget:
                fallback = row.copy()
                fallback["candidate_action"] = "STOP"
                fallback["estimated_recovery_probability"] = 0.0
                fallback["intervention_cost"] = 0.0
                fallback["expected_gross_recovery"] = 0.0
                fallback["expected_net_recovery"] = 0.0
                fallback_stop_rows.append(fallback)
                continue

            # Check capacity K
            if len(selected_active_rows) < self.capacity:
                selected_active_rows.append(row)
                customer_counts[cid] = customer_counts.get(cid, 0) + 1
                cum_cost += cost
            else:
                fallback = row.copy()
                fallback["candidate_action"] = "STOP"
                fallback["estimated_recovery_probability"] = 0.0
                fallback["intervention_cost"] = 0.0
                fallback["expected_gross_recovery"] = 0.0
                fallback["expected_net_recovery"] = 0.0
                fallback_stop_rows.append(fallback)

        selected_active_df = pd.DataFrame(selected_active_rows)
        fallback_stop_df = pd.DataFrame(fallback_stop_rows)

        if not selected_active_df.empty:
            selected_active_df["portfolio_rank"] = np.arange(1, len(selected_active_df) + 1)
            selected_active_df["portfolio_selected"] = True
            selected_active_df["portfolio_status"] = "SELECTED_IN_CAPACITY"

        if not fallback_stop_df.empty:
            fallback_stop_df["portfolio_rank"] = 0
            fallback_stop_df["portfolio_selected"] = False
            fallback_stop_df["portfolio_status"] = "EXCEEDED_CAPACITY_FALLBACK_STOP"

        if not stop_decisions.empty:
            stop_decisions["portfolio_rank"] = 0
            stop_decisions["portfolio_selected"] = True
            stop_decisions["portfolio_status"] = "UNCONSTRAINED_STOP"

        final_portfolio_df = pd.concat(
            [selected_active_df, fallback_stop_df, stop_decisions],
            ignore_index=True
        ).sort_values(by="failure_id").reset_index(drop=True)

        return final_portfolio_df
