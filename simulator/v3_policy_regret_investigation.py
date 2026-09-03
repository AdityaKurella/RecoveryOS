"""
RecoveryOS V3 — Policy Regret Investigation (Day 1 Research Script)

Performs exhaustive offline forensic analysis across 559 held-out test cases:
1. Reconstructs RecoveryOS ML, Failure-Aware Rules, and Oracle decisions.
2. Builds Action Disagreement Matrix (RecoveryOS vs Oracle & Rules).
3. Analyzes regret by failure reason, customer segment, amount buckets, and actions.
4. Investigates model confidence & margin vs regret.
5. Quantifies Rules structural simulator advantage.
6. Outputs CSV artifacts to data/v3_research/ and summary stats.

OFFLINE RESEARCH ONLY — Ground-truth true probabilities are used ONLY for analysis.
"""

import sys
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
MODEL_PATH = BASE_DIR / "data" / "recovery_probability" / "counterfactual_model.pkl.gz"
RESEARCH_DIR = BASE_DIR / "data" / "v3_research"

MODEL_FEATURES = [
    "amount", "account_age_days", "successful_payments", "failed_payments",
    "total_payments", "payment_success_rate", "historical_recovery_rate",
    "engagement_score", "failure_reason", "behavior_profile", "candidate_action"
]

ALL_ACTIONS = ["RETRY_NOW", "WAIT_AND_RETRY", "SEND_REMINDER", "PAYMENT_LINK", "UPDATE_PAYMENT_METHOD", "STOP"]


def load_model():
    with gzip.open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
        return bundle["model"] if isinstance(bundle, dict) and "model" in bundle else bundle


