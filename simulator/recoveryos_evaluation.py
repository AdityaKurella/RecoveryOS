from pathlib import Path
import hashlib
import pandas as pd


# ============================================================
# RECOVERYOS — M16 EVALUATION ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

OUTCOME_FILE = (
    BASE_DIR / "data" / "outcomes"
    / "recoveryos_outcomes.csv"
)

COUNTERFACTUAL_FILE = (
    BASE_DIR / "data"
    / "counterfactual_training.csv"
)

POLICY_FILE = (
    BASE_DIR / "data" / "ml_decision"
    / "m10c_policy_decisions.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "evaluation"

OUTPUT_FILE = (
    OUTPUT_DIR / "recoveryos_evaluation.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "recoveryos_evaluation_summary.csv"
)


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
# DETERMINISTIC SIMULATION
# ============================================================

def deterministic_uniform(key):

    digest = hashlib.sha256(
        key.encode("utf-8")
    ).hexdigest()

    integer = int(
        digest[:16],
        16,
    )

    return integer / float(16 ** 16)


def simulated_recovery(
    failure_id,
    action,
    amount,
    probability,
):

    draw = deterministic_uniform(
        f"{failure_id}|{action}"
    )

    if draw < probability:
        return float(amount)

    return 0.0


# ============================================================
# RULE BASELINE
# ============================================================

def rule_action(row):

    reason = str(
        row["failure_reason"]
    )

    amount = float(
        row["amount"]
    )

    if reason in {
        "CARD_EXPIRED",
        "AUTHENTICATION_FAILED",
    }:
        return "UPDATE_PAYMENT_METHOD"

    if reason == "INSUFFICIENT_FUNDS":
        return "WAIT_AND_RETRY"

    if reason in {
        "BANK_DECLINED",
        "LIMIT_EXCEEDED",
    }:
        return "PAYMENT_LINK"

    if reason == "NETWORK_ERROR":
        return "RETRY_NOW"

    if amount >= 10000:
        return "PAYMENT_LINK"

    return "WAIT_AND_RETRY"


# ============================================================
# VALIDATION
# ============================================================

def validate_inputs(
    outcomes,
    counterfactual,
    policy,
):

    print("\n" + "=" * 70)
    print("RECOVERYOS — M16 EVALUATION ENGINE")
    print("=" * 70)

    print("\nInput files:")

    print(
        f"Outcome records: "
        f"{len(outcomes):,}"
    )

    print(
        f"Counterfactual rows: "
        f"{len(counterfactual):,}"
    )

    print(
        f"RecoveryOS policy decisions: "
        f"{len(policy):,}"
    )

    required_outcome = [
        "failure_id",
        "amount",
        "candidate_action",
        "estimated_recovery_probability",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
        "execution_status",
        "outcome_status",
        "actual_recovered_amount",
    ]

    required_cf = [
        "failure_id",
        "candidate_action",
        "true_recovery_probability",
    ]

    required_policy = [
        "failure_id",
        "candidate_action",
        "expected_gross_recovery",
        "intervention_cost",
        "expected_net_recovery",
    ]

    for column in required_outcome:

        if column not in outcomes.columns:

            raise ValueError(
                f"Missing outcome column: "
                f"{column}"
            )

    for column in required_cf:

        if column not in counterfactual.columns:

            raise ValueError(
                f"Missing counterfactual column: "
                f"{column}"
            )

    for column in required_policy:

        if column not in policy.columns:

            raise ValueError(
                f"Missing policy column: "
                f"{column}"
            )

    print("\nSchema validation: PASS")

    duplicate_outcomes = int(
        outcomes[
            "failure_id"
        ].duplicated().sum()
    )

    duplicate_policy = int(
        policy[
            "failure_id"
        ].duplicated().sum()
    )

    print(
        f"Duplicate outcome failure IDs: "
        f"{duplicate_outcomes}"
    )

    print(
        f"Duplicate policy failure IDs: "
        f"{duplicate_policy}"
    )

    if duplicate_outcomes:
        raise ValueError(
            "Duplicate outcome failure IDs."
        )

    if duplicate_policy:
        raise ValueError(
            "Duplicate policy failure IDs."
        )

    print(
        "Duplicate validation: PASS"
    )


# ============================================================
# BUILD EVALUATION DATASET
# ============================================================

def build_evaluation(
    outcomes,
    counterfactual,
):

    # Only autonomously executed cases are compared.
    ros = outcomes[
        outcomes["execution_status"]
        == "EXECUTED_SIMULATION"
    ].copy()

    print(
        f"\nAutonomous RecoveryOS cases: "
        f"{len(ros):,}"
    )

    # Hidden ground-truth environment.
    cf = counterfactual[
        counterfactual["failure_id"].isin(
            ros["failure_id"]
        )
    ].copy()

    cf = cf[
        cf["candidate_action"].isin(
            ACTIONS
        )
    ].copy()

    duplicate_pairs = int(
        cf.duplicated(
            subset=[
                "failure_id",
                "candidate_action",
            ]
        ).sum()
    )

    if duplicate_pairs:

        raise ValueError(
            "Duplicate failure/action pairs "
            "in counterfactual data."
        )

    print(
        f"Counterfactual action pairs: "
        f"{len(cf):,}"
    )

    print(
        "Counterfactual pair uniqueness: PASS"
    )

    # Pivot hidden true probabilities.
    probability_table = (
        cf.pivot(
            index="failure_id",
            columns="candidate_action",
            values="true_recovery_probability",
        )
        .reset_index()
    )

    probability_table.columns.name = None

    probability_table = probability_table.rename(
        columns={
            action: f"true_prob_{action}"
            for action in ACTIONS
        }
    )

    evaluation = ros.merge(
        probability_table,
        on="failure_id",
        how="left",
        validate="one_to_one",
    )

    probability_columns = [
        f"true_prob_{action}"
        for action in ACTIONS
    ]

    missing_probability_rows = int(
        evaluation[
            probability_columns
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    print(
        f"Missing ground-truth probability rows: "
        f"{missing_probability_rows}"
    )

    if missing_probability_rows:

        raise ValueError(
            "Ground-truth probabilities missing "
            "for evaluation cases."
        )

    print(
        "Ground-truth alignment: PASS"
    )

    return evaluation


# ============================================================
# BENCHMARK CALCULATION
# ============================================================

def calculate_benchmarks(
    evaluation
):

    rows = []

    for _, row in evaluation.iterrows():

        failure_id = row[
            "failure_id"
        ]

        amount = float(
            row["amount"]
        )

        # ----------------------------------------------------
        # RECOVERYOS
        # ----------------------------------------------------

        ros_action = row[
            "candidate_action"
        ]

        ros_probability = float(
            row[
                f"true_prob_{ros_action}"
            ]
        )

        ros_actual = simulated_recovery(
            failure_id,
            ros_action,
            amount,
            ros_probability,
        )

        ros_cost = ACTION_COSTS[
            ros_action
        ]

        ros_net = (
            ros_actual
            - ros_cost
        )

        # ----------------------------------------------------
        # RULES
        # ----------------------------------------------------

        rules_action = rule_action(
            row
        )

        rules_probability = float(
            row[
                f"true_prob_{rules_action}"
            ]
        )

        rules_actual = simulated_recovery(
            failure_id,
            rules_action,
            amount,
            rules_probability,
        )

        rules_cost = ACTION_COSTS[
            rules_action
        ]

        rules_net = (
            rules_actual
            - rules_cost
        )

        # ----------------------------------------------------
        # ORACLE
        # ----------------------------------------------------

        true_probabilities = {
            action: float(
                row[
                    f"true_prob_{action}"
                ]
            )
            for action in ACTIONS
        }

        oracle_action = max(
            ACTIONS,
            key=lambda action:
                (
                    amount
                    * true_probabilities[action]
                    - ACTION_COSTS[action]
                ),
        )

        oracle_probability = (
            true_probabilities[
                oracle_action
            ]
        )

        oracle_actual = simulated_recovery(
            failure_id,
            oracle_action,
            amount,
            oracle_probability,
        )

        oracle_cost = ACTION_COSTS[
            oracle_action
        ]

        oracle_net = (
            oracle_actual
            - oracle_cost
        )

        rows.append(
            {
                "failure_id": failure_id,
                "amount": amount,

                "recoveryos_action":
                    ros_action,

                "recoveryos_true_probability":
                    ros_probability,

                "recoveryos_actual_revenue":
                    ros_actual,

                "recoveryos_cost":
                    ros_cost,

                "recoveryos_net_revenue":
                    ros_net,

                "rules_action":
                    rules_action,

                "rules_true_probability":
                    rules_probability,

                "rules_actual_revenue":
                    rules_actual,

                "rules_cost":
                    rules_cost,

                "rules_net_revenue":
                    rules_net,

                "oracle_action":
                    oracle_action,

                "oracle_true_probability":
                    oracle_probability,

                "oracle_actual_revenue":
                    oracle_actual,

                "oracle_cost":
                    oracle_cost,

                "oracle_net_revenue":
                    oracle_net,

                "recoveryos_vs_rules_net":
                    ros_net - rules_net,

                "recoveryos_vs_oracle_net":
                    ros_net - oracle_net,

                "oracle_opportunity_loss":
                    oracle_net - ros_net,
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# SUMMARY
# ============================================================

def calculate_summary(
    evaluation
):

    total_cases = len(
        evaluation
    )

    amount = evaluation[
        "amount"
    ].sum()

    ros_actual = evaluation[
        "recoveryos_actual_revenue"
    ].sum()

    ros_cost = evaluation[
        "recoveryos_cost"
    ].sum()

    ros_net = evaluation[
        "recoveryos_net_revenue"
    ].sum()

    rules_actual = evaluation[
        "rules_actual_revenue"
    ].sum()

    rules_cost = evaluation[
        "rules_cost"
    ].sum()

    rules_net = evaluation[
        "rules_net_revenue"
    ].sum()

    oracle_actual = evaluation[
        "oracle_actual_revenue"
    ].sum()

    oracle_cost = evaluation[
        "oracle_cost"
    ].sum()

    oracle_net = evaluation[
        "oracle_net_revenue"
    ].sum()

    ros_rate = (
        ros_actual / amount * 100
        if amount else 0
    )

    rules_rate = (
        rules_actual / amount * 100
        if amount else 0
    )

    oracle_rate = (
        oracle_actual / amount * 100
        if amount else 0
    )

    ros_vs_rules = (
        ros_net - rules_net
    )

    ros_vs_oracle = (
        ros_net - oracle_net
    )

    oracle_gap = abs(
        ros_vs_oracle
    )

    oracle_gap_pct = (
        oracle_gap
        / oracle_net
        * 100
        if oracle_net
        else 0
    )

    action_match = (
        evaluation[
            "recoveryos_action"
        ]
        ==
        evaluation[
            "oracle_action"
        ]
    ).sum()

    action_match_rate = (
        action_match
        / total_cases
        * 100
        if total_cases
        else 0
    )

    return pd.DataFrame(
        [
            {
                "metric":
                    "Cases evaluated",
                "recoveryos":
                    total_cases,
                "rules":
                    total_cases,
                "oracle":
                    total_cases,
            },
            {
                "metric":
                    "Revenue at risk",
                "recoveryos":
                    amount,
                "rules":
                    amount,
                "oracle":
                    amount,
            },
            {
                "metric":
                    "Actual recovered revenue (simulated)",
                "recoveryos":
                    ros_actual,
                "rules":
                    rules_actual,
                "oracle":
                    oracle_actual,
            },
            {
                "metric":
                    "Intervention cost",
                "recoveryos":
                    ros_cost,
                "rules":
                    rules_cost,
                "oracle":
                    oracle_cost,
            },
            {
                "metric":
                    "Net recovered revenue (simulated)",
                "recoveryos":
                    ros_net,
                "rules":
                    rules_net,
                "oracle":
                    oracle_net,
            },
            {
                "metric":
                    "Recovery rate %",
                "recoveryos":
                    ros_rate,
                "rules":
                    rules_rate,
                "oracle":
                    oracle_rate,
            },
            {
                "metric":
                    "RecoveryOS vs Rules net",
                "recoveryos":
                    ros_vs_rules,
                "rules":
                    0,
                "oracle":
                    0,
            },
            {
                "metric":
                    "RecoveryOS vs Oracle net",
                "recoveryos":
                    ros_vs_oracle,
                "rules":
                    0,
                "oracle":
                    0,
            },
            {
                "metric":
                    "RecoveryOS oracle action match %",
                "recoveryos":
                    action_match_rate,
                "rules":
                    None,
                "oracle":
                    100.0,
            },
            {
                "metric":
                    "Oracle opportunity gap %",
                "recoveryos":
                    oracle_gap_pct,
                "rules":
                    None,
                "oracle":
                    0.0,
            },
        ]
    )


# ============================================================
# ACTION ANALYSIS
# ============================================================

def print_action_analysis(
    evaluation
):

    print("\n" + "=" * 70)
    print("RECOVERYOS ACTION PERFORMANCE")
    print("=" * 70)

    action_summary = (
        evaluation
        .groupby(
            "recoveryos_action"
        )
        .agg(
            cases=(
                "failure_id",
                "count",
            ),
            actual_revenue=(
                "recoveryos_actual_revenue",
                "sum",
            ),
            cost=(
                "recoveryos_cost",
                "sum",
            ),
            net_revenue=(
                "recoveryos_net_revenue",
                "sum",
            ),
            oracle_net=(
                "oracle_net_revenue",
                "sum",
            ),
        )
        .reset_index()
    )

    action_summary[
        "oracle_gap"
    ] = (
        action_summary[
            "oracle_net"
        ]
        -
        action_summary[
            "net_revenue"
        ]
    )

    print(
        action_summary.to_string(
            index=False
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not OUTCOME_FILE.exists():

        raise FileNotFoundError(
            f"Outcome file not found:\n"
            f"{OUTCOME_FILE}"
        )

    if not COUNTERFACTUAL_FILE.exists():

        raise FileNotFoundError(
            f"Counterfactual file not found:\n"
            f"{COUNTERFACTUAL_FILE}"
        )

    if not POLICY_FILE.exists():

        raise FileNotFoundError(
            f"Policy file not found:\n"
            f"{POLICY_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    outcomes = pd.read_csv(
        OUTCOME_FILE
    )

    counterfactual = pd.read_csv(
        COUNTERFACTUAL_FILE
    )

    policy = pd.read_csv(
        POLICY_FILE
    )

    validate_inputs(
        outcomes,
        counterfactual,
        policy,
    )

    evaluation = build_evaluation(
        outcomes,
        counterfactual,
    )

    evaluation = calculate_benchmarks(
        evaluation
    )

    summary = calculate_summary(
        evaluation
    )

    # --------------------------------------------------------
    # EVALUATION VALIDATION
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("EVALUATION VALIDATION")
    print("=" * 70)

    print(
        f"Cases evaluated: "
        f"{len(evaluation):,}"
    )

    duplicate_cases = int(
        evaluation[
            "failure_id"
        ].duplicated().sum()
    )

    print(
        f"Duplicate evaluation cases: "
        f"{duplicate_cases}"
    )

    if duplicate_cases:

        raise ValueError(
            "Duplicate evaluation cases."
        )

    print(
        "Evaluation uniqueness: PASS"
    )

    numeric_columns = [
        "recoveryos_actual_revenue",
        "recoveryos_cost",
        "recoveryos_net_revenue",
        "rules_actual_revenue",
        "rules_cost",
        "rules_net_revenue",
        "oracle_actual_revenue",
        "oracle_cost",
        "oracle_net_revenue",
    ]

    invalid_numeric = 0

    for column in numeric_columns:

        values = pd.to_numeric(
            evaluation[column],
            errors="coerce",
        )

        invalid_numeric += int(
            values.isna().sum()
        )

    print(
        f"Invalid numeric evaluation values: "
        f"{invalid_numeric}"
    )

    if invalid_numeric:

        raise ValueError(
            "Invalid numeric evaluation values."
        )

    print(
        "Numeric validation: PASS"
    )

    # --------------------------------------------------------
    # ECONOMIC CONSISTENCY
    # --------------------------------------------------------

    invalid_recovery = 0

    for column in [
        "recoveryos_actual_revenue",
        "rules_actual_revenue",
        "oracle_actual_revenue",
    ]:

        invalid_recovery += int(
            (
                evaluation[column]
                > evaluation["amount"]
            ).sum()
        )

    print(
        f"Recovery exceeding payment amount: "
        f"{invalid_recovery}"
    )

    if invalid_recovery:

        raise ValueError(
            "Recovery exceeds payment amount."
        )

    print(
        "Economic consistency: PASS"
    )

    # --------------------------------------------------------
    # ACTION VALIDATION
    # --------------------------------------------------------

    invalid_ros_actions = (
        set(
            evaluation[
                "recoveryos_action"
            ]
        )
        - set(ACTIONS)
    )

    invalid_rule_actions = (
        set(
            evaluation[
                "rules_action"
            ]
        )
        - set(ACTIONS)
    )

    invalid_oracle_actions = (
        set(
            evaluation[
                "oracle_action"
            ]
        )
        - set(ACTIONS)
    )

    print(
        f"Invalid RecoveryOS actions: "
        f"{len(invalid_ros_actions)}"
    )

    print(
        f"Invalid rules actions: "
        f"{len(invalid_rule_actions)}"
    )

    print(
        f"Invalid oracle actions: "
        f"{len(invalid_oracle_actions)}"
    )

    if (
        invalid_ros_actions
        or invalid_rule_actions
        or invalid_oracle_actions
    ):

        raise ValueError(
            "Invalid actions detected."
        )

    print(
        "Action validation: PASS"
    )

    print(
        "\nEvaluation validation: PASS"
    )

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)

    print(
        summary.to_string(
            index=False
        )
    )

    print_action_analysis(
        evaluation
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    evaluation.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    print("\n" + "=" * 70)
    print("OUTPUT")
    print("=" * 70)

    print(
        "\nDetailed evaluation:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\nEvaluation summary:"
    )

    print(
        SUMMARY_FILE
    )

    print(
        "\nM16 Evaluation Engine: COMPLETE ✓"
    )


if __name__ == "__main__":
    main()