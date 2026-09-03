import csv
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

ACTION_COSTS = {
    "RETRY_NOW": 2.00,
    "WAIT_AND_RETRY": 2.00,
    "SEND_REMINDER": 1.00,
    "PAYMENT_LINK": 3.00,
    "UPDATE_PAYMENT_METHOD": 3.00,
    "NO_ACTION": 0.00,
}


VALID_ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
    "NO_ACTION",
]


# ============================================================
# DATA LOADING
# ============================================================

def load_csv(filename):
    input_path = (
        Path(__file__).parent.parent
        / "data"
        / filename
    )

    with open(
        input_path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


# ============================================================
# GROUND-TRUTH PROBABILITY
# ============================================================

def get_ground_truth_probability(
    ground_truth_by_failure,
    failure_id,
    action,
):
    """
    Read the hidden probability for an action.

    This function is ONLY used during evaluation.
    The ML model never sees these probabilities.
    """

    record = ground_truth_by_failure.get(
        failure_id
    )

    if record is None:
        raise ValueError(
            f"Ground truth missing for "
            f"{failure_id}"
        )

    field = (
        f"{action.lower()}_probability"
    )

    if field not in record:
        raise ValueError(
            f"Missing probability field "
            f"{field} for {failure_id}"
        )

    return float(
        record[field]
    )


# ============================================================
# EVALUATE A STRATEGY
# ============================================================

def evaluate_strategy(
    name,
    decisions,
    ground_truth_by_failure,
):
    """
    Evaluate one policy against the hidden ground truth.
    """

    gross_recovery = 0.0
    intervention_cost = 0.0
    revenue_at_risk = 0.0

    action_counts = {}

    decision_ids = []

    for decision in decisions:

        failure_id = decision[
            "failure_id"
        ]

        action = decision[
            "selected_action"
        ]

        amount = float(
            decision["amount"]
        )

        if action not in VALID_ACTIONS:
            raise ValueError(
                f"Invalid action: {action}"
            )

        decision_ids.append(
            failure_id
        )

        revenue_at_risk += amount

        # ----------------------------------------------------
        # Hidden true probability
        # ----------------------------------------------------

        probability = (
            get_ground_truth_probability(
                ground_truth_by_failure,
                failure_id,
                action,
            )
        )

        # ----------------------------------------------------
        # Expected recovery
        # ----------------------------------------------------

        gross_recovery += (
            amount * probability
        )

        # ----------------------------------------------------
        # Action cost
        # ----------------------------------------------------

        intervention_cost += (
            ACTION_COSTS[action]
        )

        # ----------------------------------------------------
        # Action distribution
        # ----------------------------------------------------

        action_counts[action] = (
            action_counts.get(
                action,
                0,
            )
            + 1
        )

    # --------------------------------------------------------
    # Net recovery
    # --------------------------------------------------------

    net_recovery = (
        gross_recovery
        - intervention_cost
    )

    # --------------------------------------------------------
    # Recovery rate
    # --------------------------------------------------------

    recovery_rate = (
        gross_recovery
        / revenue_at_risk
        if revenue_at_risk > 0
        else 0
    )

    return {
        "strategy": name,
        "cases": len(decisions),
        "revenue_at_risk": revenue_at_risk,
        "gross_recovery": gross_recovery,
        "intervention_cost": intervention_cost,
        "net_recovery": net_recovery,
        "recovery_rate": recovery_rate,
        "action_counts": action_counts,
        "_ids": decision_ids,
    }


# ============================================================
# FAILURE-AWARE RULE BASELINE
# ============================================================

def failure_aware_action(
    failure_reason
):
    """
    Deterministic failure-aware baseline.
    """

    if failure_reason == "NETWORK_ERROR":
        return "RETRY_NOW"

    if failure_reason == "CARD_EXPIRED":
        return "UPDATE_PAYMENT_METHOD"

    if failure_reason == "INSUFFICIENT_FUNDS":
        return "WAIT_AND_RETRY"

    if failure_reason == "BANK_DECLINED":
        return "WAIT_AND_RETRY"

    if failure_reason == "AUTHENTICATION_FAILED":
        return "UPDATE_PAYMENT_METHOD"

    if failure_reason == "LIMIT_EXCEEDED":
        return "PAYMENT_LINK"

    return "NO_ACTION"


# ============================================================
# CREATE RULE DECISIONS
# ============================================================

def create_rule_decisions(
    test_rows
):
    decisions = []

    for row in test_rows:

        action = failure_aware_action(
            row["failure_reason"]
        )

        decisions.append(
            {
                "failure_id":
                    row["failure_id"],

                "amount":
                    row["amount"],

                "selected_action":
                    action,
            }
        )

    return decisions


# ============================================================
# LOAD ML DECISIONS
# ============================================================

def load_ml_decisions(
    test_rows,
    ml_decisions,
):
    """
    Select only ML decisions belonging to the untouched
    test set.

    This prevents accidental leakage from training data.
    """

    test_ids = {
        row["failure_id"]
        for row in test_rows
    }

    selected = []

    seen_ids = set()

    for decision in ml_decisions:

        failure_id = decision[
            "failure_id"
        ]

        if failure_id not in test_ids:
            continue

        if failure_id in seen_ids:
            raise ValueError(
                f"Duplicate ML decision for "
                f"{failure_id}"
            )

        seen_ids.add(
            failure_id
        )

        selected.append(
            {
                "failure_id":
                    failure_id,

                "amount":
                    decision["amount"],

                "selected_action":
                    decision[
                        "selected_action"
                    ],
            }
        )

    # --------------------------------------------------------
    # Verify every test case has an ML decision.
    # --------------------------------------------------------

    missing_ids = (
        test_ids - seen_ids
    )

    extra_ids = (
        seen_ids - test_ids
    )

    if missing_ids:

        raise ValueError(
            "ML decisions missing for "
            f"{len(missing_ids)} test cases"
        )

    if extra_ids:

        raise ValueError(
            "ML decisions contain "
            f"{len(extra_ids)} extra cases"
        )

    return selected


# ============================================================
# ORACLE POLICY
# ============================================================

def create_oracle_decisions(
    test_rows,
    ground_truth_by_failure,
):
    """
    Oracle policy chooses the action with the highest
    TRUE expected net value.

    IMPORTANT:
    This is a benchmark only.

    The oracle is NOT available to RecoveryOS during
    decision making.
    """

    decisions = []

    for row in test_rows:

        failure_id = row[
            "failure_id"
        ]

        amount = float(
            row["amount"]
        )

        best_action = None
        best_net_value = float(
            "-inf"
        )

        for action in VALID_ACTIONS:

            probability = (
                get_ground_truth_probability(
                    ground_truth_by_failure,
                    failure_id,
                    action,
                )
            )

            expected_net_value = (
                amount * probability
                - ACTION_COSTS[action]
            )

            if expected_net_value > best_net_value:

                best_net_value = (
                    expected_net_value
                )

                best_action = action

        decisions.append(
            {
                "failure_id":
                    failure_id,

                "amount":
                    amount,

                "selected_action":
                    best_action,
            }
        )

    return decisions


# ============================================================
# IMPROVEMENT CALCULATION
# ============================================================

def calculate_improvement(
    recovery_os_net,
    baseline_net,
):
    if baseline_net == 0:
        return 0.0

    return (
        (
            recovery_os_net
            - baseline_net
        )
        / baseline_net
        * 100
    )


# ============================================================
# PRINT STRATEGY
# ============================================================

def print_strategy(
    result
):

    print(
        f"\nStrategy: "
        f"{result['strategy']}"
    )

    print(
        f"Cases: "
        f"{result['cases']}"
    )

    print(
        f"Revenue at risk: "
        f"₹{result['revenue_at_risk']:,.2f}"
    )

    print(
        f"Expected gross recovery: "
        f"₹{result['gross_recovery']:,.2f}"
    )

    print(
        f"Intervention cost: "
        f"₹{result['intervention_cost']:,.2f}"
    )

    print(
        f"Expected NET recovery: "
        f"₹{result['net_recovery']:,.2f}"
    )

    print(
        f"Revenue recovery rate: "
        f"{result['recovery_rate']:.2%}"
    )

    print("Actions:")

    for action in VALID_ACTIONS:

        count = result[
            "action_counts"
        ].get(
            action,
            0,
        )

        if count > 0:

            print(
                f"  {action}: {count}"
            )


# ============================================================
# POLICY COMPARISON
# ============================================================

def print_policy_comparison(
    ml_result,
    baseline_result,
    oracle_result,
):
    print(
        "\n========== POLICY COMPARISON =========="
    )

    print(
        f"ML RecoveryOS NET: "
        f"₹{ml_result['net_recovery']:,.2f}"
    )

    print(
        f"Failure-aware Rules NET: "
        f"₹{baseline_result['net_recovery']:,.2f}"
    )

    print(
        f"Oracle NET: "
        f"₹{oracle_result['net_recovery']:,.2f}"
    )

    # --------------------------------------------------------
    # ML vs baseline
    # --------------------------------------------------------

    ml_vs_baseline = (
        ml_result["net_recovery"]
        - baseline_result["net_recovery"]
    )

    ml_vs_baseline_pct = (
        calculate_improvement(
            ml_result["net_recovery"],
            baseline_result["net_recovery"],
        )
    )

    print(
        "\nML vs Rules:"
    )

    print(
        f"Incremental NET recovery: "
        f"₹{ml_vs_baseline:,.2f}"
    )

    print(
        f"Improvement: "
        f"{ml_vs_baseline_pct:.2f}%"
    )

    # --------------------------------------------------------
    # ML vs oracle
    # --------------------------------------------------------

    ml_oracle_gap = (
        oracle_result["net_recovery"]
        - ml_result["net_recovery"]
    )

    ml_oracle_gap_pct = (
        calculate_improvement(
            oracle_result["net_recovery"],
            ml_result["net_recovery"],
        )
    )

    print(
        "\nML vs Oracle:"
    )

    print(
        f"Oracle advantage: "
        f"₹{ml_oracle_gap:,.2f}"
    )

    print(
        f"Oracle gap: "
        f"{ml_oracle_gap_pct:.2f}%"
    )

    # --------------------------------------------------------
    # Rules vs oracle
    # --------------------------------------------------------

    rules_oracle_gap = (
        oracle_result["net_recovery"]
        - baseline_result["net_recovery"]
    )

    rules_oracle_gap_pct = (
        calculate_improvement(
            oracle_result["net_recovery"],
            baseline_result["net_recovery"],
        )
    )

    print(
        "\nRules vs Oracle:"
    )

    print(
        f"Oracle advantage: "
        f"₹{rules_oracle_gap:,.2f}"
    )

    print(
        f"Oracle gap: "
        f"{rules_oracle_gap_pct:.2f}%"
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_results(
    ml_result,
    baseline_result,
    oracle_result,
):

    print(
        "\n========== EVALUATION VALIDATION =========="
    )

    # --------------------------------------------------------
    # Case counts
    # --------------------------------------------------------

    same_cases = (
        ml_result["cases"]
        == baseline_result["cases"]
        == oracle_result["cases"]
    )

    print(
        f"Same number of test cases: "
        f"{'YES ✅' if same_cases else 'NO ❌'}"
    )

    # --------------------------------------------------------
    # Revenue at risk
    # --------------------------------------------------------

    same_revenue = (
        abs(
            ml_result[
                "revenue_at_risk"
            ]
            - baseline_result[
                "revenue_at_risk"
            ]
        )
        < 0.01
        and
        abs(
            ml_result[
                "revenue_at_risk"
            ]
            - oracle_result[
                "revenue_at_risk"
            ]
        )
        < 0.01
    )

    print(
        f"Same revenue at risk: "
        f"{'YES ✅' if same_revenue else 'NO ❌'}"
    )

    # --------------------------------------------------------
    # Failure IDs
    # --------------------------------------------------------

    ml_ids = set(
        ml_result["_ids"]
    )

    baseline_ids = set(
        baseline_result["_ids"]
    )

    oracle_ids = set(
        oracle_result["_ids"]
    )

    same_ids = (
        ml_ids
        == baseline_ids
        == oracle_ids
    )

    print(
        f"Same failure IDs: "
        f"{'YES ✅' if same_ids else 'NO ❌'}"
    )

    # --------------------------------------------------------
    # Duplicate IDs
    # --------------------------------------------------------

    ml_unique = (
        len(
            ml_result["_ids"]
        )
        == len(
            set(
                ml_result["_ids"]
            )
        )
    )

    baseline_unique = (
        len(
            baseline_result["_ids"]
        )
        == len(
            set(
                baseline_result["_ids"]
            )
        )
    )

    oracle_unique = (
        len(
            oracle_result["_ids"]
        )
        == len(
            set(
                oracle_result["_ids"]
            )
        )
    )

    no_duplicates = (
        ml_unique
        and baseline_unique
        and oracle_unique
    )

    print(
        f"No duplicate test cases: "
        f"{'YES ✅' if no_duplicates else 'NO ❌'}"
    )

    print(
        "============================================"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # LOAD TEST DATA
    # ========================================================

    test_rows = load_csv(
        "test_features.csv"
    )

    # ========================================================
    # LOAD GROUND TRUTH
    # ========================================================

    ground_truth = load_csv(
        "recovery_ground_truth.csv"
    )

    ground_truth_by_failure = {
        row["failure_id"]: row
        for row in ground_truth
    }

    # ========================================================
    # LOAD ACTUAL M9C ML DECISIONS
    # ========================================================

    ml_decision_rows = load_csv(
        "ml_decision_outputs.csv"
    )

    ml_decisions = load_ml_decisions(
        test_rows,
        ml_decision_rows,
    )

    # ========================================================
    # CREATE FAILURE-AWARE RULE DECISIONS
    # ========================================================

    baseline_decisions = (
        create_rule_decisions(
            test_rows
        )
    )

    # ========================================================
    # CREATE ORACLE BENCHMARK
    # ========================================================

    oracle_decisions = (
        create_oracle_decisions(
            test_rows,
            ground_truth_by_failure,
        )
    )

    # ========================================================
    # EVALUATE ML
    # ========================================================

    ml_result = evaluate_strategy(
        "RECOVERYOS_ML",
        ml_decisions,
        ground_truth_by_failure,
    )

    # ========================================================
    # EVALUATE RULES
    # ========================================================

    baseline_result = evaluate_strategy(
        "FAILURE_AWARE_RULES",
        baseline_decisions,
        ground_truth_by_failure,
    )

    # ========================================================
    # EVALUATE ORACLE
    # ========================================================

    oracle_result = evaluate_strategy(
        "ORACLE_BENCHMARK",
        oracle_decisions,
        ground_truth_by_failure,
    )

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print(
        "\n========== RECOVERYOS TEST EVALUATION =========="
    )

    print_strategy(
        ml_result
    )

    print_strategy(
        baseline_result
    )

    print_strategy(
        oracle_result
    )

    # ========================================================
    # POLICY COMPARISON
    # ========================================================

    print_policy_comparison(
        ml_result,
        baseline_result,
        oracle_result,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    validate_results(
        ml_result,
        baseline_result,
        oracle_result,
    )

    print(
        "\nM9D POLICY EVALUATION COMPLETE. ✅"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()