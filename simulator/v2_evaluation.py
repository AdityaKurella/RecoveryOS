"""
RecoveryOS V2 — Milestone 1 Benchmark Evaluation Script

Compares V1 RecoveryOS, V2 Counterfactual Value Engine, Failure-Aware Rules, and Oracle Benchmark
on the 559 test cases using ground-truth counterfactual data.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from simulator.baseline_strategies import failure_aware_rules, ACTION_COSTS

TEST_PATH = BASE_DIR / "data" / "test_features.csv"
GROUND_TRUTH_PATH = BASE_DIR / "data" / "counterfactual_training.csv"
V1_DECISIONS_PATH = BASE_DIR / "data" / "ml_decision" / "m10c_policy_decisions.csv"
V2_DECISIONS_PATH = BASE_DIR / "data" / "ml_decision" / "v2_policy_decisions.csv"


def load_gt_lookup(gt_df: pd.DataFrame):
    gt_map = {}
    for _, row in gt_df.iterrows():
        key = (str(row["failure_id"]), str(row["candidate_action"]))
        gt_map[key] = {
            "true_prob": float(row["true_recovery_probability"]),
            "expected_net": float(row["expected_net_value"]),
        }
    return gt_map


def run_evaluation_benchmark():
    print("\n======================================================================")
    print("RECOVERYOS V2 — MILESTONE 1 BENCHMARK EVALUATION")
    print("======================================================================")

    test_df = pd.read_csv(TEST_PATH)
    gt_df = pd.read_csv(GROUND_TRUTH_PATH)
    v1_df = pd.read_csv(V1_DECISIONS_PATH)
    v2_df = pd.read_csv(V2_DECISIONS_PATH)

    gt_map = load_gt_lookup(gt_df)

    action_costs = {
        "RETRY_NOW": 2.0,
        "WAIT_AND_RETRY": 2.0,
        "SEND_REMINDER": 1.0,
        "PAYMENT_LINK": 3.0,
        "UPDATE_PAYMENT_METHOD": 3.0,
        "STOP": 0.0,
    }

    # 1. Evaluate V1
    v1_rows = []
    for _, row in v1_df.iterrows():
        fid, act, amt = str(row["failure_id"]), str(row["candidate_action"]), float(row["amount"])
        key = (fid, act)
        prob = gt_map[key]["true_prob"] if key in gt_map else 0.0
        cost = action_costs.get(act, 0.0)
        gross = amt * prob
        net = gross - cost
        v1_rows.append({"failure_id": fid, "amount": amt, "action": act, "gross": gross, "cost": cost, "net": net, "prob": prob})
    v1_res = pd.DataFrame(v1_rows)

    # 2. Evaluate V2
    v2_rows = []
    for _, row in v2_df.iterrows():
        fid, act, amt = str(row["failure_id"]), str(row["candidate_action"]), float(row["amount"])
        if act == "STOP":
            prob, cost, gross, net = 0.0, 0.0, 0.0, 0.0
        else:
            key = (fid, act)
            prob = gt_map[key]["true_prob"] if key in gt_map else 0.0
            cost = action_costs.get(act, 0.0)
            gross = amt * prob
            net = gross - cost
        v2_rows.append({"failure_id": fid, "amount": amt, "action": act, "gross": gross, "cost": cost, "net": net, "prob": prob})
    v2_res = pd.DataFrame(v2_rows)

    # 3. Evaluate Failure-Aware Rules
    rules_rows = []
    for _, row in test_df.iterrows():
        fid, amt = str(row["failure_id"]), float(row["amount"])
        act = failure_aware_rules(row)
        key = (fid, act)
        prob = gt_map[key]["true_prob"] if key in gt_map else 0.0
        cost = action_costs.get(act, 0.0)
        gross = amt * prob
        net = gross - cost
        rules_rows.append({"failure_id": fid, "amount": amt, "action": act, "gross": gross, "cost": cost, "net": net, "prob": prob})
    rules_res = pd.DataFrame(rules_rows)

    # 4. Evaluate Oracle Benchmark
    oracle_rows = []
    for fid, group in gt_df.groupby("failure_id"):
        # filter to test_df failure_ids
        if fid in test_df["failure_id"].values:
            best_row = group.sort_values("expected_net_value", ascending=False).iloc[0]
            amt = float(best_row["amount"])
            act = str(best_row["candidate_action"])
            prob = float(best_row["true_recovery_probability"])
            cost = action_costs.get(act, 0.0)
            gross = amt * prob
            net = gross - cost
            oracle_rows.append({"failure_id": fid, "amount": amt, "action": act, "gross": gross, "cost": cost, "net": net, "prob": prob})
    oracle_res = pd.DataFrame(oracle_rows)

    rev_at_risk = test_df["amount"].sum()

    metrics = [
        ("Cases evaluated", len(test_df), len(test_df), len(test_df), len(test_df)),
        ("Revenue at risk (₹)", f"{rev_at_risk:,.2f}", f"{rev_at_risk:,.2f}", f"{rev_at_risk:,.2f}", f"{rev_at_risk:,.2f}"),
        ("Expected gross recovery (₹)", f"{v1_res['gross'].sum():,.2f}", f"{v2_res['gross'].sum():,.2f}", f"{rules_res['gross'].sum():,.2f}", f"{oracle_res['gross'].sum():,.2f}"),
        ("Intervention cost (₹)", f"{v1_res['cost'].sum():,.2f}", f"{v2_res['cost'].sum():,.2f}", f"{rules_res['cost'].sum():,.2f}", f"{oracle_res['cost'].sum():,.2f}"),
        ("Expected NET recovery (₹)", f"{v1_res['net'].sum():,.2f}", f"{v2_res['net'].sum():,.2f}", f"{rules_res['net'].sum():,.2f}", f"{oracle_res['net'].sum():,.2f}"),
        ("Recovery rate (%)", f"{v1_res['gross'].sum()/rev_at_risk*100:.2f}%", f"{v2_res['gross'].sum()/rev_at_risk*100:.2f}%", f"{rules_res['gross'].sum()/rev_at_risk*100:.2f}%", f"{oracle_res['gross'].sum()/rev_at_risk*100:.2f}%"),
    ]

    res_df = pd.DataFrame(metrics, columns=["Metric", "V1 RecoveryOS", "V2 Value Engine", "Failure-Aware Rules", "Oracle Ceiling"])
    print(res_df.to_string(index=False))

    oracle_net = oracle_res["net"].sum()
    v1_net = v1_res["net"].sum()
    v2_net = v2_res["net"].sum()
    rules_net = rules_res["net"].sum()

    print("\n----------------------------------------------------------------------")
    print("KEY PERFORMANCE COMPARISONS:")
    print("----------------------------------------------------------------------")
    print(f"V1 Net Recovery:                 ₹{v1_net:,.2f}")
    print(f"V2 Net Recovery:                 ₹{v2_net:,.2f}")
    print(f"Rules Net Recovery:              ₹{rules_net:,.2f}")
    print(f"Oracle Net Recovery:             ₹{oracle_net:,.2f}")
    
    print(f"\nV2 vs V1 Net Difference:        ₹{v2_net - v1_net:+,.2f} ({(v2_net - v1_net)/v1_net*100:+.2f}%)")
    print(f"V2 vs Rules Net Difference:     ₹{v2_net - rules_net:+,.2f} ({(v2_net - rules_net)/rules_net*100:+.2f}%)")
    print(f"V2 Oracle Opportunity Gap:       ₹{oracle_net - v2_net:,.2f} ({((oracle_net - v2_net) / oracle_net * 100):.2f}%)")

    # Match percentage with Oracle
    oracle_action_map = dict(zip(oracle_res["failure_id"], oracle_res["action"]))
    v1_matches = sum(row["action"] == oracle_action_map.get(row["failure_id"]) for _, row in v1_res.iterrows())
    v2_matches = sum(row["action"] == oracle_action_map.get(row["failure_id"]) for _, row in v2_res.iterrows())

    print(f"\nV1 Action Match with Oracle:    {v1_matches/len(test_df)*100:.2f}% ({v1_matches}/{len(test_df)})")
    print(f"V2 Action Match with Oracle:    {v2_matches/len(test_df)*100:.2f}% ({v2_matches}/{len(test_df)})")

    print("\n----------------------------------------------------------------------")
    print("ACTION DISTRIBUTION COMPARISON:")
    print("----------------------------------------------------------------------")
    actions_list = ["RETRY_NOW", "WAIT_AND_RETRY", "SEND_REMINDER", "PAYMENT_LINK", "UPDATE_PAYMENT_METHOD", "STOP"]
    act_df = pd.DataFrame({
        "Action": actions_list,
        "V1 Count": [v1_res["action"].value_counts().get(a, 0) for a in actions_list],
        "V2 Count": [v2_res["action"].value_counts().get(a, 0) for a in actions_list],
        "Rules Count": [rules_res["action"].value_counts().get(a, 0) for a in actions_list],
        "Oracle Count": [oracle_res["action"].value_counts().get(a, 0) for a in actions_list],
    })
    print(act_df.to_string(index=False))

    return res_df


if __name__ == "__main__":
    run_evaluation_benchmark()
