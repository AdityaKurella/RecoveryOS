import csv
import random
from pathlib import Path


random.seed(42)


# -------------------------------------------------
# SYNTHETIC BASELINE FAILURE DISTRIBUTION
# -------------------------------------------------
# These are simulation assumptions.
# They are NOT Razorpay production statistics.

BASE_FAILURE_WEIGHTS = {
    "INSUFFICIENT_FUNDS": 35,
    "BANK_DECLINED": 25,
    "NETWORK_ERROR": 15,
    "CARD_EXPIRED": 10,
    "AUTHENTICATION_FAILED": 8,
    "LIMIT_EXCEEDED": 7,
}


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
        return list(csv.DictReader(file))


def choose_failure_reason(customer, payment):
    """
    Generate a synthetic failure reason using:
    1. Baseline failure probabilities
    2. Customer behavior profile
    3. Payment amount

    RecoveryOS does NOT choose this.
    This is part of the synthetic environment.
    """

    weights = BASE_FAILURE_WEIGHTS.copy()

    profile = customer["behavior_profile"]
    amount = float(payment["amount"])

    # ---------------------------------------------
    # CUSTOMER PROFILE ADJUSTMENTS
    # ---------------------------------------------

    if profile == "friction_prone":
        weights["INSUFFICIENT_FUNDS"] += 12
        weights["BANK_DECLINED"] += 8

    elif profile == "low_engagement":
        weights["CARD_EXPIRED"] += 10
        weights["AUTHENTICATION_FAILED"] += 10

    elif profile == "reliable":
        weights["NETWORK_ERROR"] += 10
        weights["BANK_DECLINED"] -= 5

    elif profile == "high_value_loyal":
        weights["NETWORK_ERROR"] += 5
        weights["LIMIT_EXCEEDED"] += 5

    # ---------------------------------------------
    # PAYMENT AMOUNT ADJUSTMENTS
    # ---------------------------------------------

    if amount >= 5000:
        weights["LIMIT_EXCEEDED"] += 12
        weights["BANK_DECLINED"] += 5

    elif amount >= 3000:
        weights["LIMIT_EXCEEDED"] += 5

    # Ensure no weight becomes negative.
    for reason in weights:
        weights[reason] = max(
            weights[reason],
            0,
        )

    reasons = list(weights.keys())
    probability_weights = list(weights.values())

    failure_reason = random.choices(
        reasons,
        weights=probability_weights,
        k=1,
    )[0]

    return failure_reason


def get_failure_category(failure_reason):
    """
    Convert detailed failure reason into a broader
    recovery-relevant category.
    """

    categories = {
        "INSUFFICIENT_FUNDS": "CUSTOMER_FINANCIAL",
        "BANK_DECLINED": "ISSUER_DECLINE",
        "NETWORK_ERROR": "TECHNICAL",
        "CARD_EXPIRED": "PAYMENT_METHOD",
        "AUTHENTICATION_FAILED": "CUSTOMER_ACTION",
        "LIMIT_EXCEEDED": "PAYMENT_LIMIT",
    }

    return categories[failure_reason]


def generate_failures(
    payments,
    customers,
):
    failures = []

    customers_by_id = {
        customer["customer_id"]: customer
        for customer in customers
    }

    failure_counter = 1

    for payment in payments:

        # Only failed payments belong in this dataset.
        if payment["payment_status"] != "FAILED":
            continue

        customer = customers_by_id[
            payment["customer_id"]
        ]

        failure_reason = choose_failure_reason(
            customer,
            payment,
        )

        failure_category = get_failure_category(
            failure_reason
        )

        failure = {
            "failure_id": (
                f"FAIL_{failure_counter:06d}"
            ),
            "payment_id": payment["payment_id"],
            "subscription_id": (
                payment["subscription_id"]
            ),
            "customer_id": payment["customer_id"],
            "failure_reason": failure_reason,
            "failure_category": failure_category,
        }

        failures.append(failure)

        failure_counter += 1

    return failures


