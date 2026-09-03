from pathlib import Path
from datetime import datetime, timezone
import uuid
import hashlib
import pandas as pd


# ============================================================
# RECOVERYOS — M15 OUTCOME + AUDIT TRAIL
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "execution"
    / "recoveryos_execution_results.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "outcomes"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "recoveryos_outcomes.csv"
)

VALID_EXECUTION_STATUSES = {
    "EXECUTED_SIMULATION",
    "NOT_AUTONOMOUSLY_EXECUTED",
    "NOT_EXECUTED",
}

VALID_OUTCOME_STATUSES = {
    "RECOVERED",
    "NOT_RECOVERED",
    "AWAITING_HUMAN",
    "NOT_ATTEMPTED",
}

VALID_EXECUTION_RESULTS = {
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
    "HUMAN_ESCALATION",
    "STOPPED",
    "BLOCKED",
}


# ============================================================
# DETERMINISTIC OUTCOME SIMULATION
# ============================================================

def deterministic_uniform(key):
    """
    Generates a deterministic value in [0, 1).

    This makes the demo reproducible:
    same failure + action = same simulated outcome.
    """

    digest = hashlib.sha256(
        key.encode("utf-8")
    ).hexdigest()

    integer = int(
        digest[:16],
        16
    )

    return integer / float(16 ** 16)


def simulate_outcome(row):

    execution_status = row["execution_status"]

    probability = float(
        row["estimated_recovery_probability"]
    )

    amount = float(row["amount"])

    execution_result = row["execution_result"]

    # --------------------------------------------------------
    # HUMAN
    # --------------------------------------------------------

    if execution_status == "NOT_AUTONOMOUSLY_EXECUTED":

        return {
            "outcome_status": "AWAITING_HUMAN",
            "recovered": False,
            "actual_recovered_amount": 0.0,
            "outcome_reason": (
                "Recovery action requires human approval "
                "and was not autonomously executed."
            ),
        }

    # --------------------------------------------------------
    # STOP / BLOCK
    # --------------------------------------------------------

    if execution_status == "NOT_EXECUTED":

        return {
            "outcome_status": "NOT_ATTEMPTED",
            "recovered": False,
            "actual_recovered_amount": 0.0,
            "outcome_reason": (
                "Recovery action was blocked or stopped "
                "by policy."
            ),
        }

    # --------------------------------------------------------
    # AUTONOMOUS EXECUTION
    # --------------------------------------------------------

    if execution_status != "EXECUTED_SIMULATION":

        raise ValueError(
            f"Unexpected execution status: "
            f"{execution_status}"
        )

    # Stable pseudo-random outcome.
    seed = (
        f"{row['failure_id']}|"
        f"{execution_result}"
    )

    draw = deterministic_uniform(seed)

    recovered = draw < probability

    if recovered:

        return {
            "outcome_status": "RECOVERED",
            "recovered": True,
            "actual_recovered_amount": amount,
            "outcome_reason": (
                "Simulated payment recovery succeeded "
                "after the executed intervention."
            ),
        }

    return {
        "outcome_status": "NOT_RECOVERED",
        "recovered": False,
        "actual_recovered_amount": 0.0,
        "outcome_reason": (
            "Simulated intervention completed, but "
            "the payment was not recovered."
        ),
    }


# ============================================================
# AUDIT ID
# ============================================================

