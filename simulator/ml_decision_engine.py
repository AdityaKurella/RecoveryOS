import csv
import pickle
from pathlib import Path

import pandas as pd


ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
    "NO_ACTION",
]


ACTION_COSTS = {
    "RETRY_NOW": 2.00,
    "WAIT_AND_RETRY": 2.00,
    "SEND_REMINDER": 1.00,
    "PAYMENT_LINK": 3.00,
    "UPDATE_PAYMENT_METHOD": 3.00,
    "NO_ACTION": 0.00,
}


NUMERIC_FEATURES = [
    "amount",
    "account_age_days",
    "successful_payments",
    "failed_payments",
    "total_payments",
    "payment_success_rate",
    "historical_recovery_rate",
    "engagement_score",
]


CATEGORICAL_FEATURES = [
    "failure_reason",
    "behavior_profile",
    "action_taken",
]


MODEL_FEATURES = (
    NUMERIC_FEATURES
    + CATEGORICAL_FEATURES
)


def load_csv(filename):

    path = (
        Path(__file__).parent.parent
        / "data"
        / filename
    )

    with open(
        path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


def load_model():

    path = (
        Path(__file__).parent.parent
        / "data"
        / "recovery_probability_model.pkl"
    )

    with open(
        path,
        "rb",
    ) as file:

        return pickle.load(file)


def build_action_row(
    row,
    action,
):

    result = {}

    for feature in NUMERIC_FEATURES:

        result[feature] = float(
            row[feature]
        )

    for feature in [
        "failure_reason",
        "behavior_profile",
    ]:

        result[feature] = row[
            feature
        ]

    # The action is deliberately supplied
    # as a feature to the trained model.

    result["action_taken"] = action

    return result


def predict_probability(
    model,
    row,
    action,
):

    action_row = build_action_row(
        row,
        action,
    )

    X = pd.DataFrame(
        [action_row],
        columns=MODEL_FEATURES,
    )

    probability = model.predict_proba(
        X
    )[0][1]

    return float(probability)


def calculate_expected_net_value(
    amount,
    probability,
    action,
):

    return (
        amount * probability
        - ACTION_COSTS[action]
    )


def choose_ml_action(
    model,
    row,
):

    amount = float(
        row["amount"]
    )

    action_scores = []

    for action in ACTIONS:

        if action == "NO_ACTION":

            probability = 0.0

        else:

            probability = (
                predict_probability(
                    model,
                    row,
                    action,
                )
            )

        expected_net_value = (
            calculate_expected_net_value(
                amount,
                probability,
                action,
            )
        )

        action_scores.append(
            {
                "action": action,
                "probability": probability,
                "expected_net_value":
                    expected_net_value,
                "action_cost":
                    ACTION_COSTS[action],
            }
        )

    best = max(
        action_scores,
        key=lambda item:
            item["expected_net_value"],
    )

    return best, action_scores


def generate_decisions(
    model,
    test_rows,
):

    decisions = []

    for row in test_rows:

        best, scores = (
            choose_ml_action(
                model,
                row,
            )
        )

        ranked = sorted(
            scores,
            key=lambda item:
                item["expected_net_value"],
            reverse=True,
        )

        second_best = ranked[1]

        margin = (
            best["expected_net_value"]
            - second_best["expected_net_value"]
        )

        decision = {
            "failure_id":
                row["failure_id"],

            "payment_id":
                row["payment_id"],

            "customer_id":
                row["customer_id"],

            "subscription_id":
                row["subscription_id"],

            "amount":
                float(row["amount"]),

            "failure_reason":
                row["failure_reason"],

            "behavior_profile":
                row["behavior_profile"],

            "selected_action":
                best["action"],

            "estimated_recovery_probability":
                round(
                    best["probability"],
                    4,
                ),

            "action_cost":
                round(
                    best["action_cost"],
                    2,
                ),

            "expected_net_value":
                round(
                    best["expected_net_value"],
                    2,
                ),

            "decision_margin":
                round(
                    margin,
                    2,
                ),
        }

        decisions.append(
            decision
        )

    return decisions


def save_decisions(
    decisions,
):

    path = (
        Path(__file__).parent.parent
        / "data"
        / "ml_decision_outputs.csv"
    )

    fieldnames = [
        "failure_id",
        "payment_id",
        "customer_id",
        "subscription_id",
        "amount",
        "failure_reason",
        "behavior_profile",
        "selected_action",
        "estimated_recovery_probability",
        "action_cost",
        "expected_net_value",
        "decision_margin",
    ]

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            decisions
        )

    return path


def validate_decisions(
    decisions,
    test_rows,
):

    print(
        "\n========== ML DECISION VALIDATION =========="
    )

    print(
        f"Test rows: {len(test_rows)}"
    )

    print(
        f"ML decisions: {len(decisions)}"
    )

    test_ids = {
        row["failure_id"]
        for row in test_rows
    }

    decision_ids = {
        row["failure_id"]
        for row in decisions
    }

    print(
        f"Missing decisions: "
        f"{len(test_ids - decision_ids)}"
    )

    print(
        f"Extra decisions: "
        f"{len(decision_ids - test_ids)}"
    )

    duplicates = (
        len(decisions)
        - len(decision_ids)
    )

    print(
        f"Duplicate decision IDs: "
        f"{duplicates}"
    )

    valid_actions = set(
        ACTIONS
    )

    invalid_actions = [
        decision
        for decision in decisions
        if decision["selected_action"]
        not in valid_actions
    ]

    print(
        f"Invalid actions: "
        f"{len(invalid_actions)}"
    )

    invalid_probabilities = [
        decision
        for decision in decisions
        if not (
            0.0
            <= float(
                decision[
                    "estimated_recovery_probability"
                ]
            )
            <= 1.0
        )
    ]

    print(
        f"Invalid probabilities: "
        f"{len(invalid_probabilities)}"
    )

    action_counts = {}

    for decision in decisions:

        action = decision[
            "selected_action"
        ]

        action_counts[action] = (
            action_counts.get(
                action,
                0,
            )
            + 1
        )

    print(
        "\nML selected action distribution:"
    )

    for action, count in sorted(
        action_counts.items()
    ):

        percentage = (
            count
            / len(decisions)
            * 100
        )

        print(
            f"  {action}: "
            f"{count} "
            f"({percentage:.2f}%)"
        )

    if decisions:

        total_expected_value = sum(
            float(
                decision[
                    "expected_net_value"
                ]
            )
            for decision in decisions
        )

        print(
            f"\nTotal model-predicted "
            f"net value: "
            f"₹{total_expected_value:,.2f}"
        )

        sample = decisions[0]

        print(
            "\nSample ML decision:"
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
            f"  Estimated probability: "
            f"{float(sample['estimated_recovery_probability']):.2%}"
        )

        print(
            f"  Expected net value: "
            f"₹{float(sample['expected_net_value']):,.2f}"
        )

    print(
        "============================================"
    )


def main():

    print(
        "Loading trained RecoveryOS model..."
    )

    model = load_model()

    test_rows = load_csv(
        "test_features.csv"
    )

    print(
        f"Loaded {len(test_rows)} "
        f"untouched test cases."
    )

    print(
        "\nGenerating ML decisions..."
    )

    decisions = generate_decisions(
        model,
        test_rows,
    )

    print(
        f"Generated {len(decisions)} "
        f"ML decisions"
    )

    output_path = save_decisions(
        decisions
    )

    print(
        f"ML decision dataset saved to: "
        f"{output_path}"
    )

    validate_decisions(
        decisions,
        test_rows,
    )

    print(
        "\nM9C complete. ✅"
    )


if __name__ == "__main__":
    main()