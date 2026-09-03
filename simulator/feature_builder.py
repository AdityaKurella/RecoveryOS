import csv
from pathlib import Path


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


def calculate_failure_ratio(
    failed_payments,
    total_payments,
):
    total_payments = max(
        int(total_payments),
        1,
    )

    return failed_payments / total_payments


def calculate_payment_reliability(
    successful_payments,
    total_payments,
):
    total_payments = max(
        int(total_payments),
        1,
    )

    return successful_payments / total_payments


def build_features(
    customers,
    subscriptions,
    payments,
    failures,
):
    customers_by_id = {
        customer["customer_id"]: customer
        for customer in customers
    }

    subscriptions_by_id = {
        subscription["subscription_id"]: subscription
        for subscription in subscriptions
    }

    payments_by_id = {
        payment["payment_id"]: payment
        for payment in payments
    }

    feature_rows = []

    for failure in failures:

        payment_id = failure["payment_id"]
        customer_id = failure["customer_id"]
        subscription_id = failure["subscription_id"]

        customer = customers_by_id[customer_id]

        subscription = subscriptions_by_id[
            subscription_id
        ]

        payment = payments_by_id[payment_id]

        successful_payments = int(
            customer["successful_payments"]
        )

        failed_payments = int(
            customer["failed_payments"]
        )

        total_payments = int(
            customer["total_payments"]
        )

        failure_ratio = calculate_failure_ratio(
            failed_payments,
            total_payments,
        )

        payment_reliability = (
            calculate_payment_reliability(
                successful_payments,
                total_payments,
            )
        )

        monthly_amount = float(
            subscription["monthly_amount"]
        )

        payment_amount = float(
            payment["amount"]
        )

        feature_row = {
            # ---------------------------------
            # IDENTIFIERS
            # ---------------------------------

            "failure_id": failure["failure_id"],
            "payment_id": payment_id,
            "customer_id": customer_id,
            "subscription_id": subscription_id,

            # ---------------------------------
            # PAYMENT FEATURES
            # ---------------------------------

            "amount": payment_amount,
            "payment_date": payment["payment_date"],

            # ---------------------------------
            # FAILURE FEATURES
            # ---------------------------------

            "failure_reason": (
                failure["failure_reason"]
            ),
            "failure_category": (
                failure["failure_category"]
            ),

            # ---------------------------------
            # CUSTOMER FEATURES
            # ---------------------------------

            "account_age_days": int(
                customer["account_age_days"]
            ),

            "successful_payments": (
                successful_payments
            ),

            "failed_payments": (
                failed_payments
            ),

            "total_payments": (
                total_payments
            ),

            "payment_success_rate": float(
                customer["payment_success_rate"]
            ),

            "historical_recovery_rate": float(
                customer[
                    "historical_recovery_rate"
                ]
            ),

            "engagement_score": float(
                customer["engagement_score"]
            ),

            "behavior_profile": (
                customer["behavior_profile"]
            ),

            # ---------------------------------
            # DERIVED FEATURES
            # ---------------------------------

            "failure_ratio": round(
                failure_ratio,
                4,
            ),

            "payment_reliability": round(
                payment_reliability,
                4,
            ),

            # ---------------------------------
            # SUBSCRIPTION FEATURES
            # ---------------------------------

            "plan": subscription["plan"],

            "monthly_subscription_value": (
                monthly_amount
            ),

            "billing_interval": (
                subscription["billing_interval"]
            ),
        }

        feature_rows.append(
            feature_row
        )

    return feature_rows


def save_features(feature_rows):
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "decision_features.csv"
    )

    fieldnames = [
        "failure_id",
        "payment_id",
        "customer_id",
        "subscription_id",
        "amount",
        "payment_date",
        "failure_reason",
        "failure_category",
        "account_age_days",
        "successful_payments",
        "failed_payments",
        "total_payments",
        "payment_success_rate",
        "historical_recovery_rate",
        "engagement_score",
        "behavior_profile",
        "failure_ratio",
        "payment_reliability",
        "plan",
        "monthly_subscription_value",
        "billing_interval",
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
            feature_rows
        )

    return output_path


def validate_features(
    feature_rows,
    failures,
):
    print(
        "\n========== FEATURE VALIDATION =========="
    )

    print(
        f"Failure records: {len(failures)}"
    )

    print(
        f"Feature rows: {len(feature_rows)}"
    )

    # -----------------------------------------
    # ROW COVERAGE
    # -----------------------------------------

    if len(feature_rows) == len(failures):
        print(
            "Failure coverage: 100.00%"
        )

    else:
        coverage = (
            len(feature_rows)
            / len(failures)
            * 100
        )

        print(
            f"Failure coverage: "
            f"{coverage:.2f}%"
        )

    # -----------------------------------------
    # DUPLICATE FAILURE IDs
    # -----------------------------------------

    failure_ids = [
        row["failure_id"]
        for row in feature_rows
    ]

    duplicate_failure_ids = (
        len(failure_ids)
        - len(set(failure_ids))
    )

    print(
        f"Duplicate failure IDs: "
        f"{duplicate_failure_ids}"
    )

    # -----------------------------------------
    # MISSING VALUES
    # -----------------------------------------

    required_fields = [
        "failure_id",
        "payment_id",
        "customer_id",
        "subscription_id",
        "amount",
        "failure_reason",
        "failure_category",
        "account_age_days",
        "payment_success_rate",
        "historical_recovery_rate",
        "engagement_score",
        "behavior_profile",
        "failure_ratio",
        "payment_reliability",
        "plan",
        "monthly_subscription_value",
    ]

    missing_values = 0

    for row in feature_rows:

        for field in required_fields:

            if (
                field not in row
                or row[field] == ""
            ):
                missing_values += 1

    print(
        f"Missing required values: "
        f"{missing_values}"
    )

    # -----------------------------------------
    # INVALID AMOUNTS
    # -----------------------------------------

    invalid_amounts = [
        row
        for row in feature_rows
        if float(row["amount"]) <= 0
    ]

    print(
        f"Invalid payment amounts: "
        f"{len(invalid_amounts)}"
    )

    # -----------------------------------------
    # PROBABILITY RANGE CHECK
    # -----------------------------------------

    invalid_probabilities = []

    probability_fields = [
        "payment_success_rate",
        "historical_recovery_rate",
        "engagement_score",
        "failure_ratio",
        "payment_reliability",
    ]

    for row in feature_rows:

        for field in probability_fields:

            value = float(row[field])

            if not 0 <= value <= 1:
                invalid_probabilities.append(
                    row["failure_id"]
                )

    print(
        f"Invalid probability/score values: "
        f"{len(invalid_probabilities)}"
    )

    # -----------------------------------------
    # SAMPLE
    # -----------------------------------------

    if feature_rows:

        print(
            "\nSample decision feature row:"
        )

        sample = feature_rows[0]

        for key, value in sample.items():

            print(
                f"  {key}: {value}"
            )

    print(
        "========================================"
    )


if __name__ == "__main__":

    customers = load_csv(
        "customers.csv"
    )

    subscriptions = load_csv(
        "subscriptions.csv"
    )

    payments = load_csv(
        "payments.csv"
    )

    failures = load_csv(
        "payment_failures.csv"
    )

    feature_rows = build_features(
        customers,
        subscriptions,
        payments,
        failures,
    )

    print(
        f"Generated {len(feature_rows)} "
        f"decision feature rows"
    )

    output_path = save_features(
        feature_rows
    )

    print(
        f"Dataset saved to: {output_path}"
    )

    validate_features(
        feature_rows,
        failures,
    )