def run_investigation():
    print("\n======================================================================")
    print("RECOVERYOS V3 — DAY 1 POLICY REGRET INVESTIGATION")
    print("======================================================================")

    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    test_df = pd.read_csv(TEST_PATH)
    gt_df = pd.read_csv(GROUND_TRUTH_PATH)
    model = load_model()
    engine = CounterfactualValueEngine()

    assert len(test_df) == 559, f"Expected 559 test cases, got {len(test_df)}"
    print(f"Loaded {len(test_df)} held-out test cases cleanly.")

    # Build ground-truth lookup map
    gt_map = {}
    for _, row in gt_df.iterrows():
        key = (str(row["failure_id"]), str(row["candidate_action"]))
        gt_map[key] = {
            "true_prob": float(row["true_recovery_probability"]),
            "net_val": float(row["expected_net_value"])
        }

    # Build Oracle map (best action per failure)
    oracle_map = {}
    test_fids = set(test_df["failure_id"].astype(str))
    for fid, group in gt_df.groupby("failure_id"):
        sfid = str(fid)
        if sfid in test_fids:
            best_row = group.sort_values("expected_net_value", ascending=False).iloc[0]
            amt = float(best_row["amount"])
            act = str(best_row["candidate_action"])
            prob = float(best_row["true_recovery_probability"])
            cost = ACTION_COSTS.get(act, 0.0)
            net = (amt * prob) - cost
            oracle_map[sfid] = {
                "action": act,
                "true_prob": prob,
                "cost": cost,
                "expected_net": net
            }

    # Generate RecoveryOS ML candidate decisions & ranked actions
    cand_df = engine.generate_candidate_table(test_df, model, MODEL_FEATURES)

    cases = []
    for fid, group in cand_df.groupby("failure_id"):
        sfid = str(fid)
        sorted_cand = group.sort_values("expected_net_recovery", ascending=False)
        top1 = sorted_cand.iloc[0]
        top2 = sorted_cand.iloc[1] if len(sorted_cand) > 1 else top1

        ml_act = str(top1["candidate_action"])
        ml_est_p = float(top1["estimated_recovery_probability"])
        ml_est_net = float(top1["expected_net_recovery"])
        ml_margin = ml_est_net - float(top2["expected_net_recovery"])

        amt = float(top1["amount"])
        f_reason = str(top1["failure_reason"])
        b_profile = str(top1["behavior_profile"])
        acc_age = int(top1["account_age_days"])
        hist_rec = float(top1["historical_recovery_rate"])
        hist_succ = float(top1["payment_success_rate"])
        eng_score = float(top1["engagement_score"])

        # ML Evaluation against GT
        ml_gt_info = gt_map.get((sfid, ml_act), {"true_prob": 0.0})
        ml_true_p = ml_gt_info["true_prob"] if ml_act != "STOP" else 0.0
        ml_cost = ACTION_COSTS.get(ml_act, 0.0)
        ml_net = (amt * ml_true_p) - ml_cost if ml_act != "STOP" else 0.0

        # Rules Evaluation
        row_test = test_df[test_df["failure_id"].astype(str) == sfid].iloc[0]
        rules_act = failure_aware_rules(row_test)
        rules_cost = ACTION_COSTS.get(rules_act, 0.0)
        rules_gt_info = gt_map.get((sfid, rules_act), {"true_prob": 0.0})
        rules_true_p = rules_gt_info["true_prob"] if rules_act != "STOP" else 0.0
        rules_net = (amt * rules_true_p) - rules_cost

        # Oracle Evaluation
        oracle_info = oracle_map[sfid]
        oracle_act = oracle_info["action"]
        oracle_net = oracle_info["expected_net"]

        # Regret Metrics
        oracle_regret = oracle_net - ml_net
        rules_regret = rules_net - ml_net

        cases.append({
            "failure_id": sfid,
            "amount": amt,
            "failure_reason": f_reason,
            "behavior_profile": b_profile,
            "account_age_days": acc_age,
            "historical_recovery_rate": hist_rec,
            "payment_success_rate": hist_succ,
            "engagement_score": eng_score,
            "ml_action": ml_act,
            "ml_est_prob": ml_est_p,
            "ml_true_prob": ml_true_p,
            "ml_cost": ml_cost,
            "ml_net": ml_net,
            "ml_margin": ml_margin,
            "rules_action": rules_act,
            "rules_net": rules_net,
            "oracle_action": oracle_act,
            "oracle_net": oracle_net,
            "oracle_regret": oracle_regret,
            "rules_regret": rules_regret,
            "ml_equals_oracle": (ml_act == oracle_act),
            "ml_equals_rules": (ml_act == rules_act),
        })

    df = pd.DataFrame(cases)

    # 1. Total Metrics
    tot_ml_net = df["ml_net"].sum()
    tot_rules_net = df["rules_net"].sum()
    tot_oracle_net = df["oracle_net"].sum()
    tot_oracle_gap = tot_oracle_net - tot_ml_net
    tot_rules_gap = tot_rules_net - tot_ml_net
    oracle_match_pct = (df["ml_equals_oracle"].sum() / len(df)) * 100
    rules_match_pct = (df["ml_equals_rules"].sum() / len(df)) * 100

    print("\n--- SUMMARY COMPARISON METRICS ---")
    print(f"Total ML Expected NET:        ₹{tot_ml_net:,.2f}")
    print(f"Total Rules Expected NET:     ₹{tot_rules_net:,.2f}")
    print(f"Total Oracle Expected NET:    ₹{tot_oracle_net:,.2f}")
    print(f"Total Oracle Opportunity Gap: ₹{tot_oracle_gap:,.2f} ({tot_oracle_gap/tot_oracle_net*100:.2f}%)")
    print(f"RecoveryOS vs Rules Gap:      ₹{tot_rules_gap:,.2f}")
    print(f"Oracle Action Match:          {oracle_match_pct:.2f}% ({df['ml_equals_oracle'].sum()}/{len(df)})")
    print(f"Rules Action Match:           {rules_match_pct:.2f}% ({df['ml_equals_rules'].sum()}/{len(df)})")

    # Save policy_regret_cases.csv
    df.sort_values("oracle_regret", ascending=False).to_csv(RESEARCH_DIR / "policy_regret_cases.csv", index=False)

    # 2. Action Disagreement Matrix (ML vs Oracle)
    diag_matrix = pd.crosstab(df["ml_action"], df["oracle_action"], rownames=["ML Action"], colnames=["Oracle Action"])
    for a in ALL_ACTIONS:
        if a not in diag_matrix.index:
            diag_matrix.loc[a] = 0
        if a not in diag_matrix.columns:
            diag_matrix[a] = 0
    diag_matrix = diag_matrix.reindex(index=ALL_ACTIONS, columns=ALL_ACTIONS).fillna(0).astype(int)
    diag_matrix.to_csv(RESEARCH_DIR / "action_disagreement_matrix.csv")

    print("\n--- ACTION DISAGREEMENT MATRIX (ML vs Oracle Counts) ---")
    print(diag_matrix.to_string())

    # 3. Top Regret Analysis
    top10 = df.sort_values("oracle_regret", ascending=False).head(10)
    top25 = df.sort_values("oracle_regret", ascending=False).head(25)
    top50 = df.sort_values("oracle_regret", ascending=False).head(50)
    top100 = df.sort_values("oracle_regret", ascending=False).head(100)

    print("\n--- REGRET CONCENTRATION ---")
    print(f"Top 10 Regret Total:  ₹{top10['oracle_regret'].sum():,.2f} ({top10['oracle_regret'].sum()/tot_oracle_gap*100:.1f}% of total gap)")
    print(f"Top 25 Regret Total:  ₹{top25['oracle_regret'].sum():,.2f} ({top25['oracle_regret'].sum()/tot_oracle_gap*100:.1f}% of total gap)")
    print(f"Top 50 Regret Total:  ₹{top50['oracle_regret'].sum():,.2f} ({top50['oracle_regret'].sum()/tot_oracle_gap*100:.1f}% of total gap)")
    print(f"Top 100 Regret Total: ₹{top100['oracle_regret'].sum():,.2f} ({top100['oracle_regret'].sum()/tot_oracle_gap*100:.1f}% of total gap)")

    print("\n--- TOP 10 HIGHEST REGRET CASES ---")
    top10_disp = top10[["failure_id", "amount", "failure_reason", "ml_action", "oracle_action", "ml_net", "oracle_net", "oracle_regret"]]
    print(top10_disp.to_string(index=False))

    # 4. Regret by Segment
    seg_reason = df.groupby("failure_reason").agg(
        cases=("failure_id", "count"),
        total_regret=("oracle_regret", "sum"),
        avg_regret=("oracle_regret", "mean"),
        ml_net=("ml_net", "sum"),
        oracle_net=("oracle_net", "sum")
    ).reset_index()
    seg_reason["pct_of_gap"] = (seg_reason["total_regret"] / tot_oracle_gap) * 100
    seg_reason.sort_values("total_regret", ascending=False).to_csv(RESEARCH_DIR / "regret_by_segment.csv", index=False)

    print("\n--- REGRET BY FAILURE REASON ---")
    print(seg_reason.sort_values("total_regret", ascending=False).to_string(index=False))

    # 5. Regret by Amount Bucket
    bins = [0, 1000, 5000, 10000, np.inf]
    labels = ["< ₹1,000", "₹1,000–₹5,000", "₹5,000–₹10,000", "₹10,000+"]
    df["amount_bucket"] = pd.cut(df["amount"], bins=bins, labels=labels)

    amt_summary = df.groupby("amount_bucket", observed=False).agg(
        cases=("failure_id", "count"),
        total_amount=("amount", "sum"),
        total_regret=("oracle_regret", "sum"),
        avg_regret=("oracle_regret", "mean"),
        ml_net=("ml_net", "sum"),
        oracle_net=("oracle_net", "sum")
    ).reset_index()
    amt_summary["pct_of_gap"] = (amt_summary["total_regret"] / tot_oracle_gap) * 100

    print("\n--- REGRET BY AMOUNT BUCKET ---")
    print(amt_summary.to_string(index=False))

    # 6. Regret by ML Chosen Action
    act_summary = df.groupby("ml_action").agg(
        cases=("failure_id", "count"),
        oracle_matches=("ml_equals_oracle", "sum"),
        total_regret=("oracle_regret", "sum"),
        avg_regret=("oracle_regret", "mean")
    ).reset_index()
    act_summary["match_rate_%"] = (act_summary["oracle_matches"] / act_summary["cases"]) * 100
    act_summary["pct_of_gap"] = (act_summary["total_regret"] / tot_oracle_gap) * 100

    print("\n--- REGRET BY ML CHOSEN ACTION ---")
    print(act_summary.sort_values("total_regret", ascending=False).to_string(index=False))

    # 7. ML vs Rules Disagreement Analysis
    rules_diff_df = df[~df["ml_equals_rules"]].copy()
    rules_diff_df["ml_vs_rules_net"] = rules_diff_df["ml_net"] - rules_diff_df["rules_net"]

    ml_better_rules = rules_diff_df[rules_diff_df["ml_vs_rules_net"] > 0]
    rules_better_ml = rules_diff_df[rules_diff_df["ml_vs_rules_net"] < 0]

    ml_vs_rules_summary = {
        "disagreement_cases": len(rules_diff_df),
        "disagreement_pct": (len(rules_diff_df) / len(df)) * 100,
        "cases_ml_beats_rules": len(ml_better_rules),
        "gain_when_ml_beats_rules": ml_better_rules["ml_vs_rules_net"].sum(),
        "cases_rules_beats_ml": len(rules_better_ml),
        "loss_when_rules_beats_ml": abs(rules_better_ml["ml_vs_rules_net"].sum()),
        "net_difference_ml_minus_rules": rules_diff_df["ml_vs_rules_net"].sum(),
    }

    pd.DataFrame([ml_vs_rules_summary]).to_csv(RESEARCH_DIR / "ml_vs_rules.csv", index=False)

    print("\n--- ML vs RULES DISAGREEMENT ANALYSIS ---")
    print(f"Total Disagreement Cases:        {len(rules_diff_df)} ({len(rules_diff_df)/len(df)*100:.1f}%)")
    print(f"Cases where ML beats Rules:     {len(ml_better_rules)} (Gained +₹{ml_better_rules['ml_vs_rules_net'].sum():,.2f})")
    print(f"Cases where Rules beats ML:    {len(rules_better_ml)} (Lost -₹{abs(rules_better_ml['ml_vs_rules_net'].sum()):,.2f})")
    print(f"Net Difference (ML - Rules):    ₹{rules_diff_df['ml_vs_rules_net'].sum():,.2f}")

    # 8. Model Margin / Uncertainty Analysis
    df["margin_quartile"] = pd.qcut(df["ml_margin"], q=4, labels=["Q1 (Uncertain)", "Q2", "Q3", "Q4 (Confident)"])
    margin_summary = df.groupby("margin_quartile", observed=False).agg(
        cases=("failure_id", "count"),
        avg_margin=("ml_margin", "mean"),
        total_regret=("oracle_regret", "sum"),
        avg_regret=("oracle_regret", "mean"),
        oracle_match_pct=("ml_equals_oracle", "mean")
    ).reset_index()
    margin_summary["oracle_match_pct"] *= 100

    print("\n--- REGRET VS MODEL MARGIN (CONFIDENCE) ---")
    print(margin_summary.to_string(index=False))

    return df


if __name__ == "__main__":
    run_investigation()
