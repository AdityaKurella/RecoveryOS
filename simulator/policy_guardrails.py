from pathlib import Path
import pandas as pd


# ============================================================
# RECOVERYOS — POLICY + GUARDRAILS ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "decisions"
    / "recoveryos_decisions.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "policy"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "recoveryos_policy_decisions.csv"
)

VALID_ACTIONS = {
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
}

VALID_POLICY_RESULTS = {
    "ALLOW",
    "HUMAN",
    "STOP",
}


# ============================================================
# POLICY CONFIGURATION
# ============================================================

# Maximum number of direct retry attempts permitted by the
# recovery policy.
MAX_RETRY_ATTEMPTS = 2

# High-value payments receive additional control when the
# recovery recommendation is not sufficiently confident.
HIGH_VALUE_THRESHOLD = 10000

HIGH_VALUE_CONFIDENCE_THRESHOLD = 0.70

# Very low expected net value is not worth active intervention.
MIN_EXPECTED_NET_VALUE = 50


# ============================================================
# POLICY EVALUATION
# ============================================================

def evaluate_policy(row):
    """
    Apply deterministic safety and operational policies.

    IMPORTANT:
    The AI recommends the action.
    This function decides whether that recommendation can
    proceed.

    Returns:
        policy_result
        policy_reason
        policy_checks
    """

    action = row["candidate_action"]

    amount = float(row["amount"])

    probability = float(
        row["estimated_recovery_probability"]
    )

    expected_net = float(
        row["expected_net_recovery"]
    )

    failure_reason = row["failure_reason"]

    checks = []

    # --------------------------------------------------------
    # Check 1 — Valid action
    # --------------------------------------------------------

    if action not in VALID_ACTIONS:

        checks.append(
            "FAIL: invalid recovery action"
        )

        return (
            "STOP",
            "Recovery action is not permitted.",
            " | ".join(checks),
        )

    checks.append("PASS: valid recovery action")

    # --------------------------------------------------------
    # Check 2 — Minimum economic value
    # --------------------------------------------------------

    if expected_net < MIN_EXPECTED_NET_VALUE:

        checks.append(
            "FAIL: expected net value below threshold"
        )

        return (
            "STOP",
            "Expected recovery value is too low "
            "to justify intervention.",
            " | ".join(checks),
        )

    checks.append(
        "PASS: expected net value above threshold"
    )

    # --------------------------------------------------------
    # Check 3 — Probability sanity
    # --------------------------------------------------------

    if probability < 0 or probability > 1:

        checks.append(
            "FAIL: invalid recovery probability"
        )

        return (
            "STOP",
            "Recovery probability is invalid.",
            " | ".join(checks),
        )

    checks.append(
        "PASS: recovery probability valid"
    )

    # --------------------------------------------------------
    # Check 4 — Payment-method failures
    # --------------------------------------------------------

    if failure_reason == "CARD_EXPIRED":

        if action == "RETRY_NOW":

            checks.append(
                "FAIL: direct retry unsuitable for expired card"
            )

            return (
                "STOP",
                "Direct retry is blocked because the "
                "payment method is expired.",
                " | ".join(checks),
            )

        checks.append(
            "PASS: expired-card action is compatible"
        )

    # --------------------------------------------------------
    # Check 5 — High-value confidence control
    # --------------------------------------------------------

    if (
        amount >= HIGH_VALUE_THRESHOLD
        and probability < HIGH_VALUE_CONFIDENCE_THRESHOLD
    ):

        checks.append(
            "REVIEW: high-value case requires confidence review"
        )

        return (
            "HUMAN",
            "High-value recovery opportunity does not meet "
            "the confidence threshold for autonomous execution.",
            " | ".join(checks),
        )

    checks.append(
        "PASS: high-value confidence requirement"
    )

    # --------------------------------------------------------
    # Check 6 — Direct retry policy
    # --------------------------------------------------------

    if action == "RETRY_NOW":

        checks.append(
            f"PASS: retry action within maximum "
            f"{MAX_RETRY_ATTEMPTS} attempts"
        )

    # --------------------------------------------------------
    # Check 7 — Recovery action compatibility
    # --------------------------------------------------------

    action_reason = {

        "RETRY_NOW":
            "Direct retry is permitted under bounded policy.",

        "WAIT_AND_RETRY":
            "Delayed retry is permitted under bounded policy.",

        "SEND_REMINDER":
            "Reminder is permitted as a lower-friction intervention.",

        "PAYMENT_LINK":
            "Payment link is permitted as an alternative recovery path.",

        "UPDATE_PAYMENT_METHOD":
            "Payment-method update is permitted as an alternative recovery path.",
    }

    checks.append(
        f"PASS: {action_reason[action]}"
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return (
        "ALLOW",
        "Recovery recommendation passed all deterministic "
        "policy and safety checks.",
        " | ".join(checks),
    )


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_input(df):

    print("\n" + "=" * 70)
    print("RECOVERYOS — POLICY + GUARDRAILS ENGINE")
    print("=" * 70)

    print("\nInput:")
    print(INPUT_FILE)

    print(f"\nRows loaded: {len(df):,}")
    print(f"Columns loaded: {len(df.columns)}")

    required_columns = [
        "decision_id",
        "failure_id",
        "customer_id",
        "subscription_id",
        "amount",
        "failure_reason",
        "behavior_profile",
        "candidate_action",
        "estimated_recovery_probability",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
        "decision_status",
        "decision_reason",
        "execution_status",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    print("\nSchema validation: PASS")

    duplicate_decisions = int(
        df["decision_id"].duplicated().sum()
    )

    duplicate_failures = int(
        df["failure_id"].duplicated().sum()
    )

    print(
        f"Duplicate decision IDs: "
        f"{duplicate_decisions}"
    )

    print(
        f"Duplicate failure IDs: "
        f"{duplicate_failures}"
    )

    if duplicate_decisions != 0:
        raise ValueError(
            "Duplicate decision IDs detected."
        )

    if duplicate_failures != 0:
        raise ValueError(
            "Duplicate failure IDs detected."
        )

    print("Duplicate validation: PASS")

    invalid_actions = (
        set(df["candidate_action"])
        - VALID_ACTIONS
    )

    print(
        f"Invalid actions: "
        f"{len(invalid_actions)}"
    )

    if invalid_actions:
        raise ValueError(
            f"Invalid actions: {invalid_actions}"
        )

    print("Action validation: PASS")

    if df["amount"].isna().any():
        raise ValueError(
            "Missing payment amounts detected."
        )

    if df[
        "estimated_recovery_probability"
    ].isna().any():

        raise ValueError(
            "Missing recovery probabilities detected."
        )

    if df[
        "expected_net_recovery"
    ].isna().any():

        raise ValueError(
            "Missing expected net values detected."
        )

    print("Missing-value validation: PASS")

    return df


# ============================================================
# APPLY POLICY
# ============================================================

def apply_policy(df):

    results = df.copy()

    policy_results = []
    policy_reasons = []
    policy_checks = []

    for _, row in results.iterrows():

        (
            result,
            reason,
            checks,
        ) = evaluate_policy(row)

        policy_results.append(result)
        policy_reasons.append(reason)
        policy_checks.append(checks)

    results["policy_result"] = policy_results

    results["policy_reason"] = policy_reasons

    results["policy_checks"] = policy_checks

    # Execution remains pending until the execution layer.
    results["execution_status"] = "PENDING"

    return results


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def validate_output(df):

    print("\n" + "=" * 70)
    print("POLICY VALIDATION")
    print("=" * 70)

    print(
        f"Policy decisions: {len(df):,}"
    )

    duplicate_ids = int(
        df["decision_id"].duplicated().sum()
    )

    print(
        f"Duplicate decision IDs: "
        f"{duplicate_ids}"
    )

    if duplicate_ids != 0:
        raise ValueError(
            "Duplicate decision IDs detected."
        )

    invalid_results = (
        set(df["policy_result"])
        - VALID_POLICY_RESULTS
    )

    print(
        f"Invalid policy results: "
        f"{len(invalid_results)}"
    )

    if invalid_results:
        raise ValueError(
            f"Invalid policy results: "
            f"{invalid_results}"
        )

    print("Policy-result validation: PASS")

    missing_reasons = int(
        df["policy_reason"].isna().sum()
    )

    print(
        f"Missing policy reasons: "
        f"{missing_reasons}"
    )

    if missing_reasons != 0:
        raise ValueError(
            "Missing policy reasons detected."
        )

    print("Policy explanation validation: PASS")

    missing_checks = int(
        df["policy_checks"].isna().sum()
    )

    print(
        f"Missing policy checks: "
        f"{missing_checks}"
    )

    if missing_checks != 0:
        raise ValueError(
            "Missing policy checks detected."
        )

    print("Policy-check validation: PASS")

    # Every decision must have exactly one final policy state.
    if not (
        df["policy_result"].isin(
            VALID_POLICY_RESULTS
        )
    ).all():

        raise ValueError(
            "Invalid final policy states detected."
        )

    print(
        "Final policy-state validation: PASS"
    )

    print("\nPolicy validation: PASS")


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"\nInput file not found:\n{INPUT_FILE}\n\n"
            "Run recoveryos_core.py first."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(INPUT_FILE)

    df = validate_input(df)

    results = apply_policy(df)

    validate_output(results)

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("POLICY DECISION SUMMARY")
    print("=" * 70)

    counts = (
        results["policy_result"]
        .value_counts()
        .reindex(
            ["ALLOW", "HUMAN", "STOP"],
            fill_value=0,
        )
    )

    print(
        f"\nALLOW: "
        f"{counts['ALLOW']}"
    )

    print(
        f"HUMAN: "
        f"{counts['HUMAN']}"
    )

    print(
        f"STOP: "
        f"{counts['STOP']}"
    )

    # ========================================================
    # ECONOMIC VIEW
    # ========================================================

    print("\n" + "=" * 70)
    print("POLICY ECONOMICS")
    print("=" * 70)

    for result in [
        "ALLOW",
        "HUMAN",
        "STOP",
    ]:

        subset = results[
            results["policy_result"] == result
        ]

        print(
            f"\n{result}:"
        )

        print(
            f"  Cases: "
            f"{len(subset)}"
        )

        print(
            f"  Revenue represented: "
            f"₹{subset['amount'].sum():,.2f}"
        )

        print(
            f"  Expected net recovery: "
            f"₹{subset['expected_net_recovery'].sum():,.2f}"
        )

    # ========================================================
    # SAMPLE DECISIONS
    # ========================================================

    print("\n" + "=" * 70)
    print("SAMPLE POLICY DECISIONS")
    print("=" * 70)

    display_columns = [
        "decision_id",
        "failure_id",
        "amount",
        "failure_reason",
        "candidate_action",
        "estimated_recovery_probability",
        "policy_result",
    ]

    print(
        results[
            display_columns
        ]
        .head(10)
        .to_string(index=False)
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_columns = [
        "decision_id",
        "portfolio_rank",
        "failure_id",
        "customer_id",
        "subscription_id",
        "amount",
        "failure_reason",
        "behavior_profile",
        "candidate_action",
        "estimated_recovery_probability",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
        "decision_status",
        "decision_reason",
        "policy_result",
        "policy_reason",
        "policy_checks",
        "execution_status",
    ]

    results[
        output_columns
    ].to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\n" + "=" * 70)
    print("OUTPUT")
    print("=" * 70)

    print(
        f"\nSaved policy decisions:"
    )

    print(OUTPUT_FILE)

    print(
        "\nPolicy + Guardrails Engine: COMPLETE ✓"
    )


if __name__ == "__main__":
    main()