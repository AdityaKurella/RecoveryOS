from pathlib import Path
from datetime import datetime, timezone
import uuid
import pandas as pd


# ============================================================
# RECOVERYOS — BOUNDED EXECUTION ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "policy"
    / "recoveryos_policy_decisions.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "execution"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "recoveryos_execution_results.csv"
)

ALLOWED_EXECUTION_ACTIONS = {
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
}

ALLOWED_POLICY_RESULTS = {
    "ALLOW",
    "HUMAN",
    "STOP",
}

VALID_EXECUTION_STATUSES = {
    "EXECUTED_SIMULATION",
    "NOT_AUTONOMOUSLY_EXECUTED",
    "NOT_EXECUTED",
}


# ============================================================
# SINGLE DECISION EXECUTION
# ============================================================

def execute_decision(row, execution_number):

    execution_id = (
        f"EXE_{execution_number:06d}_"
        f"{uuid.uuid4().hex[:8].upper()}"
    )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    policy_result = row["policy_result"]
    action = row["candidate_action"]

    # --------------------------------------------------------
    # HUMAN
    # --------------------------------------------------------

    if policy_result == "HUMAN":

        return {
            "execution_id": execution_id,
            "execution_timestamp": timestamp,
            "execution_result": "HUMAN_ESCALATION",
            "execution_status": "NOT_AUTONOMOUSLY_EXECUTED",
            "execution_reason": (
                "Policy requires human review before "
                "recovery execution."
            ),
        }

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if policy_result == "STOP":

        return {
            "execution_id": execution_id,
            "execution_timestamp": timestamp,
            "execution_result": "STOPPED",
            "execution_status": "NOT_EXECUTED",
            "execution_reason": (
                "Policy blocked the recovery action."
            ),
        }

    # --------------------------------------------------------
    # Unknown policy state
    # --------------------------------------------------------

    if policy_result not in ALLOWED_POLICY_RESULTS:

        return {
            "execution_id": execution_id,
            "execution_timestamp": timestamp,
            "execution_result": "BLOCKED",
            "execution_status": "NOT_EXECUTED",
            "execution_reason": (
                "Unknown policy state."
            ),
        }

    # --------------------------------------------------------
    # ALLOW
    # --------------------------------------------------------

    if policy_result == "ALLOW":

        if action not in ALLOWED_EXECUTION_ACTIONS:

            return {
                "execution_id": execution_id,
                "execution_timestamp": timestamp,
                "execution_result": "BLOCKED",
                "execution_status": "NOT_EXECUTED",
                "execution_reason": (
                    "Action is not present in the "
                    "execution allowlist."
                ),
            }

        return {
            "execution_id": execution_id,
            "execution_timestamp": timestamp,
            "execution_result": action,
            "execution_status": "EXECUTED_SIMULATION",
            "execution_reason": (
                "Action passed deterministic policy "
                "controls and was executed in the "
                "RecoveryOS test environment."
            ),
        }


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_input(df):

    print("\n" + "=" * 70)
    print("RECOVERYOS — BOUNDED EXECUTION ENGINE")
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
        "candidate_action",
        "estimated_recovery_probability",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
        "policy_result",
        "policy_reason",
        "policy_checks",
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
        - ALLOWED_EXECUTION_ACTIONS
    )

    print(
        f"Invalid actions: "
        f"{len(invalid_actions)}"
    )

    if invalid_actions:
        raise ValueError(
            f"Invalid actions: {invalid_actions}"
        )

    print("Action allowlist validation: PASS")

    invalid_policy_results = (
        set(df["policy_result"])
        - ALLOWED_POLICY_RESULTS
    )

    print(
        f"Invalid policy results: "
        f"{len(invalid_policy_results)}"
    )

    if invalid_policy_results:
        raise ValueError(
            f"Invalid policy results: "
            f"{invalid_policy_results}"
        )

    print("Policy-state validation: PASS")

    return df


# ============================================================
# EXECUTE BATCH
# ============================================================

def execute_batch(df):

    base = df.copy()

    # Remove any old execution columns before adding the
    # newly generated execution results.
    execution_columns = [
        "execution_id",
        "execution_timestamp",
        "execution_result",
        "execution_status",
        "execution_reason",
    ]

    base = base.drop(
        columns=[
            column
            for column in execution_columns
            if column in base.columns
        ],
        errors="ignore",
    )

    records = []

    for execution_number, (_, row) in enumerate(
        base.iterrows(),
        start=1,
    ):

        record = execute_decision(
            row,
            execution_number,
        )

        records.append(record)

    execution_df = pd.DataFrame(records)

    # Explicitly concatenate after removing old execution
    # columns. This guarantees unique column names.
    results = pd.concat(
        [
            base.reset_index(drop=True),
            execution_df.reset_index(drop=True),
        ],
        axis=1,
    )

    # Defensive duplicate-column check.
    duplicate_columns = results.columns[
        results.columns.duplicated()
    ].tolist()

    if duplicate_columns:
        raise ValueError(
            f"Duplicate output columns detected: "
            f"{duplicate_columns}"
        )

    return results


# ============================================================
# EXECUTION VALIDATION
# ============================================================

