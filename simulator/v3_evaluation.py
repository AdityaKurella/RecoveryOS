"""
RecoveryOS V3 — System Evaluation Benchmark Runner

Compares:
1. V1 RecoveryOS Baseline
2. V2 Counterfactual Value Engine
3. V3 Promoted Uncertainty-Aware Hybrid Policy (Threshold ₹35)
4. Failure-Aware Rules Baseline
5. Oracle Ceiling

All strategies evaluated against ground-truth counterfactual environment (`gt_map`).
Strict Data Isolation: Ground-truth true probabilities are used ONLY in evaluation, NEVER in inference.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pickle
import gzip
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.baseline_strategies import failure_aware_rules, ACTION_COSTS
from simulator.value_engine import CounterfactualValueEngine

TEST_PATH = BASE_DIR / "data" / "test_features.csv"
GROUND_TRUTH_PATH = BASE_DIR / "data" / "counterfactual_training.csv"
V2_MODEL_PATH = BASE_DIR / "data" / "recovery_probability" / "counterfactual_model.pkl.gz"

MODEL_FEATURES = [
    "amount", "account_age_days", "successful_payments", "failed_payments",
    "total_payments", "payment_success_rate", "historical_recovery_rate",
    "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
]


def load_model_from_path(path: Path):
    if not path.exists():
        return None
    with gzip.open(path, "rb") as f:
        bundle = pickle.load(f)
        return bundle["model"] if isinstance(bundle, dict) and "model" in bundle else bundle


def load_gt_lookup(gt_df: pd.DataFrame) -> dict:
    gt_map = {}
    for _, row in gt_df.iterrows():
        key = (str(row["failure_id"]), str(row["candidate_action"]))
        gt_map[key] = {
            "true_prob": float(row["true_recovery_probability"]),
            "net_val": float(row["expected_net_value"]),
        }
    return gt_map


def run_v3_benchmark_evaluation():
    print("\n======================================================================")
    print("RECOVERYOS V3 — SYSTEM EVALUATION BENCHMARK")
    print("======================================================================")

    test_df = pd.read_csv(TEST_PATH)
    gt_df = pd.read_csv(GROUND_TRUTH_PATH)
    gt_map = load_gt_lookup(gt_df)
    engine = CounterfactualValueEngine()

    v2_model = load_model_from_path(V2_MODEL_PATH)
    total_failures = len(test_df)
    total_revenue_at_risk = test_df["amount"].sum()

    # 1. V2 Policy Selection
    v2_cand_df = engine.generate_candidate_table(test_df, v2_model, MODEL_FEATURES)
    v2_dec_df = engine.select_best_decisions(v2_cand_df)

    # Evaluate V2 on Ground Truth
    v2_rows = []
    for _, row in v2_dec_df.iterrows():
        fid, act, amt = str(row["failure_id"]), str(row["candidate_action"]), float(row["amount"])
        if act == "STOP":
            prob, cost, gross, net = 0.0, 0.0, 0.0, 0.0
        else:
            key = (fid, act)
            prob = gt_map[key]["true_prob"] if key in gt_map else 0.0
            cost = ACTION_COSTS.get(act, 0.0)
            gross = amt * prob
            net = gross - cost
        v2_rows.append({"gross": gross, "cost": cost, "net": net, "action": act})
    v2_res = pd.DataFrame(v2_rows)

    # 2. V3 Promoted Hybrid Policy Selection (Threshold ₹35)
    v3_hybrid_rows = []
    v3_hybrid_actions = []
    threshold = 35.0

    for _, test_row in test_df.iterrows():
        fid = str(test_row["failure_id"])
        amt = float(test_row["amount"])

        sub = v2_cand_df[v2_cand_df["failure_id"].astype(str) == fid].sort_values("expected_net_recovery", ascending=False)
        top1 = sub.iloc[0]
        top2 = sub.iloc[1] if len(sub) > 1 else top1

        ml_act = str(top1["candidate_action"])
        margin = float(top1["expected_net_recovery"]) - float(top2["expected_net_recovery"])

        if margin < threshold:
            act = failure_aware_rules(test_row)
        else:
            act = ml_act

        v3_hybrid_actions.append(act)

        if act == "STOP":
            prob, cost, gross, net = 0.0, 0.0, 0.0, 0.0
        else:
            key = (fid, act)
            prob = gt_map[key]["true_prob"] if key in gt_map else 0.0
            cost = ACTION_COSTS.get(act, 0.0)
            gross = amt * prob
            net = gross - cost
        v3_hybrid_rows.append({"failure_id": fid, "gross": gross, "cost": cost, "net": net, "action": act})
    v3_res = pd.DataFrame(v3_hybrid_rows)

    # 3. Evaluate Failure-Aware Rules on Ground Truth
    rules_rows = []
    for _, row in test_df.iterrows():
        fid, amt = str(row["failure_id"]), float(row["amount"])
        act = failure_aware_rules(row)
        key = (fid, act)
        prob = gt_map[key]["true_prob"] if key in gt_map else 0.0
        cost = ACTION_COSTS.get(act, 0.0)
        gross = amt * prob
        net = gross - cost
        rules_rows.append({"failure_id": fid, "gross": gross, "cost": cost, "net": net, "action": act})
    rules_res = pd.DataFrame(rules_rows)

    # 4. Evaluate Oracle Upper Bound on Ground Truth
    test_fids = set(test_df["failure_id"].astype(str))
    oracle_rows = []
    oracle_map = {}
    for fid, group in gt_df.groupby("failure_id"):
        if str(fid) in test_fids:
            best_row = group.sort_values("expected_net_value", ascending=False).iloc[0]
            amt = float(best_row["amount"])
            act = str(best_row["candidate_action"])
            prob = float(best_row["true_recovery_probability"])
            cost = ACTION_COSTS.get(act, 0.0)
            gross = amt * prob
            net = gross - cost
            oracle_rows.append({"failure_id": str(fid), "gross": gross, "cost": cost, "net": net, "action": act})
            oracle_map[str(fid)] = act
    oracle_res = pd.DataFrame(oracle_rows)

    table_data = {
        "Metric": [
            "Cases evaluated",
            "Revenue at risk (₹)",
            "Expected gross recovery (₹)",
            "Intervention cost (₹)",
            "Expected NET recovery (₹)",
            "Recovery rate (%)",
        ],
        "V1 Historical Reference": [
            f"{total_failures}",
            f"{total_revenue_at_risk:,.2f}",
            f"{843404.27:,.2f}",
            f"{1354.00:,.2f}",
            f"{842050.27:,.2f}",
            f"{77.34}%",
        ],
        "V2 Engine": [
            f"{total_failures}",
            f"{total_revenue_at_risk:,.2f}",
            f"{v2_res['gross'].sum():,.2f}",
            f"{v2_res['cost'].sum():,.2f}",
            f"{v2_res['net'].sum():,.2f}",
            f"{(v2_res['gross'].sum() / total_revenue_at_risk)*100:.2f}%",
        ],
        "V3 Hybrid Policy (Promoted)": [
            f"{total_failures}",
            f"{total_revenue_at_risk:,.2f}",
            f"{v3_res['gross'].sum():,.2f}",
            f"{v3_res['cost'].sum():,.2f}",
            f"{v3_res['net'].sum():,.2f}",
            f"{(v3_res['gross'].sum() / total_revenue_at_risk)*100:.2f}%",
        ],
        "Failure-Aware Rules": [
            f"{total_failures}",
            f"{total_revenue_at_risk:,.2f}",
            f"{rules_res['gross'].sum():,.2f}",
            f"{rules_res['cost'].sum():,.2f}",
            f"{rules_res['net'].sum():,.2f}",
            f"{(rules_res['gross'].sum() / total_revenue_at_risk)*100:.2f}%",
        ],
        "Oracle Upper Bound": [
            f"{total_failures}",
            f"{total_revenue_at_risk:,.2f}",
            f"{oracle_res['gross'].sum():,.2f}",
            f"{oracle_res['cost'].sum():,.2f}",
            f"{oracle_res['net'].sum():,.2f}",
            f"{(oracle_res['gross'].sum() / total_revenue_at_risk)*100:.2f}%",
        ],
    }

    results_df = pd.DataFrame(table_data)
    print(results_df.to_string(index=False))

    # Calculate Oracle Action Match for V3 Promoted by Failure ID key
    v3_oracle_matches = sum(1 for _, row in v3_res.iterrows() if row["action"] == oracle_map.get(row["failure_id"]))
    v3_oracle_match_pct = (v3_oracle_matches / total_failures) * 100

    v2_net = v2_res['net'].sum()
    v3_net = v3_res['net'].sum()
    rules_net = rules_res['net'].sum()
    oracle_net = oracle_res['net'].sum()

    print("\n----------------------------------------------------------------------")
    print("KEY PERFORMANCE COMPARISONS:")
    print("----------------------------------------------------------------------")
    print(f"V2 Expected Net Recovery:         ₹{v2_net:,.2f}")
    print(f"V3 Hybrid Expected Net Recovery:  ₹{v3_net:,.2f}")
    print(f"Rules Expected Net Recovery:      ₹{rules_net:,.2f}")
    print(f"Oracle Expected Net Recovery:     ₹{oracle_net:,.2f}")

    print(f"\nV3 vs V2 Net Difference:        ₹{v3_net - v2_net:+,.2f} ({(v3_net - v2_net)/v2_net * 100:+.2f}%)")
    print(f"V3 vs Rules Net Difference:     ₹{v3_net - rules_net:+,.2f} ({(v3_net - rules_net)/rules_net * 100:+.2f}%)")
    print(f"V3 Oracle Opportunity Gap:       ₹{oracle_net - v3_net:,.2f} ({(oracle_net - v3_net)/oracle_net * 100:.2f}%)")
    print(f"V3 Oracle Action Match %:        {v3_oracle_match_pct:.2f}% ({v3_oracle_matches}/{total_failures})")

    # Save standard summary CSV for API / Dashboard
    summary_path = BASE_DIR / "data" / "evaluation" / "recoveryos_evaluation_summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df = pd.DataFrame([
        {"metric": "Cases evaluated", "recoveryos": float(total_failures), "rules": float(total_failures), "oracle": float(total_failures)},
        {"metric": "Revenue at risk", "recoveryos": round(float(total_revenue_at_risk), 2), "rules": round(float(total_revenue_at_risk), 2), "oracle": round(float(total_revenue_at_risk), 2)},
        {"metric": "Actual recovered revenue (simulated)", "recoveryos": round(float(v3_res['gross'].sum()), 2), "rules": round(float(rules_res['gross'].sum()), 2), "oracle": round(float(oracle_res['gross'].sum()), 2)},
        {"metric": "Intervention cost", "recoveryos": round(float(v3_res['cost'].sum()), 2), "rules": round(float(rules_res['cost'].sum()), 2), "oracle": round(float(oracle_res['cost'].sum()), 2)},
        {"metric": "Net recovered revenue (simulated)", "recoveryos": round(float(v3_net), 2), "rules": round(float(rules_net), 2), "oracle": round(float(oracle_net), 2)},
        {"metric": "Recovery rate %", "recoveryos": round((v3_res['gross'].sum() / total_revenue_at_risk)*100, 2), "rules": round((rules_res['gross'].sum() / total_revenue_at_risk)*100, 2), "oracle": round((oracle_res['gross'].sum() / total_revenue_at_risk)*100, 2)},
        {"metric": "RecoveryOS vs Rules net", "recoveryos": round(v3_net - rules_net, 2), "rules": 0.0, "oracle": 0.0},
        {"metric": "RecoveryOS vs Oracle net", "recoveryos": round(v3_net - oracle_net, 2), "rules": 0.0, "oracle": 0.0},
        {"metric": "RecoveryOS oracle action match %", "recoveryos": round(v3_oracle_match_pct, 2), "rules": 0.0, "oracle": 100.0},
        {"metric": "Oracle opportunity gap %", "recoveryos": round(((oracle_net - v3_net) / oracle_net)*100, 2), "rules": 0.0, "oracle": 0.0},
    ])
    summary_df.to_csv(summary_path, index=False)

    return results_df


if __name__ == "__main__":
    run_v3_benchmark_evaluation()
