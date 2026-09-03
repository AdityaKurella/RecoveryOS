import csv
import random
from pathlib import Path


random.seed(42)


# ============================================================
# SYNTHETIC RECOVERY ACTION EFFECTIVENESS
# ============================================================
#
# These are simulation assumptions.
# They are NOT Razorpay production statistics.
#
# Values represent the base probability that an action
# successfully recovers a failed payment.
# ============================================================

BASE_ACTION_PROBABILITIES = {
    "INSUFFICIENT_FUNDS": {
        "RETRY_NOW": 0.20,
        "WAIT_AND_RETRY": 0.60,
        "SEND_REMINDER": 0.35,
        "PAYMENT_LINK": 0.45,
        "UPDATE_PAYMENT_METHOD": 0.15,
    },

    "CARD_EXPIRED": {
        "RETRY_NOW": 0.05,
        "WAIT_AND_RETRY": 0.05,
        "SEND_REMINDER": 0.20,
        "PAYMENT_LINK": 0.35,
        "UPDATE_PAYMENT_METHOD": 0.80,
    },

    "BANK_DECLINED": {
        "RETRY_NOW": 0.20,
        "WAIT_AND_RETRY": 0.50,
        "SEND_REMINDER": 0.25,
        "PAYMENT_LINK": 0.40,
        "UPDATE_PAYMENT_METHOD": 0.20,
    },

    "NETWORK_ERROR": {
        "RETRY_NOW": 0.85,
        "WAIT_AND_RETRY": 0.70,
        "SEND_REMINDER": 0.25,
        "PAYMENT_LINK": 0.30,
        "UPDATE_PAYMENT_METHOD": 0.10,
    },

    "AUTHENTICATION_FAILED": {
        "RETRY_NOW": 0.05,
        "WAIT_AND_RETRY": 0.10,
        "SEND_REMINDER": 0.35,
        "PAYMENT_LINK": 0.45,
        "UPDATE_PAYMENT_METHOD": 0.65,
    },

    "LIMIT_EXCEEDED": {
        "RETRY_NOW": 0.10,
        "WAIT_AND_RETRY": 0.25,
        "SEND_REMINDER": 0.20,
        "PAYMENT_LINK": 0.55,
        "UPDATE_PAYMENT_METHOD": 0.35,
    },
}


ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
    "NO_ACTION",
]


# ============================================================
# ACTION COSTS
# ============================================================
#
# Synthetic assumptions for experimentation.
# ============================================================

ACTION_COSTS = {
    "RETRY_NOW": 2.00,
    "WAIT_AND_RETRY": 2.00,
    "SEND_REMINDER": 1.00,
    "PAYMENT_LINK": 3.00,
    "UPDATE_PAYMENT_METHOD": 3.00,
    "NO_ACTION": 0.00,
}


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
        return list(csv.DictReader(file))


def clamp_probability(value):
    """
    Keep probabilities between 0 and 1.
    """
    return max(
        0.01,
        min(value, 0.99),
    )


def calculate_context_adjustment(
    customer,
    failure_reason,
    action,
):
    """
    Apply small contextual adjustments to the
    base recovery probability.

    These adjustments are intentionally limited.
    """

    profile = customer["behavior_profile"]

    engagement = float(
        customer["engagement_score"]
    )

    historical_recovery = float(
        customer["historical_recovery_rate"]
    )

    adjustment = 0.0

    # --------------------------------------------------------
    # ENGAGEMENT EFFECT
    # --------------------------------------------------------

    customer_action_actions = {
        "SEND_REMINDER",
        "PAYMENT_LINK",
        "UPDATE_PAYMENT_METHOD",
    }

    if action in customer_action_actions:

        # Higher engagement increases responsiveness.
        adjustment += (
            engagement - 0.5
        ) * 0.12

    # --------------------------------------------------------
    # HISTORICAL RECOVERY EFFECT
    # --------------------------------------------------------

    adjustment += (
        historical_recovery - 0.60
    ) * 0.08

    # --------------------------------------------------------
    # PROFILE-SPECIFIC EFFECTS
    # --------------------------------------------------------

    if profile == "reliable":

        if action in {
            "RETRY_NOW",
            "WAIT_AND_RETRY",
        }:
            adjustment += 0.03

    elif profile == "friction_prone":

        if action in {
            "RETRY_NOW",
            "WAIT_AND_RETRY",
        }:
            adjustment -= 0.04

    elif profile == "high_value_loyal":

        if action in {
            "PAYMENT_LINK",
            "UPDATE_PAYMENT_METHOD",
        }:
            adjustment += 0.03

    elif profile == "low_engagement":

        if action in {
            "SEND_REMINDER",
            "PAYMENT_LINK",
            "UPDATE_PAYMENT_METHOD",
        }:
            adjustment -= 0.05

    return adjustment


def calculate_true_probability(
    customer,
    failure_reason,
    action,
):
    """
    Calculate the hidden true recovery probability.

    RecoveryOS must NOT receive this value.
    """

    if action == "NO_ACTION":
        return 0.0

    base_probability = BASE_ACTION_PROBABILITIES[
        failure_reason
    ][action]

    adjustment = calculate_context_adjustment(
        customer,
        failure_reason,
        action,
    )

    true_probability = (
        base_probability + adjustment
    )

    return clamp_probability(
        true_probability
    )


