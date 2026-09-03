import csv
from pathlib import Path


# ============================================================
# ACTION COSTS
# ============================================================

ACTION_COSTS = {
    "RETRY_NOW": 2.00,
    "WAIT_AND_RETRY": 2.00,
    "SEND_REMINDER": 1.00,
    "PAYMENT_LINK": 3.00,
    "UPDATE_PAYMENT_METHOD": 3.00,
    "NO_ACTION": 0.00,
}


ACTIONS = list(ACTION_COSTS.keys())


# ============================================================
# BASE ACTION PROBABILITIES
# ============================================================
#
# These are INITIAL ESTIMATES used by the decision engine.
#
# IMPORTANT:
# These are NOT the hidden ground-truth probabilities.
# The engine is intentionally using an imperfect model.
#
# Later we will replace/improve this estimator using data.
# ============================================================

BASE_ESTIMATES = {
    "INSUFFICIENT_FUNDS": {
        "RETRY_NOW": 0.20,
        "WAIT_AND_RETRY": 0.50,
        "SEND_REMINDER": 0.30,
        "PAYMENT_LINK": 0.40,
        "UPDATE_PAYMENT_METHOD": 0.15,
        "NO_ACTION": 0.00,
    },

    "CARD_EXPIRED": {
        "RETRY_NOW": 0.05,
        "WAIT_AND_RETRY": 0.05,
        "SEND_REMINDER": 0.20,
        "PAYMENT_LINK": 0.30,
        "UPDATE_PAYMENT_METHOD": 0.70,
        "NO_ACTION": 0.00,
    },

    "BANK_DECLINED": {
        "RETRY_NOW": 0.20,
        "WAIT_AND_RETRY": 0.45,
        "SEND_REMINDER": 0.25,
        "PAYMENT_LINK": 0.35,
        "UPDATE_PAYMENT_METHOD": 0.20,
        "NO_ACTION": 0.00,
    },

    "NETWORK_ERROR": {
        "RETRY_NOW": 0.75,
        "WAIT_AND_RETRY": 0.65,
        "SEND_REMINDER": 0.20,
        "PAYMENT_LINK": 0.25,
        "UPDATE_PAYMENT_METHOD": 0.10,
        "NO_ACTION": 0.00,
    },

    "AUTHENTICATION_FAILED": {
        "RETRY_NOW": 0.05,
        "WAIT_AND_RETRY": 0.10,
        "SEND_REMINDER": 0.30,
        "PAYMENT_LINK": 0.40,
        "UPDATE_PAYMENT_METHOD": 0.55,
        "NO_ACTION": 0.00,
    },

    "LIMIT_EXCEEDED": {
        "RETRY_NOW": 0.10,
        "WAIT_AND_RETRY": 0.20,
        "SEND_REMINDER": 0.20,
        "PAYMENT_LINK": 0.50,
        "UPDATE_PAYMENT_METHOD": 0.30,
        "NO_ACTION": 0.00,
    },
}


