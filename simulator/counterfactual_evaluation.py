import csv
from pathlib import Path


# ============================================================
# M10D — COUNTERFACTUAL POLICY EVALUATION
# ============================================================

ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
]

ACTION_COSTS = {
    "RETRY_NOW": 2.0,
    "WAIT_AND_RETRY": 2.0,
    "SEND_REMINDER": 1.0,
    "PAYMENT_LINK": 3.0,
    "UPDATE_PAYMENT_METHOD": 3.0,
}


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

COUNTERFACTUAL_PATH = (
    DATA_DIR / "counterfactual_training.csv"
)

TEST_PATH = (
    DATA_DIR / "test_features.csv"
)

POLICY_PATH = (
    DATA_DIR
    / "ml_decision"
    / "m10c_policy_decisions.csv"
)


# ============================================================
# CSV HELPERS
# ============================================================

def load_csv(path):

    if not path.exists():
        raise FileNotFoundError(
            f"File not found:\n{path}"
        )

    with open(
        path,
        "r",
        newline="",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def to_float(value, default=0.0):

    try:
        return float(value)

    except (ValueError, TypeError):
        return default


# ============================================================
# ACTION VALIDATION
# ============================================================

def validate_action(action):

    return action in ACTIONS


# ============================================================
# BUILD COUNTERFACTUAL LOOKUP
# ============================================================

def build_counterfactual_lookup(rows):

    lookup = {}

    for row in rows:

        failure_id = row["failure_id"]

        action = row["candidate_action"]

        lookup.setdefault(
            failure_id,
            {}
        )

        lookup[
            failure_id
        ][action] = row

    return lookup


# ============================================================
# RULE BASELINE
# ============================================================

def failure_aware_rule(failure_reason):

    rules = {

        "NETWORK_ERROR":
            "RETRY_NOW",

        "CARD_EXPIRED":
            "UPDATE_PAYMENT_METHOD",

        "INSUFFICIENT_FUNDS":
            "WAIT_AND_RETRY",

        "BANK_DECLINED":
            "WAIT_AND_RETRY",

        "AUTHENTICATION_FAILED":
            "UPDATE_PAYMENT_METHOD",

        "LIMIT_EXCEEDED":
            "PAYMENT_LINK",
    }

    return rules.get(
        failure_reason,
        "WAIT_AND_RETRY"
    )


# ============================================================
# EVALUATE STRATEGY
# ============================================================

def evaluate_strategy(
    strategy_name,
    decisions,
    counterfactual_lookup,
):

    total_cases = 0

    revenue_at_risk = 0.0

    gross_recovery = 0.0

    intervention_cost = 0.0

    action_counts = {
        action: 0
        for action in ACTIONS
    }

    evaluated_failure_ids = []

    for decision in decisions:

        failure_id = decision[
            "failure_id"
        ]

        if failure_id not in counterfactual_lookup:

            raise ValueError(
                f"Missing counterfactual data "
                f"for {failure_id}"
            )

        candidates = counterfactual_lookup[
            failure_id
        ]

        # ----------------------------------------------------
        # Determine selected action
        # ----------------------------------------------------

        if strategy_name == "RECOVERYOS_M10C":

            action = decision[
                "candidate_action"
            ]

        elif strategy_name == "FAILURE_AWARE_RULES":

            failure_reason = decision[
                "failure_reason"
            ]

            action = failure_aware_rule(
                failure_reason
            )

        elif strategy_name == "ORACLE_BENCHMARK":

            action = max(
                candidates.values(),
                key=lambda row:
                    to_float(
                        row[
                            "expected_net_value"
                        ]
                    )
            )[
                "candidate_action"
            ]

        else:

            raise ValueError(
                f"Unknown strategy: "
                f"{strategy_name}"
            )

        # ----------------------------------------------------
        # Validate selected action
        # ----------------------------------------------------

        if not validate_action(action):

            raise ValueError(
                f"Invalid action '{action}' "
                f"for {failure_id}"
            )

        if action not in candidates:

            raise ValueError(
                f"Action '{action}' missing "
                f"for {failure_id}"
            )

        # ----------------------------------------------------
        # Get hidden counterfactual outcome
        # ----------------------------------------------------

        selected = candidates[action]

        amount = to_float(
            selected["amount"]
        )

        probability = to_float(
            selected[
                "true_recovery_probability"
            ]
        )

        cost = to_float(
            selected["action_cost"]
        )

        # ----------------------------------------------------
        # Counterfactual economic outcome
        # ----------------------------------------------------

        gross = (
            amount * probability
        )

        net = gross - cost

        # Keep net explicitly calculated
        # for clarity and future diagnostics.
        _ = net

        # ----------------------------------------------------
        # Aggregate
        # ----------------------------------------------------

        total_cases += 1

        revenue_at_risk += amount

        gross_recovery += gross

        intervention_cost += cost

        action_counts[action] += 1

        evaluated_failure_ids.append(
            failure_id
        )

    # --------------------------------------------------------
    # Strategy metrics
    # --------------------------------------------------------

    net_recovery = (
        gross_recovery
        -
        intervention_cost
    )

    recovery_rate = (
        gross_recovery
        /
        revenue_at_risk
        if revenue_at_risk > 0
        else 0.0
    )

    return {

        "strategy": strategy_name,

        "cases": total_cases,

        "revenue_at_risk":
            revenue_at_risk,

        "gross_recovery":
            gross_recovery,

        "intervention_cost":
            intervention_cost,

        "net_recovery":
            net_recovery,

        "recovery_rate":
            recovery_rate,

        "action_counts":
            action_counts,

        "failure_ids":
            evaluated_failure_ids,
    }


# ============================================================
# PRINT RESULTS
# ============================================================

def print_results(result):

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

    for action in ACTIONS:

        print(
            f"{action}: "
            f"{result['action_counts'][action]}"
        )


# ============================================================
# VALIDATION
# ============================================================

def validate_results(
    test_rows,
    counterfactual_rows,
    decisions,
    results,
):

    print(
        "\n"
        + "=" * 70
    )

    print(
        "M10D EVALUATION VALIDATION"
    )

    print(
        "=" * 70
    )

    expected_cases = len(
        test_rows
    )

    # --------------------------------------------------------
    # Case counts
    # --------------------------------------------------------

    print(
        f"Expected test cases: "
        f"{expected_cases}"
    )

    same_cases = all(
        result["cases"]
        == expected_cases
        for result in results
    )

    print(
        f"Same number of test cases: "
        f"{'YES ✅' if same_cases else 'NO ❌'}"
    )

    # --------------------------------------------------------
    # Duplicate test IDs
    # --------------------------------------------------------

    test_ids = [
        row["failure_id"]
        for row in test_rows
    ]

    test_duplicates = (
        len(test_ids)
        -
        len(set(test_ids))
    )

    print(
        f"Duplicate test IDs: "
        f"{test_duplicates}"
    )

    # --------------------------------------------------------
    # Counterfactual coverage
    # --------------------------------------------------------

    counterfactual_lookup = (
        build_counterfactual_lookup(
            counterfactual_rows
        )
    )

    missing_counterfactuals = [

        failure_id

        for failure_id in test_ids

        if failure_id
        not in counterfactual_lookup
    ]

    print(
        f"Missing counterfactual failures: "
        f"{len(missing_counterfactuals)}"
    )

    # --------------------------------------------------------
    # Five actions per failure
    # --------------------------------------------------------

    invalid_action_coverage = 0

    for failure_id in test_ids:

        actions = set(
            counterfactual_lookup[
                failure_id
            ].keys()
        )

        if actions != set(ACTIONS):

            invalid_action_coverage += 1

    print(
        f"Five-action counterfactual coverage: "
        f"{'PASS ✅' if invalid_action_coverage == 0 else 'FAIL ❌'}"
    )

    # --------------------------------------------------------
    # M10C IDs
    # --------------------------------------------------------

    decision_ids = [
        row["failure_id"]
        for row in decisions
    ]

    decision_duplicates = (
        len(decision_ids)
        -
        len(set(decision_ids))
    )

    missing_decisions = (
        set(test_ids)
        -
        set(decision_ids)
    )

    extra_decisions = (
        set(decision_ids)
        -
        set(test_ids)
    )

    print(
        f"M10C duplicate IDs: "
        f"{decision_duplicates}"
    )

    print(
        f"M10C missing decisions: "
        f"{len(missing_decisions)}"
    )

    print(
        f"M10C extra decisions: "
        f"{len(extra_decisions)}"
    )

    # --------------------------------------------------------
    # Selected actions
    # --------------------------------------------------------

    invalid_actions = 0

    for decision in decisions:

        if not validate_action(
            decision[
                "candidate_action"
            ]
        ):

            invalid_actions += 1

    print(
        f"Invalid M10C actions: "
        f"{invalid_actions}"
    )

    # --------------------------------------------------------
    # Ground-truth probabilities
    # --------------------------------------------------------

    invalid_probabilities = 0

    for row in counterfactual_rows:

        probability = to_float(
            row[
                "true_recovery_probability"
            ]
        )

        if not 0.0 < probability < 1.0:

            invalid_probabilities += 1

    print(
        f"Invalid ground-truth probabilities: "
        f"{invalid_probabilities}"
    )

    # --------------------------------------------------------
    # Same evaluation universe
    # --------------------------------------------------------

    same_failure_ids = all(
    set(result["failure_ids"]) == set(test_ids)
    for result in results
)



    print(
        f"All strategies same test universe: "
        f"{'YES ✅' if same_failure_ids else 'NO ❌'}"
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    validation_pass = (

        same_cases

        and test_duplicates == 0

        and len(
            missing_counterfactuals
        ) == 0

        and invalid_action_coverage == 0

        and decision_duplicates == 0

        and len(
            missing_decisions
        ) == 0

        and len(
            extra_decisions
        ) == 0

        and invalid_actions == 0

        and invalid_probabilities == 0

        and same_failure_ids
    )

    print(
        "\nM10D validation status: "
        f"{'PASS ✅' if validation_pass else 'FAIL ❌'}"
    )

    return validation_pass


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "\n"
        + "=" * 45
    )

    print(
        "M10D COUNTERFACTUAL POLICY EVALUATION"
    )

    print(
        "=" * 45
    )

    print(
        f"\nProject root:\n{BASE_DIR}"
    )

    print(
        f"\nData directory:\n{DATA_DIR}"
    )

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    print(
        "\nLoading test dataset..."
    )

    test_rows = load_csv(
        TEST_PATH
    )

    print(
        "Loading NEW counterfactual "
        "ground-truth dataset..."
    )

    counterfactual_rows = load_csv(
        COUNTERFACTUAL_PATH
    )

    print(
        "Loading M10C policy decisions..."
    )

    decisions = load_csv(
        POLICY_PATH
    )

    print(
        f"\nTest cases loaded: "
        f"{len(test_rows)}"
    )

    print(
        f"Counterfactual rows loaded: "
        f"{len(counterfactual_rows)}"
    )

    print(
        f"M10C decisions loaded: "
        f"{len(decisions)}"
    )

    # --------------------------------------------------------
    # Input validation
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 70
    )

    print(
        "M10D INPUT VALIDATION"
    )

    print(
        "=" * 70
    )

    print(
        f"Test cases: "
        f"{len(test_rows)}"
    )

    test_ids = [
        row["failure_id"]
        for row in test_rows
    ]

    print(
        f"Duplicate test IDs: "
        f"{len(test_ids) - len(set(test_ids))}"
    )

    print(
        f"Counterfactual rows: "
        f"{len(counterfactual_rows)}"
    )

    print(
        f"M10C decisions: "
        f"{len(decisions)}"
    )

    # --------------------------------------------------------
    # Build lookup
    # --------------------------------------------------------

    counterfactual_lookup = (
        build_counterfactual_lookup(
            counterfactual_rows
        )
    )

    # --------------------------------------------------------
    # Evaluate RecoveryOS
    # --------------------------------------------------------

    print(
        "\nEvaluating RecoveryOS M10C..."
    )

    recoveryos_result = evaluate_strategy(
        "RECOVERYOS_M10C",
        decisions,
        counterfactual_lookup,
    )

    # --------------------------------------------------------
    # Evaluate rules
    # --------------------------------------------------------

    print(
        "Evaluating failure-aware rules..."
    )

    rules_result = evaluate_strategy(
        "FAILURE_AWARE_RULES",
        test_rows,
        counterfactual_lookup,
    )

    # --------------------------------------------------------
    # Evaluate oracle
    # --------------------------------------------------------

    print(
        "Evaluating oracle benchmark..."
    )

    oracle_result = evaluate_strategy(
        "ORACLE_BENCHMARK",
        test_rows,
        counterfactual_lookup,
    )

    results = [
        recoveryos_result,
        rules_result,
        oracle_result,
    ]

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 70
    )

    print(
        "M10D RESULTS"
    )

    print(
        "=" * 70
    )

    print_results(
        recoveryos_result
    )

    print_results(
        rules_result
    )

    print_results(
        oracle_result
    )

    # --------------------------------------------------------
    # Comparison
    # --------------------------------------------------------

    recoveryos_net = (
        recoveryos_result[
            "net_recovery"
        ]
    )

    rules_net = (
        rules_result[
            "net_recovery"
        ]
    )

    oracle_net = (
        oracle_result[
            "net_recovery"
        ]
    )

    recoveryos_vs_rules = (
        recoveryos_net
        -
        rules_net
    )

    recoveryos_vs_oracle = (
        oracle_net
        -
        recoveryos_net
    )

    rules_vs_oracle = (
        oracle_net
        -
        rules_net
    )

    rules_improvement = (

        (
            recoveryos_net
            -
            rules_net
        )
        /
        rules_net
        *
        100

        if rules_net != 0
        else 0
    )

    oracle_gap = (

        recoveryos_vs_oracle
        /
        oracle_net
        *
        100

        if oracle_net != 0
        else 0
    )

    rules_oracle_gap = (

        rules_vs_oracle
        /
        oracle_net
        *
        100

        if oracle_net != 0
        else 0
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "POLICY COMPARISON"
    )

    print(
        "=" * 70
    )

    print(
        f"RecoveryOS NET: "
        f"₹{recoveryos_net:,.2f}"
    )

    print(
        f"Failure-aware Rules NET: "
        f"₹{rules_net:,.2f}"
    )

    print(
        f"Oracle NET: "
        f"₹{oracle_net:,.2f}"
    )

    print(
        "\nRecoveryOS vs Rules:"
    )

    print(
        f"Incremental NET recovery: "
        f"₹{recoveryos_vs_rules:,.2f}"
    )

    print(
        f"Improvement: "
        f"{rules_improvement:.2f}%"
    )

    print(
        "\nRecoveryOS vs Oracle:"
    )

    print(
        f"Oracle advantage: "
        f"₹{recoveryos_vs_oracle:,.2f}"
    )

    print(
        f"Oracle gap: "
        f"{oracle_gap:.2f}%"
    )

    print(
        "\nRules vs Oracle:"
    )

    print(
        f"Oracle advantage: "
        f"₹{rules_vs_oracle:,.2f}"
    )

    print(
        f"Oracle gap: "
        f"{rules_oracle_gap:.2f}%"
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validation_pass = validate_results(
        test_rows=test_rows,
        counterfactual_rows=counterfactual_rows,
        decisions=decisions,
        results=results,
    )

    if not validation_pass:

        raise SystemExit(
            "\nM10D validation failed. "
            "Do not use these metrics."
        )

    print(
        "\nM10D COUNTERFACTUAL POLICY "
        "EVALUATION COMPLETE. ✅"
    )