def generate_ground_truth(
    failures,
    customers,
):
    """
    Generate hidden effectiveness probabilities
    for every possible recovery action.
    """

    ground_truth = []

    customers_by_id = {
        customer["customer_id"]: customer
        for customer in customers
    }

    for failure in failures:

        customer = customers_by_id[
            failure["customer_id"]
        ]

        failure_reason = failure[
            "failure_reason"
        ]

        record = {
            "failure_id": failure["failure_id"],
            "payment_id": failure["payment_id"],
            "customer_id": failure["customer_id"],
            "subscription_id": (
                failure["subscription_id"]
            ),
            "failure_reason": failure_reason,
        }

        for action in ACTIONS:

            probability = calculate_true_probability(
                customer,
                failure_reason,
                action,
            )

            field_name = (
                f"{action.lower()}_probability"
            )

            record[field_name] = round(
                probability,
                4,
            )

        ground_truth.append(record)

    return ground_truth


def save_ground_truth(ground_truth):
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "recovery_ground_truth.csv"
    )

    fieldnames = [
        "failure_id",
        "payment_id",
        "customer_id",
        "subscription_id",
        "failure_reason",
        "retry_now_probability",
        "wait_and_retry_probability",
        "send_reminder_probability",
        "payment_link_probability",
        "update_payment_method_probability",
        "no_action_probability",
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
        writer.writerows(
            ground_truth
        )

    return output_path


def validate_ground_truth(
    ground_truth,
    failures,
):
    print(
        "\n========== GROUND TRUTH VALIDATION =========="
    )

    print(
        f"Failure records loaded: "
        f"{len(failures)}"
    )

    print(
        f"Ground-truth records generated: "
        f"{len(ground_truth)}"
    )

    # --------------------------------------------------------
    # RECORD COUNT
    # --------------------------------------------------------

    if len(ground_truth) == len(failures):
        print(
            "Failure coverage: 100.00%"
        )
    else:
        coverage = (
            len(ground_truth)
            / len(failures)
            * 100
        )

        print(
            f"Failure coverage: {coverage:.2f}%"
        )

    # --------------------------------------------------------
    # DUPLICATE FAILURE IDS
    # --------------------------------------------------------

    failure_ids = [
        record["failure_id"]
        for record in ground_truth
    ]

    duplicate_failure_ids = (
        len(failure_ids)
        - len(set(failure_ids))
    )

    print(
        f"Duplicate failure IDs: "
        f"{duplicate_failure_ids}"
    )

    # --------------------------------------------------------
    # PROBABILITY VALIDATION
    # --------------------------------------------------------

    probability_fields = [
        "retry_now_probability",
        "wait_and_retry_probability",
        "send_reminder_probability",
        "payment_link_probability",
        "update_payment_method_probability",
        "no_action_probability",
    ]

    invalid_probability_values = []

    for record in ground_truth:

        for field in probability_fields:

            value = float(
                record[field]
            )

            if not 0.0 <= value <= 1.0:
                invalid_probability_values.append(
                    record["failure_id"]
                )

    print(
        f"Invalid probability values: "
        f"{len(invalid_probability_values)}"
    )

    # --------------------------------------------------------
    # NO-ACTION VALIDATION
    # --------------------------------------------------------

    invalid_no_action = [
        record
        for record in ground_truth
        if float(
            record["no_action_probability"]
        ) != 0.0
    ]

    print(
        f"Invalid NO_ACTION probabilities: "
        f"{len(invalid_no_action)}"
    )

    # --------------------------------------------------------
    # FAILURE REFERENCES
    # --------------------------------------------------------

    known_failure_ids = {
        failure["failure_id"]
        for failure in failures
    }

    invalid_references = [
        record
        for record in ground_truth
        if record["failure_id"]
        not in known_failure_ids
    ]

    print(
        f"Invalid failure references: "
        f"{len(invalid_references)}"
    )

    # --------------------------------------------------------
    # SAMPLE RECORD
    # --------------------------------------------------------

    if ground_truth:

        sample = ground_truth[0]

        print(
            "\nSample hidden ground truth:"
        )

        print(
            f"  Failure: "
            f"{sample['failure_id']}"
        )

        print(
            f"  Reason: "
            f"{sample['failure_reason']}"
        )

        print(
            f"  Retry now: "
            f"{sample['retry_now_probability']}"
        )

        print(
            f"  Wait + retry: "
            f"{sample['wait_and_retry_probability']}"
        )

        print(
            f"  Reminder: "
            f"{sample['send_reminder_probability']}"
        )

        print(
            f"  Payment link: "
            f"{sample['payment_link_probability']}"
        )

        print(
            f"  Update method: "
            f"{sample['update_payment_method_probability']}"
        )

    print(
        "=============================================="
    )


if __name__ == "__main__":

    customers = load_csv(
        "customers.csv"
    )

    failures = load_csv(
        "payment_failures.csv"
    )

    ground_truth = generate_ground_truth(
        failures,
        customers,
    )

    print(
        f"Generated {len(ground_truth)} "
        f"ground-truth records"
    )

    output_path = save_ground_truth(
        ground_truth
    )

    print(
        f"Dataset saved to: {output_path}"
    )

    validate_ground_truth(
        ground_truth,
        failures,
    )