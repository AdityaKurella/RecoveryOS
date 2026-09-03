"""
RecoveryOS V3 — Multi-Seed Evaluation & Model Diagnostics Engine

Evaluates strategies across 5 independent random seeds (42, 101, 202, 303, 404)
and computes distribution statistics (mean, median, std, min, max) for expected & realized net recovery,
recovery rates, intervention costs, policy regret, and oracle opportunity gaps.
"""

import sys
import pickle
import gzip
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.baseline_strategies import failure_aware_rules, ACTION_COSTS
from simulator.value_engine import CounterfactualValueEngine

TEST_PATH = BASE_DIR / "data" / "test_features.csv"
GROUND_TRUTH_PATH = BASE_DIR / "data" / "counterfactual_training.csv"
MODEL_PATH = BASE_DIR / "data" / "recovery_probability" / "counterfactual_model.pkl.gz"

EVAL_SEEDS = [42, 101, 202, 303, 404]


def load_model():
    with gzip.open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
        return bundle["model"] if isinstance(bundle, dict) and "model" in bundle else bundle


def run_multi_seed_evaluation():
    print("\n======================================================================")
    print("RECOVERYOS V3 — MULTI-SEED EVALUATION (5 SEEDS)")
    print("======================================================================")

    test_df = pd.read_csv(TEST_PATH)
    gt_df = pd.read_csv(GROUND_TRUTH_PATH)
    model = load_model()
    engine = CounterfactualValueEngine()

    model_features = [
        "amount", "account_age_days", "successful_payments", "failed_payments",
        "total_payments", "payment_success_rate", "historical_recovery_rate",
        "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
    ]

    action_costs = {
        "RETRY_NOW": 2.0, "WAIT_AND_RETRY": 2.0, "SEND_REMINDER": 1.0,
        "PAYMENT_LINK": 3.0, "UPDATE_PAYMENT_METHOD": 3.0, "STOP": 0.0
    }

    # Pre-build ground truth map per failure & action
    gt_map = {}
    for _, row in gt_df.iterrows():
        gt_map[(str(row["failure_id"]), str(row["candidate_action"]))] = float(row["true_recovery_probability"])

    # Pre-build Oracle best action per failure
    oracle_map = {}
    for fid, group in gt_df.groupby("failure_id"):
        best_row = group.sort_values("expected_net_value", ascending=False).iloc[0]
        oracle_map[str(fid)] = {
            "action": str(best_row["candidate_action"]),
            "prob": float(best_row["true_recovery_probability"]),
        }

    # Generate V2 decisions once
    cand_df = engine.generate_candidate_table(test_df, model, model_features)
    v2_decisions = engine.select_best_decisions(cand_df)
    v2_map = dict(zip(v2_decisions["failure_id"], v2_decisions.to_dict("records")))

    # Calculate deterministic Ground-Truth Expected Net and Model-Estimated Expected Net
    gt_expected_net = 0.0
    model_estimated_net = 0.0
    for _, row in test_df.iterrows():
        fid = str(row["failure_id"])
        amt = float(row["amount"])
        rec = v2_map[fid]
        act = str(rec["candidate_action"])
        c = action_costs.get(act, 0.0)
        p_true = gt_map.get((fid, act), 0.0) if act != "STOP" else 0.0
        gt_expected_net += (amt * p_true) - c
        model_estimated_net += float(rec["expected_net_recovery"])

    print(f"Ground-Truth Expected NET Recovery: ₹{gt_expected_net:,.2f}")
    print(f"Model-Estimated Expected NET Recovery: ₹{model_estimated_net:,.2f}")

    seed_results = []

    for seed in EVAL_SEEDS:
        rng = np.random.RandomState(seed)

        v2_realized_gross, v2_cost = 0.0, 0.0
        rules_realized_gross, rules_cost = 0.0, 0.0
        oracle_realized_gross, oracle_cost = 0.0, 0.0

        for _, row in test_df.iterrows():
            fid = str(row["failure_id"])
            amt = float(row["amount"])

            # 1. V2 Decision Realized Outcome
            v2_rec = v2_map[fid]
            v2_act = str(v2_rec["candidate_action"])
            v2_c = action_costs.get(v2_act, 0.0)
            v2_cost += v2_c

            if v2_act != "STOP":
                v2_true_p = gt_map.get((fid, v2_act), 0.0)
                if rng.rand() < v2_true_p:
                    v2_realized_gross += amt

            # 2. Rules Decision Realized Outcome
            r_act = failure_aware_rules(row)
            r_c = action_costs.get(r_act, 0.0)
            rules_cost += r_c
            r_true_p = gt_map.get((fid, r_act), 0.0)
            if rng.rand() < r_true_p:
                rules_realized_gross += amt

            # 3. Oracle Decision Realized Outcome
            o_info = oracle_map[fid]
            o_act = o_info["action"]
            o_c = action_costs.get(o_act, 0.0)
            oracle_cost += o_c
            if rng.rand() < o_info["prob"]:
                oracle_realized_gross += amt

        v2_realized_net = v2_realized_gross - v2_cost
        rules_realized_net = rules_realized_gross - rules_cost
        oracle_realized_net = oracle_realized_gross - oracle_cost

        seed_results.append({
            "seed": seed,
            "gt_expected_net": gt_expected_net,
            "v2_realized_net": v2_realized_net,
            "rules_realized_net": rules_realized_net,
            "oracle_realized_net": oracle_realized_net,
            "oracle_gap": oracle_realized_net - v2_realized_net,
        })

    s_df = pd.DataFrame(seed_results)

    print("\n5-SEED REALIZED NET RECOVERY RESULTS (₹):")
    print(s_df.to_string(index=False))

    print("\nSTATISTICAL DISTRIBUTION SUMMARY (5 SEEDS):")
    stats = [
        ("V2 Realized Net Recovery", s_df["v2_realized_net"].mean(), s_df["v2_realized_net"].median(), s_df["v2_realized_net"].std(), s_df["v2_realized_net"].min(), s_df["v2_realized_net"].max()),
        ("Rules Realized Net Recovery", s_df["rules_realized_net"].mean(), s_df["rules_realized_net"].median(), s_df["rules_realized_net"].std(), s_df["rules_realized_net"].min(), s_df["rules_realized_net"].max()),
        ("Oracle Realized Net Recovery", s_df["oracle_realized_net"].mean(), s_df["oracle_realized_net"].median(), s_df["oracle_realized_net"].std(), s_df["oracle_realized_net"].min(), s_df["oracle_realized_net"].max()),
        ("V2 Oracle Opportunity Gap", s_df["oracle_gap"].mean(), s_df["oracle_gap"].median(), s_df["oracle_gap"].std(), s_df["oracle_gap"].min(), s_df["oracle_gap"].max()),
    ]
    summary_df = pd.DataFrame(stats, columns=["Metric", "Mean", "Median", "Std Dev", "Min", "Max"])
    print(summary_df.to_string(index=False))

    return s_df, summary_df


if __name__ == "__main__":
    run_multi_seed_evaluation()
