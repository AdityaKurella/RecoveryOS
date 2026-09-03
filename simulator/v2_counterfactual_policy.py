"""
RecoveryOS V2 — Milestone 1: Counterfactual Policy Optimizer

Uses CounterfactualValueEngine to evaluate all 6 candidate actions (5 active + STOP)
on 559 test cases and outputs structured candidate action tables and optimal policy decisions.
"""

import sys
import pickle
import gzip
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.value_engine import CounterfactualValueEngine

TEST_FEATURES_PATH = BASE_DIR / "data" / "test_features.csv"
MODEL_PATH = BASE_DIR / "data" / "recovery_probability" / "counterfactual_model.pkl.gz"
CANDIDATE_OUTPUT_PATH = BASE_DIR / "data" / "ml_decision" / "v2_candidate_action_values.csv"
DECISION_OUTPUT_PATH = BASE_DIR / "data" / "ml_decision" / "v2_policy_decisions.csv"

MODEL_FEATURES = [
    "amount",
    "account_age_days",
    "successful_payments",
    "failed_payments",
    "total_payments",
    "payment_success_rate",
    "historical_recovery_rate",
    "engagement_score",
    "failure_reason",
    "behavior_profile",
    "candidate_action",
]


def load_model(model_path: Path):
    if not model_path.exists():
        raw_path = model_path.with_suffix("")
        if raw_path.exists():
            with open(raw_path, "rb") as f:
                return pickle.load(f)
        raise FileNotFoundError(f"Model file not found at {model_path} or {raw_path}")

    with gzip.open(model_path, "rb") as f:
        bundle = pickle.load(f)
        return bundle["model"] if isinstance(bundle, dict) and "model" in bundle else bundle


def run_v2_policy():
    print("\n========== RECOVERYOS V2 — COUNTERFACTUAL POLICY OPTIMIZER ==========")
    test_df = pd.read_csv(TEST_FEATURES_PATH)
    print(f"Test cases loaded: {len(test_df)}")

    model = load_model(MODEL_PATH)
    print("M10F ExtraTrees Model loaded successfully.")

    engine = CounterfactualValueEngine()

    print("\n========== EVALUATING 6 CANDIDATE ACTIONS PER FAILURE ==========")
    candidate_df = engine.generate_candidate_table(
        features_df=test_df,
        model=model,
        model_features=MODEL_FEATURES,
    )

    print(f"Total candidate rows generated: {len(candidate_df)} (6 actions × {len(test_df)} failures)")

    # Select rank 1 decision per failure
    selected_df = engine.select_best_decisions(candidate_df)

    # Save output CSVs
    CANDIDATE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    candidate_df.to_csv(CANDIDATE_OUTPUT_PATH, index=False)
    selected_df.to_csv(DECISION_OUTPUT_PATH, index=False)

    revenue_at_risk = selected_df["amount"].sum()
    expected_gross = selected_df["expected_gross_recovery"].sum()
    intervention_cost = selected_df["intervention_cost"].sum()
    expected_net = selected_df["expected_net_recovery"].sum()
    recovery_rate = (expected_gross / revenue_at_risk * 100.0) if revenue_at_risk > 0 else 0.0

    print("\n========== V2 POLICY RESULTS SUMMARY ==========")
    print(f"Failures evaluated:           {len(selected_df)}")
    print(f"Revenue at risk:              ₹{revenue_at_risk:,.2f}")
    print(f"Expected gross recovery:      ₹{expected_gross:,.2f}")
    print(f"Intervention cost:            ₹{intervention_cost:,.2f}")
    print(f"Expected NET recovery:        ₹{expected_net:,.2f}")
    print(f"Expected recovery rate:       {recovery_rate:.2f}%")

    print("\nSelected action distribution:")
    action_counts = selected_df["candidate_action"].value_counts()
    for action in ["RETRY_NOW", "WAIT_AND_RETRY", "SEND_REMINDER", "PAYMENT_LINK", "UPDATE_PAYMENT_METHOD", "STOP"]:
        cnt = action_counts.get(action, 0)
        pct = (cnt / len(selected_df) * 100.0) if len(selected_df) > 0 else 0.0
        print(f"  {action:28s} {cnt:4d} ({pct:6.2f}%)")

    print(f"\nCandidate action table saved to: {CANDIDATE_OUTPUT_PATH}")
    print(f"V2 Policy decisions saved to:    {DECISION_OUTPUT_PATH}")
    print("\nV2 Counterfactual Policy Optimization Complete. ✅")

    return candidate_df, selected_df


if __name__ == "__main__":
    run_v2_policy()
