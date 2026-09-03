from pathlib import Path
import pandas as pd


# ============================================================
# RECOVERYOS CORE DECISION ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "portfolio"
    / "m11_recovery_portfolio.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "decisions"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "recoveryos_decisions.csv"
)

DEFAULT_CAPACITY = 100

VALID_ACTIONS = {
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
}

REQUIRED_COLUMNS = [
    "portfolio_rank",
    "selected",
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
]


# ============================================================
# DECISION EXPLANATIONS
# ============================================================

def generate_reason(row):
    """
    Generate a concise, deterministic explanation for the
    selected recovery decision.

    The explanation is based on observable context and the
    selected economic decision.
    """

    action = row["candidate_action"]
    failure_reason = row["failure_reason"]
    profile = row["behavior_profile"]
    amount = float(row["amount"])
    probability = float(
        row["estimated_recovery_probability"]
    )

    probability_pct = probability * 100

    reasons = []

    # Failure-specific context.
    if failure_reason == "NETWORK_ERROR":
        reasons.append(
            "The failure is consistent with a transient "
            "payment/network issue."
        )

    elif failure_reason == "CARD_EXPIRED":
        reasons.append(
            "The payment method appears unsuitable for "
            "another direct retry."
        )

    elif failure_reason == "INSUFFICIENT_FUNDS":
        reasons.append(
            "The failure indicates insufficient available "
            "funds at the time of payment."
        )

    elif failure_reason == "BANK_DECLINED":
        reasons.append(
            "The issuing bank declined the payment."
        )

    elif failure_reason == "AUTHENTICATION_FAILED":
        reasons.append(
            "The payment requires successful authentication "
            "before recovery can complete."
        )

    elif failure_reason == "LIMIT_EXCEEDED":
        reasons.append(
            "The payment encountered a transaction-limit "
            "constraint."
        )

    # Customer context.
    if profile == "high_value_loyal":
        reasons.append(
            "The customer is a high-value loyal customer."
        )

    elif profile == "reliable":
        reasons.append(
            "The customer has historically reliable payment "
            "behavior."
        )

    elif profile == "friction_prone":
        reasons.append(
            "The customer has a history of payment friction."
        )

    elif profile == "low_engagement":
        reasons.append(
            "The customer has relatively low engagement."
        )

    # Economic context.
    if amount >= 10000:
        reasons.append(
            "The payment has high revenue exposure."
        )

    elif amount < 500:
        reasons.append(
            "The payment has relatively low revenue exposure."
        )

    # Action context.
    action_descriptions = {
        "RETRY_NOW": (
            "A direct retry is the selected recovery intervention."
        ),
        "WAIT_AND_RETRY": (
            "A delayed retry is preferred to avoid an immediate "
            "repeat attempt."
        ),
        "SEND_REMINDER": (
            "A reminder is selected as a lower-friction recovery "
            "intervention."
        ),
        "PAYMENT_LINK": (
            "A payment link provides an alternative path for the "
            "customer to complete payment."
        ),
        "UPDATE_PAYMENT_METHOD": (
            "Updating the payment method provides an alternative "
            "payment path."
        ),
    }

    if action in action_descriptions:
        reasons.append(action_descriptions[action])

    # Probability.
    reasons.append(
        f"The estimated recovery probability is "
        f"{probability_pct:.2f}%."
    )

    return " ".join(reasons)


# ============================================================
# VALIDATION
# ============================================================

def validate_input(df):
    print("\n" + "=" * 70)
    print("RECOVERYOS CORE DECISION ENGINE")
    print("=" * 70)

    print(f"\nInput:")
    print(INPUT_FILE)

    print(f"\nRows loaded: {len(df):,}")
    print(f"Columns loaded: {len(df.columns)}")

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    print("\nSchema validation: PASS")

    duplicate_ids = int(
        df["failure_id"].duplicated().sum()
    )

    print(f"Duplicate failure IDs: {duplicate_ids}")

    if duplicate_ids != 0:
        raise ValueError(
            "Duplicate failure IDs detected."
        )

    print("Duplicate validation: PASS")

    invalid_actions = (
        set(df["candidate_action"]) - VALID_ACTIONS
    )

    print(f"Invalid actions: {len(invalid_actions)}")

    if invalid_actions:
        raise ValueError(
            f"Invalid actions: {invalid_actions}"
        )

    print("Action validation: PASS")

    numeric_columns = [
        "portfolio_rank",
        "amount",
        "estimated_recovery_probability",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
    ]

    for column in numeric_columns:

        if not pd.api.types.is_numeric_dtype(
            df[column]
        ):
            raise ValueError(
                f"{column} must be numeric."
            )

        if df[column].isna().any():
            raise ValueError(
                f"{column} contains missing values."
            )

    print("Numeric validation: PASS")

    invalid_probabilities = (
        (df["estimated_recovery_probability"] < 0)
        |
        (df["estimated_recovery_probability"] > 1)
    ).sum()

    print(
        "Invalid recovery probabilities: "
        f"{invalid_probabilities}"
    )

    if invalid_probabilities != 0:
        raise ValueError(
            "Recovery probabilities must be between 0 and 1."
        )

    print("Probability validation: PASS")

    # Economic consistency.
    calculated_net = (
        df["expected_gross_recovery"]
        -
        df["intervention_cost"]
    )

    maximum_error = (
        calculated_net
        -
        df["expected_net_recovery"]
    ).abs().max()

    print(
        "Maximum economic calculation error: "
        f"₹{maximum_error:.6f}"
    )

    if maximum_error > 0.01:
        raise ValueError(
            "Expected net recovery is economically inconsistent."
        )

    print("Economic consistency: PASS")

    return df