def save_failures(failures):
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "payment_failures.csv"
    )

    fieldnames = [
        "failure_id",
        "payment_id",
        "subscription_id",
        "customer_id",
        "failure_reason",
        "failure_category",
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
        writer.writerows(failures)

    return output_path


def validate_failures(
    failures,
    payments,
):
    print(
        "\n========== FAILURE VALIDATION =========="
    )

    failed_payments = [
        payment
        for payment in payments
        if payment["payment_status"] == "FAILED"
    ]

    print(
        f"Failed payments: {len(failed_payments)}"
    )

    print(
        f"Failure records generated: {len(failures)}"
    )

    # ---------------------------------------------
    # FAILURE ID VALIDATION
    # ---------------------------------------------

    failure_ids = [
        failure["failure_id"]
        for failure in failures
    ]

    duplicate_failure_ids = (
        len(failure_ids)
        - len(set(failure_ids))
    )

    print(
        f"Duplicate failure IDs: "
        f"{duplicate_failure_ids}"
    )

    # ---------------------------------------------
    # PAYMENT ID VALIDATION
    # ---------------------------------------------

    payment_ids = {
        payment["payment_id"]
        for payment in payments
    }

    invalid_payment_refs = [
        failure
        for failure in failures
        if failure["payment_id"]
        not in payment_ids
    ]

    print(
        f"Invalid payment references: "
        f"{len(invalid_payment_refs)}"
    )

    # ---------------------------------------------
    # ENSURE EACH FAILED PAYMENT HAS ONE FAILURE
    # ---------------------------------------------

    failed_payment_ids = {
        payment["payment_id"]
        for payment in failed_payments
    }

    failure_payment_ids = [
        failure["payment_id"]
        for failure in failures
    ]

    missing_failures = (
        failed_payment_ids
        - set(failure_payment_ids)
    )

    print(
        f"Failed payments without failure record: "
        f"{len(missing_failures)}"
    )

    duplicate_payment_failures = (
        len(failure_payment_ids)
        - len(set(failure_payment_ids))
    )

    print(
        f"Payments with duplicate failure records: "
        f"{duplicate_payment_failures}"
    )

    # ---------------------------------------------
    # ENSURE SUCCESSFUL PAYMENTS ARE NOT INCLUDED
    # ---------------------------------------------

    successful_payment_ids = {
        payment["payment_id"]
        for payment in payments
        if payment["payment_status"] == "SUCCESS"
    }

    success_with_failure = [
        failure
        for failure in failures
        if failure["payment_id"]
        in successful_payment_ids
    ]

    print(
        f"Successful payments with failure record: "
        f"{len(success_with_failure)}"
    )

    # ---------------------------------------------
    # VALID FAILURE REASONS
    # ---------------------------------------------

    valid_reasons = set(
        BASE_FAILURE_WEIGHTS.keys()
    )

    invalid_reasons = [
        failure
        for failure in failures
        if failure["failure_reason"]
        not in valid_reasons
    ]

    print(
        f"Invalid failure reasons: "
        f"{len(invalid_reasons)}"
    )

    # ---------------------------------------------
    # FAILURE DISTRIBUTION
    # ---------------------------------------------

    reason_counts = {}

    for failure in failures:

        reason = failure["failure_reason"]

        reason_counts[reason] = (
            reason_counts.get(reason, 0)
            + 1
        )

    print("\nFailure distribution:")

    for reason, count in sorted(
        reason_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    ):

        percentage = (
            count / len(failures) * 100
        )

        print(
            f"  {reason}: "
            f"{count} ({percentage:.2f}%)"
        )

    print(
        "========================================"
    )


if __name__ == "__main__":

    customers = load_csv(
        "customers.csv"
    )

    payments = load_csv(
        "payments.csv"
    )

    failures = generate_failures(
        payments,
        customers,
    )

    print(
        f"Generated {len(failures)} "
        f"failure records"
    )

    output_path = save_failures(
        failures
    )

    print(
        f"Dataset saved to: {output_path}"
    )

    validate_failures(
        failures,
        payments,
    )