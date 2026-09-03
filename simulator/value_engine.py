"""
RecoveryOS V2 — Milestone 1: Counterfactual Value Engine

Evaluates the economic value of every allowed intervention (5 active + STOP)
for every failed payment and selects the action maximizing expected net recovery.
"""

from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from simulator.config import ACTION_COSTS, ACTIVE_ACTIONS, ALL_ACTIONS

ACTIONS = ALL_ACTIONS


class CounterfactualValueEngine:
    def __init__(self, action_costs: Optional[Dict[str, float]] = None):
        self.action_costs = action_costs or ACTION_COSTS

    def evaluate_candidate_action(
        self,
        amount: float,
        candidate_action: str,
        probability: float
    ) -> Dict[str, float]:
        """
        Calculates economic value metrics for a single candidate action.
        Validates input boundaries.
        """
        if amount < 0:
            raise ValueError(f"Invalid payment amount: {amount}. Must be >= 0.")
        
        if candidate_action == "STOP":
            prob = 0.0
            cost = 0.0
            gross = 0.0
            net = 0.0
        else:
            if candidate_action not in self.action_costs:
                raise ValueError(f"Unknown candidate action: {candidate_action}")
            if not (0.0 <= probability <= 1.0):
                raise ValueError(f"Invalid recovery probability: {probability}. Must be in [0, 1].")
            prob = float(probability)
            cost = float(self.action_costs[candidate_action])
            gross = float(amount * prob)
            net = float(gross - cost)

        return {
            "estimated_recovery_probability": prob,
            "intervention_cost": cost,
            "expected_gross_recovery": gross,
            "expected_net_recovery": net,
        }

    def generate_candidate_table(
        self,
        features_df: pd.DataFrame,
        model: Any,
        model_features: List[str]
    ) -> pd.DataFrame:
        """
        Expands input failure features across all 6 candidate actions (5 active + STOP),
        uses the ML model to predict probabilities for active actions,
        calculates economic values, and sorts candidates deterministically.
        """
        if "failure_id" not in features_df.columns:
            raise ValueError("Input dataframe must contain 'failure_id'")
        if "amount" not in features_df.columns:
            raise ValueError("Input dataframe must contain 'amount'")
        if features_df["failure_id"].duplicated().any():
            raise ValueError("Input dataframe contains duplicate failure_id records")

        # Sanity check: Ensure true_recovery_probability is NOT in inference features
        forbidden_features = ["true_recovery_probability", "oracle_probability", "recovered"]
        for forbidden in forbidden_features:
            if forbidden in features_df.columns:
                raise ValueError(
                    f"Data isolation violation: '{forbidden}' must NOT be present in inference features!"
                )

        candidate_rows = []

        # 1. Expand active actions for model inference
        for _, row in features_df.iterrows():
            for action in ACTIVE_ACTIONS:
                c_row = row.copy()
                c_row["candidate_action"] = action
                candidate_rows.append(c_row)

        active_candidate_df = pd.DataFrame(candidate_rows)

        # 2. Model prediction on active actions
        X = active_candidate_df[model_features]
        predicted_probs = model.predict_proba(X)[:, 1]
        active_candidate_df["estimated_recovery_probability"] = predicted_probs

        # 3. Calculate economic metrics for active actions
        active_candidate_df["intervention_cost"] = active_candidate_df["candidate_action"].map(self.action_costs)
        active_candidate_df["expected_gross_recovery"] = active_candidate_df["amount"] * active_candidate_df["estimated_recovery_probability"]
        active_candidate_df["expected_net_recovery"] = active_candidate_df["expected_gross_recovery"] - active_candidate_df["intervention_cost"]

        # 4. Generate STOP candidate rows for every failure
        stop_rows = []
        for _, row in features_df.iterrows():
            s_row = row.copy()
            s_row["candidate_action"] = "STOP"
            s_row["estimated_recovery_probability"] = 0.0
            s_row["intervention_cost"] = 0.0
            s_row["expected_gross_recovery"] = 0.0
            s_row["expected_net_recovery"] = 0.0
            stop_rows.append(s_row)

        stop_candidate_df = pd.DataFrame(stop_rows)

        # 5. Combine active actions and STOP into full candidate table
        full_candidate_df = pd.concat([active_candidate_df, stop_candidate_df], ignore_index=True)

        # 6. Apply deterministic sorting
        # Tie-break order:
        # 1. expected_net_recovery DESC
        # 2. expected_gross_recovery DESC
        # 3. estimated_recovery_probability DESC
        # 4. amount DESC
        # 5. candidate_action ASC
        full_candidate_df = full_candidate_df.sort_values(
            by=[
                "failure_id",
                "expected_net_recovery",
                "expected_gross_recovery",
                "estimated_recovery_probability",
                "amount",
                "candidate_action",
            ],
            ascending=[True, False, False, False, False, True],
        ).reset_index(drop=True)

        # 7. Assign rank per failure (1 to 6)
        full_candidate_df["rank"] = full_candidate_df.groupby("failure_id").cumcount() + 1

        return full_candidate_df

    def select_best_decisions(self, candidate_table_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts the top-ranked candidate action (rank 1) per failure_id.
        """
        best_df = candidate_table_df[candidate_table_df["rank"] == 1].copy().reset_index(drop=True)
        return best_df