# ============================================================
# CORE DECISION CREATION
# ============================================================

def create_decisions(df):

    decisions = df.copy()

    # Only selected portfolio opportunities become active
    # recovery decisions.
    decisions = decisions[
        decisions["selected"] == True
    ].copy()

    decisions.reset_index(drop=True, inplace=True)

    decisions["decision_status"] = "RECOMMEND"

    decisions["decision_reason"] = (
        decisions.apply(
            generate_reason,
            axis=1
        )
    )

    # Product-level decision identifier.
    decisions.insert(
        0,
        "decision_id",
        [
            f"DEC_{i:06d}"
            for i in range(1, len(decisions) + 1)
        ],
    )

    # Initial bounded state.
    decisions["execution_status"] = "PENDING"

    return decisions


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def validate_output(decisions):

    print("\n" + "=" * 70)
    print("DECISION ENGINE VALIDATION")
    print("=" * 70)

    print(
        f"Decision records: {len(decisions):,}"
    )

    duplicate_decisions = int(
        decisions["decision_id"].duplicated().sum()
    )

    print(
        f"Duplicate decision IDs: "
        f"{duplicate_decisions}"
    )

    if duplicate_decisions != 0:
        raise ValueError(
            "Duplicate decision IDs detected."
        )

    duplicate_failures = int(
        decisions["failure_id"].duplicated().sum()
    )

    print(
        f"Duplicate failure IDs: "
        f"{duplicate_failures}"
    )

    if duplicate_failures != 0:
        raise ValueError(
            "Duplicate failure IDs detected."
        )

    missing_reasons = int(
        decisions["decision_reason"].isna().sum()
    )

    print(
        f"Missing decision explanations: "
        f"{missing_reasons}"
    )

    if missing_reasons != 0:
        raise ValueError(
            "Decision explanations are missing."
        )

    invalid_status = set(
        decisions["decision_status"]
    ) - {"RECOMMEND"}

    print(
        f"Invalid decision statuses: "
        f"{len(invalid_status)}"
    )

    if invalid_status:
        raise ValueError(
            f"Invalid decision statuses: {invalid_status}"
        )

    print("\nDecision validation: PASS")


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"\nInput file not found:\n{INPUT_FILE}\n\n"
            "Run M11 first."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(INPUT_FILE)

    df = validate_input(df)

    decisions = create_decisions(df)

    if len(decisions) != DEFAULT_CAPACITY:
        raise ValueError(
            f"Expected {DEFAULT_CAPACITY} active decisions, "
            f"found {len(decisions)}."
        )

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
        "execution_status",
    ]

    output = decisions[output_columns].copy()

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    validate_output(output)

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("RECOVERYOS DECISION SUMMARY")
    print("=" * 70)

    print(
        f"\nActive recovery decisions: "
        f"{len(output):,}"
    )

    print(
        f"Revenue represented: "
        f"₹{output['amount'].sum():,.2f}"
    )

    print(
        f"Expected gross recovery: "
        f"₹{output['expected_gross_recovery'].sum():,.2f}"
    )

    print(
        f"Intervention cost: "
        f"₹{output['intervention_cost'].sum():,.2f}"
    )

    print(
        f"Expected NET recovery: "
        f"₹{output['expected_net_recovery'].sum():,.2f}"
    )

    print("\nAction distribution:")

    print(
        output["candidate_action"]
        .value_counts()
        .to_string()
    )

    # ========================================================
    # TOP 5 DECISIONS
    # ========================================================

    print("\n" + "=" * 70)
    print("TOP 5 RECOVERY DECISIONS")
    print("=" * 70)

    display_columns = [
        "decision_id",
        "failure_id",
        "amount",
        "failure_reason",
        "candidate_action",
        "estimated_recovery_probability",
        "expected_net_recovery",
    ]

    print(
        output.head(5)[display_columns].to_string(
            index=False
        )
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print("\n" + "=" * 70)
    print("OUTPUT")
    print("=" * 70)

    print(
        f"\nSaved decisions:"
    )

    print(OUTPUT_FILE)

    print(
        "\nRecoveryOS Core Decision Engine: COMPLETE ✓"
    )


if __name__ == "__main__":
    main()