def create_audit_id(row):

    raw = (
        f"{row['execution_id']}|"
        f"{row['decision_id']}|"
        f"{row['failure_id']}"
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:12].upper()

    return f"AUD_{digest}"


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_input(df):

    print("\n" + "=" * 70)
    print("RECOVERYOS — M15 OUTCOME + AUDIT TRAIL")
    print("=" * 70)

    print("\nInput:")
    print(INPUT_FILE)

    print(f"\nRows loaded: {len(df):,}")
    print(f"Columns loaded: {len(df.columns)}")

    required_columns = [
        "execution_id",
        "execution_timestamp",
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
        "policy_result",
        "policy_reason",
        "policy_checks",
        "execution_result",
        "execution_status",
        "execution_reason",
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

    duplicate_execution_ids = int(
        df["execution_id"].duplicated().sum()
    )

    duplicate_decision_ids = int(
        df["decision_id"].duplicated().sum()
    )

    duplicate_failure_ids = int(
        df["failure_id"].duplicated().sum()
    )

    print(
        f"Duplicate execution IDs: "
        f"{duplicate_execution_ids}"
    )

    print(
        f"Duplicate decision IDs: "
        f"{duplicate_decision_ids}"
    )

    print(
        f"Duplicate failure IDs: "
        f"{duplicate_failure_ids}"
    )

    if (
        duplicate_execution_ids
        or duplicate_decision_ids
        or duplicate_failure_ids
    ):

        raise ValueError(
            "Duplicate trace identifiers detected."
        )

    print("Traceability validation: PASS")

    invalid_statuses = (
        set(df["execution_status"])
        - VALID_EXECUTION_STATUSES
    )

    print(
        f"Invalid execution statuses: "
        f"{len(invalid_statuses)}"
    )

    if invalid_statuses:

        raise ValueError(
            f"Invalid execution statuses: "
            f"{invalid_statuses}"
        )

    print("Execution-status validation: PASS")

    invalid_results = (
        set(df["execution_result"])
        - VALID_EXECUTION_RESULTS
    )

    print(
        f"Invalid execution results: "
        f"{len(invalid_results)}"
    )

    if invalid_results:

        raise ValueError(
            f"Invalid execution results: "
            f"{invalid_results}"
        )

    print("Execution-result validation: PASS")

    # --------------------------------------------------------
    # PROBABILITY VALIDATION
    # --------------------------------------------------------

    probability = pd.to_numeric(
        df["estimated_recovery_probability"],
        errors="coerce",
    )

    invalid_probability = (
        probability.isna()
        | (probability < 0)
        | (probability > 1)
    )

    print(
        f"Invalid recovery probabilities: "
        f"{int(invalid_probability.sum())}"
    )

    if invalid_probability.any():

        raise ValueError(
            "Invalid recovery probabilities detected."
        )

    print("Probability validation: PASS")

    # --------------------------------------------------------
    # ECONOMIC VALIDATION
    # --------------------------------------------------------

    numeric_columns = [
        "amount",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
    ]

    for column in numeric_columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        if values.isna().any():

            raise ValueError(
                f"Invalid numeric values in {column}."
            )

    print("Economic-field validation: PASS")

    return df


# ============================================================
# BUILD OUTCOMES
# ============================================================

def build_outcomes(df):

    outcome_records = []

    for _, row in df.iterrows():

        outcome = simulate_outcome(row)

        record = {
            "audit_id": create_audit_id(row),

            "outcome_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            # -----------------------------
            # TRACEABILITY
            # -----------------------------

            "execution_id": row["execution_id"],
            "decision_id": row["decision_id"],
            "failure_id": row["failure_id"],
            "customer_id": row["customer_id"],
            "subscription_id": row["subscription_id"],

            # -----------------------------
            # PAYMENT
            # -----------------------------

            "amount": float(row["amount"]),
            "failure_reason": row["failure_reason"],

            # -----------------------------
            # DECISION
            # -----------------------------

            "candidate_action": row["candidate_action"],
            "estimated_recovery_probability": float(
                row[
                    "estimated_recovery_probability"
                ]
            ),

            "expected_gross_recovery": float(
                row["expected_gross_recovery"]
            ),

            "intervention_cost": float(
                row["intervention_cost"]
            ),

            "expected_net_recovery": float(
                row["expected_net_recovery"]
            ),

            # -----------------------------
            # POLICY
            # -----------------------------

            "policy_result": row["policy_result"],
            "policy_reason": row["policy_reason"],
            "policy_checks": row["policy_checks"],

            # -----------------------------
            # EXECUTION
            # -----------------------------

            "execution_result": row[
                "execution_result"
            ],

            "execution_status": row[
                "execution_status"
            ],

            "execution_reason": row[
                "execution_reason"
            ],

            # -----------------------------
            # OUTCOME
            # -----------------------------

            "outcome_status": outcome[
                "outcome_status"
            ],

            "recovered": outcome[
                "recovered"
            ],

            "actual_recovered_amount": outcome[
                "actual_recovered_amount"
            ],

            "outcome_reason": outcome[
                "outcome_reason"
            ],
        }

        outcome_records.append(record)

    return pd.DataFrame(outcome_records)


# ============================================================
# OUTCOME VALIDATION
# ============================================================

def validate_outcomes(results):

    print("\n" + "=" * 70)
    print("OUTCOME + AUDIT VALIDATION")
    print("=" * 70)

    print(
        f"Outcome records: "
        f"{len(results):,}"
    )

    # --------------------------------------------------------
    # AUDIT IDS
    # --------------------------------------------------------

    duplicate_audit_ids = int(
        results["audit_id"].duplicated().sum()
    )

    print(
        f"Duplicate audit IDs: "
        f"{duplicate_audit_ids}"
    )

    if duplicate_audit_ids:

        raise ValueError(
            "Duplicate audit IDs detected."
        )

    print("Audit-ID validation: PASS")

    # --------------------------------------------------------
    # OUTCOME STATUS
    # --------------------------------------------------------

    invalid_outcomes = (
        set(results["outcome_status"])
        - VALID_OUTCOME_STATUSES
    )

    print(
        f"Invalid outcome statuses: "
        f"{len(invalid_outcomes)}"
    )

    if invalid_outcomes:

        raise ValueError(
            f"Invalid outcome statuses: "
            f"{invalid_outcomes}"
        )

    print("Outcome-status validation: PASS")

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    timestamps = pd.to_datetime(
        results["outcome_timestamp"],
        errors="coerce",
        utc=True,
    )

    missing_timestamps = int(
        timestamps.isna().sum()
    )

    print(
        f"Invalid outcome timestamps: "
        f"{missing_timestamps}"
    )

    if missing_timestamps:

        raise ValueError(
            "Invalid outcome timestamps."
        )

    print("Timestamp validation: PASS")

    # --------------------------------------------------------
    # RECOVERY AMOUNT
    # --------------------------------------------------------

    recovered_amount = pd.to_numeric(
        results["actual_recovered_amount"],
        errors="coerce",
    )

    invalid_recovery_amount = (
        recovered_amount.isna()
        | (recovered_amount < 0)
        | (
            recovered_amount
            > results["amount"]
        )
    )

    print(
        f"Invalid actual recovery amounts: "
        f"{int(invalid_recovery_amount.sum())}"
    )

    if invalid_recovery_amount.any():

        raise ValueError(
            "Invalid actual recovery amounts."
        )

    print(
        "Actual-recovery validation: PASS"
    )

    # --------------------------------------------------------
    # RECOVERED FLAG CONSISTENCY
    # --------------------------------------------------------

    recovered_status = (
        results["outcome_status"]
        == "RECOVERED"
    )

    inconsistent_flags = (
        results["recovered"]
        != recovered_status
    )

    print(
        f"Recovery-flag inconsistencies: "
        f"{int(inconsistent_flags.sum())}"
    )

    if inconsistent_flags.any():

        raise ValueError(
            "Recovered flag is inconsistent "
            "with outcome status."
        )

    print(
        "Recovery-status consistency: PASS"
    )

    # --------------------------------------------------------
    # SAFETY: HUMAN
    # --------------------------------------------------------

    human_rows = results[
        results["execution_status"]
        == "NOT_AUTONOMOUSLY_EXECUTED"
    ]

    human_execution = human_rows[
        human_rows["outcome_status"]
        == "RECOVERED"
    ]

    print(
        f"Human cases marked recovered: "
        f"{len(human_execution)}"
    )

    if len(human_execution):

        raise ValueError(
            "Human-only cases cannot be marked "
            "as autonomously recovered."
        )

    print(
        "Human outcome safety check: PASS"
    )

    # --------------------------------------------------------
    # SAFETY: NOT EXECUTED
    # --------------------------------------------------------

    stopped_rows = results[
        results["execution_status"]
        == "NOT_EXECUTED"
    ]

    stopped_recovered = stopped_rows[
        stopped_rows["outcome_status"]
        == "RECOVERED"
    ]

    print(
        f"Stopped cases marked recovered: "
        f"{len(stopped_recovered)}"
    )

    if len(stopped_recovered):

        raise ValueError(
            "Stopped cases cannot be recovered "
            "without execution."
        )

    print(
        "Stopped-outcome safety check: PASS"
    )

    # --------------------------------------------------------
    # ECONOMIC CONSISTENCY
    # --------------------------------------------------------

    invalid_economics = results[
        results["actual_recovered_amount"]
        > results["amount"]
    ]

    if len(invalid_economics):

        raise ValueError(
            "Actual recovery exceeds payment amount."
        )

    print(
        "Economic consistency: PASS"
    )

    print(
        "\nOutcome + audit validation: PASS"
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results):

    print("\n" + "=" * 70)
    print("RECOVERYOS — OUTCOME SUMMARY")
    print("=" * 70)

    total = len(results)

    recovered = int(
        (
            results["outcome_status"]
            == "RECOVERED"
        ).sum()
    )

    not_recovered = int(
        (
            results["outcome_status"]
            == "NOT_RECOVERED"
        ).sum()
    )

    human = int(
        (
            results["outcome_status"]
            == "AWAITING_HUMAN"
        ).sum()
    )

    not_attempted = int(
        (
            results["outcome_status"]
            == "NOT_ATTEMPTED"
        ).sum()
    )

    actual_recovered = (
        results[
            "actual_recovered_amount"
        ].sum()
    )

    executed = int(
        (
            results["execution_status"]
            == "EXECUTED_SIMULATION"
        ).sum()
    )

    print(
        f"\nTotal cases: "
        f"{total}"
    )

    print(
        f"Executed interventions: "
        f"{executed}"
    )

    print(
        f"Recovered: "
        f"{recovered}"
    )

    print(
        f"Not recovered: "
        f"{not_recovered}"
    )

    print(
        f"Awaiting human: "
        f"{human}"
    )

    print(
        f"Not attempted: "
        f"{not_attempted}"
    )

    print(
        f"\nACTUAL RECOVERED REVENUE: "
        f"₹{actual_recovered:,.2f}"
    )

    if executed > 0:

        executed_results = results[
            results["execution_status"]
            == "EXECUTED_SIMULATION"
        ]

        executed_amount = executed_results[
            "amount"
        ].sum()

        recovery_rate = (
            actual_recovered
            / executed_amount
            * 100
        )

        print(
            f"Actual recovery rate on "
            f"executed interventions: "
            f"{recovery_rate:.2f}%"
        )

    # --------------------------------------------------------
    # ACTION PERFORMANCE
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("ACTION OUTCOMES")
    print("=" * 70)

    action_summary = (
        results[
            results["execution_status"]
            == "EXECUTED_SIMULATION"
        ]
        .groupby("candidate_action")
        .agg(
            cases=(
                "failure_id",
                "count",
            ),
            recovered=(
                "recovered",
                "sum",
            ),
            actual_revenue=(
                "actual_recovered_amount",
                "sum",
            ),
            expected_revenue=(
                "expected_gross_recovery",
                "sum",
            ),
        )
        .reset_index()
    )

    if len(action_summary):

        action_summary[
            "actual_recovery_rate"
        ] = (
            action_summary["recovered"]
            / action_summary["cases"]
            * 100
        )

        print(
            action_summary.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # SAMPLE AUDIT RECORDS
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("SAMPLE AUDIT RECORDS")
    print("=" * 70)

    sample_columns = [
        "audit_id",
        "failure_id",
        "candidate_action",
        "execution_status",
        "outcome_status",
        "actual_recovered_amount",
    ]

    print(
        results[
            sample_columns
        ]
        .head(10)
        .to_string(index=False)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"\nInput file not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run recovery_execution.py first."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(
        INPUT_FILE
    )

    df = validate_input(df)

    results = build_outcomes(df)

    validate_outcomes(results)

    print_summary(results)

    output_columns = [
        "audit_id",
        "outcome_timestamp",
        "execution_id",
        "decision_id",
        "failure_id",
        "customer_id",
        "subscription_id",
        "amount",
        "failure_reason",
        "candidate_action",
        "estimated_recovery_probability",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
        "policy_result",
        "policy_reason",
        "policy_checks",
        "execution_result",
        "execution_status",
        "execution_reason",
        "outcome_status",
        "recovered",
        "actual_recovered_amount",
        "outcome_reason",
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
        "\nSaved outcome + audit records:"
    )

    print(OUTPUT_FILE)

    print(
        "\nM15 Outcome + Audit Trail: COMPLETE ✓"
    )


if __name__ == "__main__":
    main()