def validate_execution(results):

    print("\n" + "=" * 70)
    print("EXECUTION VALIDATION")
    print("=" * 70)

    print(
        f"Execution records: "
        f"{len(results):,}"
    )

    duplicate_columns = results.columns[
        results.columns.duplicated()
    ].tolist()

    print(
        f"Duplicate output columns: "
        f"{len(duplicate_columns)}"
    )

    if duplicate_columns:
        raise ValueError(
            f"Duplicate columns: {duplicate_columns}"
        )

    print("Output-column uniqueness: PASS")

    duplicate_execution_ids = int(
        results["execution_id"].duplicated().sum()
    )

    print(
        f"Duplicate execution IDs: "
        f"{duplicate_execution_ids}"
    )

    if duplicate_execution_ids != 0:
        raise ValueError(
            "Duplicate execution IDs detected."
        )

    print("Execution ID validation: PASS")

    missing_timestamps = int(
        results["execution_timestamp"].isna().sum()
    )

    print(
        f"Missing execution timestamps: "
        f"{missing_timestamps}"
    )

    if missing_timestamps != 0:
        raise ValueError(
            "Missing execution timestamps."
        )

    print("Timestamp validation: PASS")

    invalid_statuses = (
        set(results["execution_status"])
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

    # --------------------------------------------------------
    # HUMAN SAFETY
    # --------------------------------------------------------

    human_rows = results[
        results["policy_result"] == "HUMAN"
    ]

    human_violations = human_rows[
        human_rows["execution_status"]
        == "EXECUTED_SIMULATION"
    ]

    print(
        "Human autonomous-execution violations: "
        f"{len(human_violations)}"
    )

    if len(human_violations) != 0:
        raise ValueError(
            "HUMAN decisions were autonomously executed."
        )

    print(
        "Human escalation safety check: PASS"
    )

    # --------------------------------------------------------
    # STOP SAFETY
    # --------------------------------------------------------

    stop_rows = results[
        results["policy_result"] == "STOP"
    ]

    stop_violations = stop_rows[
        stop_rows["execution_status"]
        == "EXECUTED_SIMULATION"
    ]

    print(
        "STOP autonomous-execution violations: "
        f"{len(stop_violations)}"
    )

    if len(stop_violations) != 0:
        raise ValueError(
            "STOP decisions were executed."
        )

    print(
        "Stopping-rule safety check: PASS"
    )

    # --------------------------------------------------------
    # ALLOW CONSISTENCY
    # --------------------------------------------------------

    allow_rows = results[
        results["policy_result"] == "ALLOW"
    ]

    failed_allow = allow_rows[
        allow_rows["execution_status"]
        != "EXECUTED_SIMULATION"
    ]

    print(
        "ALLOW execution failures: "
        f"{len(failed_allow)}"
    )

    if len(failed_allow) != 0:
        raise ValueError(
            "Some ALLOW decisions failed execution."
        )

    print(
        "Allow-execution consistency: PASS"
    )

    print(
        "\nExecution validation: PASS"
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results):

    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)

    total = len(results)

    executed = int(
        (
            results["execution_status"]
            == "EXECUTED_SIMULATION"
        ).sum()
    )

    human = int(
        (
            results["execution_status"]
            == "NOT_AUTONOMOUSLY_EXECUTED"
        ).sum()
    )

    stopped = int(
        (
            results["execution_status"]
            == "NOT_EXECUTED"
        ).sum()
    )

    print(
        f"\nTotal decisions: "
        f"{total}"
    )

    print(
        f"Autonomously executed: "
        f"{executed}"
    )

    print(
        f"Human escalations: "
        f"{human}"
    )

    print(
        f"Stopped / blocked: "
        f"{stopped}"
    )

    print("\nExecution actions:")

    executed_rows = results[
        results["execution_status"]
        == "EXECUTED_SIMULATION"
    ]

    if len(executed_rows) > 0:

        print(
            executed_rows[
                "execution_result"
            ]
            .value_counts()
            .to_string()
        )

    else:

        print("No autonomous executions.")

    print("\n" + "=" * 70)
    print("EXECUTION ECONOMIC EXPOSURE")
    print("=" * 70)

    if len(executed_rows) > 0:

        print(
            f"\nRevenue represented by executed actions: "
            f"₹{executed_rows['amount'].sum():,.2f}"
        )

        print(
            f"Expected gross recovery: "
            f"₹{executed_rows['expected_gross_recovery'].sum():,.2f}"
        )

        print(
            f"Expected net recovery: "
            f"₹{executed_rows['expected_net_recovery'].sum():,.2f}"
        )

    print("\n" + "=" * 70)
    print("SAMPLE EXECUTIONS")
    print("=" * 70)

    display_columns = [
        "execution_id",
        "failure_id",
        "amount",
        "candidate_action",
        "policy_result",
        "execution_result",
        "execution_status",
    ]

    print(
        results[
            display_columns
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
            f"\nInput file not found:\n{INPUT_FILE}\n\n"
            "Run policy_guardrails.py first."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(
        INPUT_FILE
    )

    df = validate_input(df)

    results = execute_batch(df)

    validate_execution(results)

    print_summary(results)

    output_columns = [
        "execution_id",
        "execution_timestamp",
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
        "policy_result",
        "policy_reason",
        "policy_checks",
        "execution_result",
        "execution_status",
        "execution_reason",
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
        "\nSaved execution results:"
    )

    print(OUTPUT_FILE)

    print(
        "\nBounded Execution Engine: COMPLETE ✓"
    )


if __name__ == "__main__":
    main()