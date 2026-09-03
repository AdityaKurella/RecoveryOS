"""
RecoveryOS V3 — Ablation Study Runner

Measures incremental contribution of each component:
1. V2 Baseline Engine
2. Unconstrained V3 Model (K = ∞)
3. Constrained Portfolio Optimization (K = 100)
4. Full V3 Platform with Safety Guardrails & Persistence
"""

import sys
import pickle
import gzip
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.config import SystemConfig
from simulator.value_engine import CounterfactualValueEngine
from simulator.portfolio_optimizer import PortfolioOptimizer
from simulator.event_runtime import SafetyPolicyEngine

TEST_PATH = BASE_DIR / "data" / "test_features.csv"
GROUND_TRUTH_PATH = BASE_DIR / "data" / "counterfactual_training.csv"
V2_MODEL_PATH = BASE_DIR / "data" / "recovery_probability" / "counterfactual_model.pkl.gz"

MODEL_FEATURES = [
    "amount", "account_age_days", "successful_payments", "failed_payments",
    "total_payments", "payment_success_rate", "historical_recovery_rate",
    "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
]


def load_model():
    with gzip.open(V2_MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
        return bundle["model"] if isinstance(bundle, dict) and "model" in bundle else bundle


def run_ablation_study():
    print("\n======================================================================")
    print("RECOVERYOS V3 — ABLATION STUDY RESULTS")
    print("======================================================================")

    test_df = pd.read_csv(TEST_PATH)
    model = load_model()
    value_engine = CounterfactualValueEngine()
    safety_engine = SafetyPolicyEngine()

    cand_df = value_engine.generate_candidate_table(test_df, model, MODEL_FEATURES)

    # Ablation 1: Unconstrained Value Engine (Rank 1)
    unconstrained_df = value_engine.select_best_decisions(cand_df)
    u_gross = unconstrained_df["expected_gross_recovery"].sum()
    u_cost = unconstrained_df["intervention_cost"].sum()
    u_net = unconstrained_df["expected_net_recovery"].sum()

    # Ablation 2: Constrained Portfolio Optimization (Capacity K = 100)
    opt = PortfolioOptimizer(capacity=100)
    portfolio_df = opt.optimize_portfolio(cand_df)
    p_selected = portfolio_df[portfolio_df["portfolio_selected"] == True]
    p_gross = p_selected["expected_gross_recovery"].sum()
    p_cost = p_selected["intervention_cost"].sum()
    p_net = p_selected["expected_net_recovery"].sum()

    # Ablation 3: Full V3 System (Portfolio K = 100 + Safety Guardrails)
    s_rows = []
    for _, row in p_selected.iterrows():
        policy_res = safety_engine.evaluate_policy(row.to_dict())
        row_dict = row.to_dict()
        row_dict["policy_result"] = policy_res["policy_result"]
        s_rows.append(row_dict)
    s_df = pd.DataFrame(s_rows)
    s_allow = s_df[s_df["policy_result"] == "ALLOW"]
    s_gross = s_allow["expected_gross_recovery"].sum()
    s_cost = s_allow["intervention_cost"].sum()
    s_net = s_allow["expected_net_recovery"].sum()

    ablation_data = [
        ("Ablation 1: Unconstrained Value Engine (K=∞)", len(unconstrained_df), f"₹{u_gross:,.2f}", f"₹{u_cost:,.2f}", f"₹{u_net:,.2f}"),
        ("Ablation 2: Portfolio Optimizer (Capacity K=100)", len(p_selected), f"₹{p_gross:,.2f}", f"₹{p_cost:,.2f}", f"₹{p_net:,.2f}"),
        ("Ablation 3: Full System (K=100 + Safety Guardrails)", len(s_allow), f"₹{s_gross:,.2f}", f"₹{s_cost:,.2f}", f"₹{s_net:,.2f}"),
    ]

    res_df = pd.DataFrame(ablation_data, columns=["Ablation Scenario", "Dispatched Cases", "Expected Gross", "Cost", "Expected NET"])
    print(res_df.to_string(index=False))

    return res_df


if __name__ == "__main__":
    run_ablation_study()