def load_features():
    input_path = (
        Path(__file__).parent.parent
        / "data"
        / "train_features.csv"
    )

    with open(
        input_path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def clamp(value, minimum=0.01, maximum=0.99):
    return max(
        minimum,
        min(value, maximum),
    )


def estimate_probability(row, action):
    """
    Estimate recovery probability using ONLY observable
    features.

    The hidden ground truth is deliberately not used.
    """

    if action == "NO_ACTION":
        return 0.0

    failure_reason = row["failure_reason"]

    probability = BASE_ESTIMATES[
        failure_reason
    ][action]

    engagement = float(
        row["engagement_score"]
    )

    historical_recovery = float(
        row["historical_recovery_rate"]
    )

    payment_reliability = float(
        row["payment_reliability"]
    )

    failure_ratio = float(
        row["failure_ratio"]
    )

    amount = float(
        row["amount"]
    )

    # --------------------------------------------------------
    # CUSTOMER RESPONSIVENESS
    # --------------------------------------------------------

    if action in {
        "SEND_REMINDER",
        "PAYMENT_LINK",
        "UPDATE_PAYMENT_METHOD",
    }:

        probability += (
            engagement - 0.5
        ) * 0.10

    # --------------------------------------------------------
    # HISTORICAL RECOVERY SIGNAL
    # --------------------------------------------------------

    probability += (
        historical_recovery - 0.60
    ) * 0.08

    # --------------------------------------------------------
    # PAYMENT RELIABILITY
    # --------------------------------------------------------

    if action in {
        "RETRY_NOW",
        "WAIT_AND_RETRY",
    }:

        probability += (
            payment_reliability - 0.80
        ) * 0.08

    # --------------------------------------------------------
    # HIGH FAILURE RATIO PENALTY
    # --------------------------------------------------------

    if failure_ratio > 0.25:

        if action in {
            "RETRY_NOW",
            "WAIT_AND_RETRY",
        }:

            probability -= 0.05

    # --------------------------------------------------------
    # HIGH-VALUE PAYMENT ADJUSTMENT
    # --------------------------------------------------------
    #
    # This does NOT mean high-value customers are more
    # recoverable.
    #
    # We simply make the engine slightly more conservative
    # about low-probability actions for expensive payments.
    # --------------------------------------------------------

    if amount >= 5000:

        if probability < 0.25:

            probability -= 0.02

    return clamp(probability)


def calculate_expected_net_value(
    amount,
    probability,
    action,
):
    expected_revenue = (
        amount * probability
    )

    cost = ACTION_COSTS[action]

    expected_net_value = (
        expected_revenue - cost
    )

    return expected_net_value


def choose_action(row):
    """
    Evaluate every available action and choose the one
    with the highest expected net value.
    """

    amount = float(row["amount"])

    decisions = []

    for action in ACTIONS:

        probability = estimate_probability(
            row,
            action,
        )

        expected_net_value = (
            calculate_expected_net_value(
                amount,
                probability,
                action,
            )
        )

        decisions.append(
            {
                "action": action,
                "estimated_probability": probability,
                "expected_net_value": expected_net_value,
                "action_cost": ACTION_COSTS[action],
            }
        )

    best_decision = max(
        decisions,
        key=lambda item: item[
            "expected_net_value"
        ],
    )

    return best_decision, decisions


def create_decision(row):
    """
    Create a complete explainable decision record.
    """

    best_decision, all_decisions = choose_action(
        row
    )

    amount = float(row["amount"])

    ranked_decisions = sorted(
        all_decisions,
        key=lambda item: item[
            "expected_net_value"
        ],
        reverse=True,
    )

    second_best = (
        ranked_decisions[1]
        if len(ranked_decisions) > 1
        else None
    )

    if second_best:

        decision_margin = (
            best_decision["expected_net_value"]
            - second_best["expected_net_value"]
        )

    else:
        decision_margin = (
            best_decision["expected_net_value"]
        )

    return {
        "failure_id": row["failure_id"],
        "payment_id": row["payment_id"],
        "customer_id": row["customer_id"],
        "subscription_id": row["subscription_id"],
        "amount": amount,
        "failure_reason": row["failure_reason"],
        "failure_category": row["failure_category"],
        "behavior_profile": row["behavior_profile"],
        "selected_action": best_decision["action"],
        "estimated_recovery_probability": round(
            best_decision[
                "estimated_probability"
            ],
            4,
        ),
        "action_cost": round(
            best_decision["action_cost"],
            2,
        ),
        "expected_net_value": round(
            best_decision["expected_net_value"],
            2,
        ),
        "decision_margin": round(
            decision_margin,
            2,
        ),
    }


def generate_decisions(rows):
    decisions = []

    for row in rows:

        decision = create_decision(row)

        decisions.append(decision)

    return decisions


def save_decisions(decisions):
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "decision_outputs.csv"
    )

    fieldnames = [
        "failure_id",
        "payment_id",
        "customer_id",
        "subscription_id",
        "amount",
        "failure_reason",
        "failure_category",
        "behavior_profile",
        "selected_action",
        "estimated_recovery_probability",
        "action_cost",
        "expected_net_value",
        "decision_margin",
    ]

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(decisions)

    return output_path


