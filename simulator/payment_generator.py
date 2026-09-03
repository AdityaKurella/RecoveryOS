import csv
import random
from datetime import date, timedelta
from pathlib import Path


random.seed(42)


def load_customers():
    input_path = (
        Path(__file__).parent.parent
        / "data"
        / "customers.csv"
    )

    with open(
        input_path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def load_subscriptions():
    input_path = (
        Path(__file__).parent.parent
        / "data"
        / "subscriptions.csv"
    )

    with open(
        input_path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def add_months(start_date, months):
    """
    Our simulator uses a 30-day monthly billing cycle.
    """
    return start_date + timedelta(days=30 * months)


def generate_payment_history(
    customer,
    subscription,
    payment_counter,
):
    payments = []

    customer_id = customer["customer_id"]
    subscription_id = subscription["subscription_id"]

    account_age_days = int(
        customer["account_age_days"]
    )

    payment_success_rate = float(
        customer["payment_success_rate"]
    )

    monthly_amount = float(
        subscription["monthly_amount"]
    )

    start_date = date.fromisoformat(
        subscription["start_date"]
    )

    number_of_payments = max(
        1,
        account_age_days // 30,
    )

    for cycle in range(number_of_payments):

        payment_date = add_months(
            start_date,
            cycle,
        )

        if payment_date > date.today():
            break

        if random.random() < payment_success_rate:
            status = "SUCCESS"
        else:
            status = "FAILED"

        payment = {
            "payment_id": (
                f"PAY_{payment_counter[0]:06d}"
            ),
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "payment_date": payment_date.isoformat(),
            "amount": monthly_amount,
            "payment_status": status,
            "attempt_number": 1,
        }

        payments.append(payment)

        # Increment the GLOBAL counter.
        payment_counter[0] += 1

    return payments


def generate_all_payments(
    customers,
    subscriptions,
):
    payments = []

    customers_by_id = {
        customer["customer_id"]: customer
        for customer in customers
    }

    # Global counter shared by every subscription.
    payment_counter = [1]

    for subscription in subscriptions:

        customer_id = subscription["customer_id"]

        customer = customers_by_id[customer_id]

        subscription_payments = (
            generate_payment_history(
                customer,
                subscription,
                payment_counter,
            )
        )

        payments.extend(
            subscription_payments
        )

    return payments


def save_payments(payments):
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "payments.csv"
    )

    fieldnames = [
        "payment_id",
        "subscription_id",
        "customer_id",
        "payment_date",
        "amount",
        "payment_status",
        "attempt_number",
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
        writer.writerows(payments)

    return output_path


def validate_payments(
    payments,
    customers,
    subscriptions,
):
    print(
        "\n========== PAYMENT VALIDATION =========="
    )

    print(
        f"Customers loaded: {len(customers)}"
    )

    print(
        f"Subscriptions loaded: "
        f"{len(subscriptions)}"
    )

    print(
        f"Payments generated: "
        f"{len(payments)}"
    )

    # -----------------------------------------
    # PAYMENT ID CHECK
    # -----------------------------------------

    payment_ids = [
        payment["payment_id"]
        for payment in payments
    ]

    duplicate_payment_ids = (
        len(payment_ids)
        - len(set(payment_ids))
    )

    print(
        f"Duplicate payment IDs: "
        f"{duplicate_payment_ids}"
    )

    # -----------------------------------------
    # CUSTOMER RELATIONSHIP CHECK
    # -----------------------------------------

    customer_ids = {
        customer["customer_id"]
        for customer in customers
    }

    invalid_customer_payments = [
        payment
        for payment in payments
        if payment["customer_id"]
        not in customer_ids
    ]

    print(
        f"Payments with invalid customer IDs: "
        f"{len(invalid_customer_payments)}"
    )

    # -----------------------------------------
    # SUBSCRIPTION RELATIONSHIP CHECK
    # -----------------------------------------

    subscription_ids = {
        subscription["subscription_id"]
        for subscription in subscriptions
    }

    invalid_subscription_payments = [
        payment
        for payment in payments
        if payment["subscription_id"]
        not in subscription_ids
    ]

    print(
        f"Payments with invalid subscription IDs: "
        f"{len(invalid_subscription_payments)}"
    )

    # -----------------------------------------
    # AMOUNT CHECK
    # -----------------------------------------

    invalid_amounts = [
        payment
        for payment in payments
        if payment["amount"] <= 0
    ]

    print(
        f"Invalid payment amounts: "
        f"{len(invalid_amounts)}"
    )

    # -----------------------------------------
    # STATUS CHECK
    # -----------------------------------------

    valid_statuses = {
        "SUCCESS",
        "FAILED",
    }

    invalid_statuses = [
        payment
        for payment in payments
        if payment["payment_status"]
        not in valid_statuses
    ]

    print(
        f"Invalid payment statuses: "
        f"{len(invalid_statuses)}"
    )

    # -----------------------------------------
    # ATTEMPT NUMBER CHECK
    # -----------------------------------------

    invalid_attempts = [
        payment
        for payment in payments
        if payment["attempt_number"] != 1
    ]

    print(
        f"Invalid original attempt numbers: "
        f"{len(invalid_attempts)}"
    )

    # -----------------------------------------
    # SUBSCRIPTIONS WITH NO PAYMENTS
    # -----------------------------------------

    subscriptions_with_payments = {
        payment["subscription_id"]
        for payment in payments
    }

    subscriptions_without_payments = [
        subscription
        for subscription in subscriptions
        if subscription["subscription_id"]
        not in subscriptions_with_payments
    ]

    print(
        f"Subscriptions without payments: "
        f"{len(subscriptions_without_payments)}"
    )

    # -----------------------------------------
    # PAYMENT DISTRIBUTION
    # -----------------------------------------

    success_count = sum(
        1
        for payment in payments
        if payment["payment_status"]
        == "SUCCESS"
    )

    failed_count = sum(
        1
        for payment in payments
        if payment["payment_status"]
        == "FAILED"
    )

    print("\nPayment distribution:")

    print(
        f"  SUCCESS: {success_count}"
    )

    print(
        f"  FAILED: {failed_count}"
    )

    # -----------------------------------------
    # FAILURE RATE
    # -----------------------------------------

    if payments:

        failure_rate = (
            failed_count
            / len(payments)
        )

        print(
            f"\nOverall payment failure rate: "
            f"{failure_rate:.2%}"
        )

    print(
        "========================================"
    )


if __name__ == "__main__":

    customers = load_customers()

    subscriptions = load_subscriptions()

    payments = generate_all_payments(
        customers,
        subscriptions,
    )

    print(
        f"Generated {len(payments)} "
        f"payment events"
    )

    output_path = save_payments(
        payments
    )

    print(
        f"Dataset saved to: {output_path}"
    )

    validate_payments(
        payments,
        customers,
        subscriptions,
    )