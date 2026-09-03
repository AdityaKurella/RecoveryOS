from pathlib import Path
import pandas as pd


# ============================================================
# M11 — RECOVERY PORTFOLIO ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "ml_decision" / "m10c_policy_decisions.csv"
OUTPUT_DIR = BASE_DIR / "data" / "portfolio"
OUTPUT_FILE = OUTPUT_DIR / "m11_recovery_portfolio.csv"

CAPACITIES = [50, 100, 250]
DEFAULT_CAPACITY = 100

REQUIRED_COLUMNS = [
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

VALID_ACTIONS = {
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
}


def validate_input(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("M11 — RECOVERY PORTFOLIO ENGINE")
    print("=" * 70)

    print(f"\nInput file:")
    print(INPUT_FILE)

    print(f"\nRows loaded: {len(df):,}")
    print(f"Columns loaded: {len(df.columns)}")

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    print("\nSchema validation: PASS")

    duplicate_count = int(df["failure_id"].duplicated().sum())

    print(f"Duplicate failure IDs: {duplicate_count}")

    if duplicate_count > 0:
        raise ValueError("Duplicate failure IDs detected.")

    print("Duplicate validation: PASS")

    numeric_columns = [
        "amount",
        "estimated_recovery_probability",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
    ]

    for column in numeric_columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(
                f"Column '{column}' must be numeric."
            )

        if df[column].isna().any():
            raise ValueError(
                f"Column '{column}' contains missing values."
            )

    print("Numeric validation: PASS")

    probability_invalid = (
        (df["estimated_recovery_probability"] < 0)
        | (df["estimated_recovery_probability"] > 1)
    ).sum()

    print(
        f"Invalid recovery probabilities: {probability_invalid}"
    )

    if probability_invalid > 0:
        raise ValueError(
            "Recovery probabilities must be between 0 and 1."
        )

    print("Probability validation: PASS")

    invalid_actions = set(df["candidate_action"]) - VALID_ACTIONS

    print(f"Invalid actions: {len(invalid_actions)}")

    if invalid_actions:
        raise ValueError(
            f"Invalid actions found: {invalid_actions}"
        )

    print("Action validation: PASS")

    # Verify economic consistency.
    expected_net = (
        df["expected_gross_recovery"]
        - df["intervention_cost"]
    )

    economics_error = (
        expected_net - df["expected_net_recovery"]
    ).abs().max()

    print(
        f"Maximum economic calculation error: "
        f"₹{economics_error:.6f}"
    )

    if economics_error > 0.01:
        raise ValueError(
            "Expected net recovery is inconsistent with "
            "gross recovery minus intervention cost."
        )

    print("Economic consistency: PASS")

    return df


def rank_portfolio(df: pd.DataFrame):
    """
    Rank recovery opportunities.

    Primary objective:
        expected_net_recovery

    Secondary tie-breakers:
        expected_gross_recovery
        estimated_recovery_probability
        amount
        failure_id
    """

    ranked = df.copy()

    ranked = ranked.sort_values(
        by=[
            "expected_net_recovery",
            "expected_gross_recovery",
            "estimated_recovery_probability",
            "amount",
            "failure_id",
        ],
        ascending=[
            False,
            False,
            False,
            False,
            True,
        ],
        kind="mergesort",
    ).reset_index(drop=True)

    ranked.insert(
        0,
        "portfolio_rank",
        range(1, len(ranked) + 1),
    )

    ranked["selected"] = False

    return ranked


def calculate_portfolio_metrics(
    df: pd.DataFrame,
    capacity: int,
):
    selected = df.head(capacity).copy()

    revenue_at_risk = selected["amount"].sum()
    expected_gross = selected["expected_gross_recovery"].sum()
    intervention_cost = selected["intervention_cost"].sum()
    expected_net = selected["expected_net_recovery"].sum()

    if revenue_at_risk > 0:
        expected_recovery_rate = (
            expected_gross / revenue_at_risk
        )
    else:
        expected_recovery_rate = 0.0

    return {
        "capacity": capacity,
        "selected_cases": len(selected),
        "revenue_at_risk": revenue_at_risk,
        "expected_gross_recovery": expected_gross,
        "intervention_cost": intervention_cost,
        "expected_net_recovery": expected_net,
        "expected_recovery_rate": expected_recovery_rate,
    }


def print_capacity_analysis(ranked: pd.DataFrame):
    print("\n" + "=" * 70)
    print("PORTFOLIO CAPACITY ANALYSIS")
    print("=" * 70)

    for capacity in CAPACITIES:
        metrics = calculate_portfolio_metrics(
            ranked,
            capacity,
        )

        print(f"\nCapacity: {capacity}")

        print(
            f"  Cases selected:          "
            f"{metrics['selected_cases']:,}"
        )

        print(
            f"  Revenue at risk:         "
            f"₹{metrics['revenue_at_risk']:,.2f}"
        )

        print(
            f"  Expected gross recovery: "
            f"₹{metrics['expected_gross_recovery']:,.2f}"
        )

        print(
            f"  Intervention cost:       "
            f"₹{metrics['intervention_cost']:,.2f}"
        )

        print(
            f"  Expected NET recovery:   "
            f"₹{metrics['expected_net_recovery']:,.2f}"
        )

        print(
            f"  Expected recovery rate:  "
            f"{metrics['expected_recovery_rate'] * 100:.2f}%"
        )


def validate_portfolio_output(
    ranked: pd.DataFrame,
):
    print("\n" + "=" * 70)
    print("M11 PORTFOLIO VALIDATION")
    print("=" * 70)

    expected_rows = len(ranked)

    if len(ranked) != expected_rows:
        raise ValueError("Portfolio row count changed unexpectedly.")

    print(
        f"Portfolio rows: {len(ranked):,}"
    )

    duplicate_ids = int(
        ranked["failure_id"].duplicated().sum()
    )

    print(
        f"Duplicate failure IDs: {duplicate_ids}"
    )

    if duplicate_ids != 0:
        raise ValueError(
            "Portfolio contains duplicate failure IDs."
        )

    expected_ranks = list(range(1, len(ranked) + 1))
    actual_ranks = ranked["portfolio_rank"].tolist()

    if actual_ranks != expected_ranks:
        raise ValueError(
            "Portfolio ranks are not continuous."
        )

    print("Rank continuity: PASS")

    selected_count = int(
        ranked["selected"].sum()
    )

    if selected_count != DEFAULT_CAPACITY:
        raise ValueError(
            f"Expected {DEFAULT_CAPACITY} selected cases, "
            f"found {selected_count}."
        )

    print(
        f"Default capacity selection ({DEFAULT_CAPACITY}): PASS"
    )

    # Verify selected cases are the highest-ranked cases.
    expected_selected = (
        ranked["portfolio_rank"] <= DEFAULT_CAPACITY
    )

    if not (
        ranked["selected"] == expected_selected
    ).all():
        raise ValueError(
            "Selected portfolio does not match ranking."
        )

    print("Selection/ranking consistency: PASS")

    # Verify ranking monotonicity.
    net_values = ranked["expected_net_recovery"].tolist()

    for i in range(len(net_values) - 1):
        if net_values[i] < net_values[i + 1]:
            raise ValueError(
                "Portfolio is not sorted by expected net recovery."
            )

    print("Expected-net ranking: PASS")

    print("\nM11 VALIDATION: PASS")


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"\nInput file not found:\n{INPUT_FILE}\n\n"
            "Run M10C first so that "
            "m10c_policy_decisions.csv exists."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(INPUT_FILE)

    df = validate_input(df)

    ranked = rank_portfolio(df)

    # Select the default portfolio capacity.
    ranked["selected"] = (
        ranked["portfolio_rank"] <= DEFAULT_CAPACITY
    )

    print_capacity_analysis(ranked)

    # Keep the portfolio output focused on product-relevant fields.
    output_columns = [
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

    output = ranked[output_columns].copy()

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    validate_portfolio_output(output)

    print("\n" + "=" * 70)
    print("TOP 10 RECOVERY OPPORTUNITIES")
    print("=" * 70)

    display_columns = [
        "portfolio_rank",
        "failure_id",
        "amount",
        "failure_reason",
        "candidate_action",
        "estimated_recovery_probability",
        "expected_net_recovery",
    ]

    print(
        output.head(10)[display_columns].to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("OUTPUT")
    print("=" * 70)

    print(f"\nSaved portfolio:")
    print(OUTPUT_FILE)

    print(
        "\nM11 Recovery Portfolio Engine: COMPLETE ✓"
    )


if __name__ == "__main__":
    main()