import csv
import random
from datetime import date, timedelta
from pathlib import Path


random.seed(42)


PLAN_CONFIG = {
    "starter": {
        "multiplier": (0.6, 0.9),
        "billing_interval": "monthly",
    },
    "growth": {
        "multiplier": (0.9, 1.3),
        "billing_interval": "monthly",
    },
    "pro": {
        "multiplier": (1.2, 1.8),
        "billing_interval": "monthly",
    },
}


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


def generate_subscription(customer, subscription_number):
    customer_id = customer["customer_id"]

    profile = customer["behavior_profile"]
    base_value = float(
        customer["monthly_subscription_value"]
    )

    # High-value loyal customers are more likely
    # to receive a Pro plan.
    if profile == "high_value_loyal":
        plan = random.choices(
            ["growth", "pro"],
            weights=[30, 70],
            k=1,
        )[0]

    # Low-engagement customers are more likely
    # to receive a Starter plan.
    elif profile == "low_engagement":
        plan = random.choices(
            ["starter", "growth"],
            weights=[70, 30],
            k=1,
        )[0]

    else:
        plan = random.choice(
            list(PLAN_CONFIG.keys())
        )

    min_multiplier, max_multiplier = PLAN_CONFIG[
        plan
    ]["multiplier"]

    multiplier = random.uniform(
        min_multiplier,
        max_multiplier,
    )

    monthly_amount = round(
        base_value * multiplier,
        2,
    )

    # Keep the simulated subscription amount
    # within a reasonable range.
    monthly_amount = max(
        200,
        min(monthly_amount, 15000),
    )

    # -----------------------------------------
    # BILLING DATE LOGIC
    # -----------------------------------------

    account_age_days = int(
        customer["account_age_days"]
    )

    today = date.today()

    # Subscription started approximately
    # account_age_days ago.
    start_date = today - timedelta(
        days=account_age_days
    )

    # Determine where the customer currently is
    # inside their monthly billing cycle.
    days_since_start = account_age_days % 30

    # Calculate the next monthly billing date.
    next_billing_date = today + timedelta(
        days=(30 - days_since_start)
    )

    # -----------------------------------------
    # SUBSCRIPTION RECORD
    # -----------------------------------------

    subscription = {
        "subscription_id": (
            f"SUB_{subscription_number:04d}"
        ),
        "customer_id": customer_id,
        "plan": plan,
        "monthly_amount": monthly_amount,
        "billing_interval": PLAN_CONFIG[plan][
            "billing_interval"
        ],
        "start_date": start_date.isoformat(),
        "next_billing_date": (
            next_billing_date.isoformat()
        ),
        "status": "active",
    }

    return subscription


def generate_subscriptions(customers):
    subscriptions = []

    for i, customer in enumerate(
        customers,
        start=1,
    ):
        subscription = generate_subscription(
            customer,
            i,
        )

        subscriptions.append(subscription)

    return subscriptions


def save_subscriptions(subscriptions):
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "subscriptions.csv"
    )

    fieldnames = subscriptions[0].keys()

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
        writer.writerows(subscriptions)

    return output_path


def validate_subscriptions(
    subscriptions,
    customers,
):
    print(
        "\n========== SUBSCRIPTION VALIDATION =========="
    )

    # -----------------------------------------
    # CUSTOMER / SUBSCRIPTION COUNT
    # -----------------------------------------

    print(
        f"Customers loaded: {len(customers)}"
    )

    print(
        f"Subscriptions generated: "
        f"{len(subscriptions)}"
    )

    # -----------------------------------------
    # DUPLICATE SUBSCRIPTION IDS
    # -----------------------------------------

    subscription_ids = [
        subscription["subscription_id"]
        for subscription in subscriptions
    ]

    duplicate_ids = (
        len(subscription_ids)
        - len(set(subscription_ids))
    )

    print(
        f"Duplicate subscription IDs: "
        f"{duplicate_ids}"
    )

    # -----------------------------------------
    # CUSTOMER RELATIONSHIPS
    # -----------------------------------------

    customer_ids = {
        customer["customer_id"]
        for customer in customers
    }

    orphan_subscriptions = [
        subscription
        for subscription in subscriptions
        if subscription["customer_id"]
        not in customer_ids
    ]

    print(
        f"Orphan subscriptions: "
        f"{len(orphan_subscriptions)}"
    )

    # -----------------------------------------
    # MONTHLY AMOUNT VALIDATION
    # -----------------------------------------

    invalid_amounts = [
        subscription
        for subscription in subscriptions
        if subscription["monthly_amount"] <= 0
    ]

    print(
        f"Invalid monthly amounts: "
        f"{len(invalid_amounts)}"
    )

    # -----------------------------------------
    # PLAN VALIDATION
    # -----------------------------------------

    valid_plans = set(
        PLAN_CONFIG.keys()
    )

    invalid_plans = [
        subscription
        for subscription in subscriptions
        if subscription["plan"]
        not in valid_plans
    ]

    print(
        f"Invalid plans: "
        f"{len(invalid_plans)}"
    )

    # -----------------------------------------
    # PLAN DISTRIBUTION
    # -----------------------------------------

    plan_counts = {}

    for subscription in subscriptions:

        plan = subscription["plan"]

        plan_counts[plan] = (
            plan_counts.get(plan, 0)
            + 1
        )

    print("\nPlan distribution:")

    for plan, count in plan_counts.items():

        print(
            f"  {plan}: {count}"
        )

    # -----------------------------------------
    # AVERAGE SUBSCRIPTION VALUE
    # -----------------------------------------

    average_amount = sum(
        subscription["monthly_amount"]
        for subscription in subscriptions
    ) / len(subscriptions)

    print(
        f"\nAverage monthly subscription value: "
        f"₹{average_amount:.2f}"
    )

    print(
        "============================================="
    )


# ---------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------

if __name__ == "__main__":

    customers = load_customers()

    subscriptions = generate_subscriptions(
        customers
    )

    print(
        f"Generated {len(subscriptions)} "
        f"subscriptions"
    )

    output_path = save_subscriptions(
        subscriptions
    )

    print(
        f"Dataset saved to: {output_path}"
    )

    validate_subscriptions(
        subscriptions,
        customers,
    )