def validate_decisions(
    decisions,
    input_rows,
):
    print(
        "\n========== DECISION ENGINE VALIDATION =========="
    )

    print(
        f"Input feature rows: {len(input_rows)}"
    )

    print(
        f"Decision rows: {len(decisions)}"
    )

    # --------------------------------------------------------
    # COVERAGE
    # --------------------------------------------------------

    if len(decisions) == len(input_rows):

        print(
            "Decision coverage: 100.00%"
        )

    else:

        coverage = (
            len(decisions)
            / len(input_rows)
            * 100
        )

        print(
            f"Decision coverage: {coverage:.2f}%"
        )

    # --------------------------------------------------------
    # DUPLICATE IDS
    # --------------------------------------------------------

    decision_ids = [
        decision["failure_id"]
        for decision in decisions
    ]

    duplicate_ids = (
        len(decision_ids)
        - len(set(decision_ids))
    )

    print(
        f"Duplicate decision IDs: "
        f"{duplicate_ids}"
    )

    # --------------------------------------------------------
    # VALID ACTIONS
    # --------------------------------------------------------

    valid_actions = set(ACTIONS)

    invalid_actions = [
        decision
        for decision in decisions
        if decision["selected_action"]
        not in valid_actions
    ]

    print(
        f"Invalid selected actions: "
        f"{len(invalid_actions)}"
    )

    # --------------------------------------------------------
    # PROBABILITY VALIDATION
    # --------------------------------------------------------

    invalid_probabilities = [
        decision
        for decision in decisions
        if not 0.0
        <= float(
            decision[
                "estimated_recovery_probability"
            ]
        )
        <= 0.99
    ]

    print(
        f"Invalid estimated probabilities: "
        f"{len(invalid_probabilities)}"
    )

    # --------------------------------------------------------
    # ACTION DISTRIBUTION
    # --------------------------------------------------------

    action_counts = {}

    for decision in decisions:

        action = decision[
            "selected_action"
        ]

        action_counts[action] = (
            action_counts.get(action, 0)
            + 1
        )

    print("\nSelected action distribution:")

    for action, count in sorted(
        action_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    ):

        percentage = (
            count
            / len(decisions)
            * 100
        )

        print(
            f"  {action}: "
            f"{count} ({percentage:.2f}%)"
        )

    # --------------------------------------------------------
    # EXPECTED VALUE
    # --------------------------------------------------------

    total_expected_value = sum(
        float(
            decision["expected_net_value"]
        )
        for decision in decisions
    )

    print(
        f"\nTotal expected net value: "
        f"₹{total_expected_value:,.2f}"
    )

    # --------------------------------------------------------
    # SAMPLE DECISION
    # --------------------------------------------------------

    if decisions:

        sample = decisions[0]

        print(
            "\nSample RecoveryOS decision:"
        )

        print(
            f"  Failure: "
            f"{sample['failure_id']}"
        )

        print(
            f"  Amount: "
            f"₹{float(sample['amount']):,.2f}"
        )

        print(
            f"  Failure reason: "
            f"{sample['failure_reason']}"
        )

        print(
            f"  Selected action: "
            f"{sample['selected_action']}"
        )

        print(
            f"  Estimated recovery probability: "
            f"{float(sample['estimated_recovery_probability']):.2%}"
        )

        print(
            f"  Action cost: "
            f"₹{float(sample['action_cost']):,.2f}"
        )

        print(
            f"  Expected net value: "
            f"₹{float(sample['expected_net_value']):,.2f}"
        )

        print(
            f"  Decision margin: "
            f"₹{float(sample['decision_margin']):,.2f}"
        )

    print(
        "================================================="
    )


if __name__ == "__main__":

    rows = load_features()

    decisions = generate_decisions(
        rows
    )

    print(
        f"Generated {len(decisions)} "
        f"RecoveryOS decisions"
    )

    output_path = save_decisions(
        decisions
    )

    print(
        f"Decision dataset saved to: "
        f"{output_path}"
    )

    validate_decisions(
        decisions,
        rows,
    )