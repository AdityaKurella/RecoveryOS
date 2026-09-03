import csv
import random
from pathlib import Path

random.seed(42)


PROFILE_CONFIG = {
    "reliable": {
        "payment_success_rate": 0.95,
        "engagement_score": 0.85,
        "recovery_rate": 0.80,
        "monthly_value_range": (500, 3000),
    },
    "normal": {
        "payment_success_rate": 0.85,
        "engagement_score": 0.60,
        "recovery_rate": 0.60,
        "monthly_value_range": (300, 2000),
    },
    "friction_prone": {
        "payment_success_rate": 0.70,
        "engagement_score": 0.45,
        "recovery_rate": 0.35,
        "monthly_value_range": (200, 1500),
    },
    "high_value_loyal": {
        "payment_success_rate": 0.93,
        "engagement_score": 0.90,
        "recovery_rate": 0.82,
        "monthly_value_range": (3000, 10000),
    },
    "low_engagement": {
        "payment_success_rate": 0.78,
        "engagement_score": 0.25,
        "recovery_rate": 0.30,
        "monthly_value_range": (200, 1200),
    },
}


def generate_customer(customer_id):
    profile = random.choice(list(PROFILE_CONFIG.keys()))
    config = PROFILE_CONFIG[profile]

    account_age_days = random.randint(30, 1000)

    total_payments = max(1, account_age_days // 30)

    successful_payments = 0
    failed_payments = 0

    for _ in range(total_payments):
        if random.random() < config["payment_success_rate"]:
            successful_payments += 1
        else:
            failed_payments += 1

    payment_success_rate = successful_payments / total_payments

    min_value, max_value = config["monthly_value_range"]

    monthly_subscription_value = random.randint(
        min_value,
        max_value
    )

    customer = {
        "customer_id": customer_id,
        "account_age_days": account_age_days,
        "successful_payments": successful_payments,
        "failed_payments": failed_payments,
        "total_payments": total_payments,
        "payment_success_rate": round(payment_success_rate, 4),
        "monthly_subscription_value": monthly_subscription_value,
        "historical_recovery_rate": config["recovery_rate"],
        "engagement_score": config["engagement_score"],
        "behavior_profile": profile,
    }

    return customer


def generate_customers(count=1000):
    customers = []

    for i in range(1, count + 1):
        customer_id = f"CUST_{i:04d}"
        customers.append(generate_customer(customer_id))

    return customers


def save_customers(customers):
    output_path = Path(__file__).parent.parent / "data" / "customers.csv"

    fieldnames = customers[0].keys()

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(customers)

    return output_path


def validate_customers(customers):
    print("\n========== VALIDATION REPORT ==========")

    print(f"Customer count: {len(customers)}")

    customer_ids = [customer["customer_id"] for customer in customers]

    duplicate_ids = len(customer_ids) - len(set(customer_ids))

    print(f"Duplicate IDs: {duplicate_ids}")

    required_fields = {
        "customer_id",
        "account_age_days",
        "successful_payments",
        "failed_payments",
        "total_payments",
        "payment_success_rate",
        "monthly_subscription_value",
        "historical_recovery_rate",
        "engagement_score",
        "behavior_profile",
    }

    missing_fields = []

    for customer in customers:
        if not required_fields.issubset(customer.keys()):
            missing_fields.append(customer["customer_id"])

    print(f"Customers with missing fields: {len(missing_fields)}")

    invalid_customers = []

    for customer in customers:
        if (
            customer["account_age_days"] < 30
            or customer["successful_payments"] < 0
            or customer["failed_payments"] < 0
            or customer["total_payments"] <= 0
            or customer["successful_payments"]
            + customer["failed_payments"]
            != customer["total_payments"]
            or not 0 <= customer["payment_success_rate"] <= 1
            or customer["monthly_subscription_value"] <= 0
            or not 0 <= customer["historical_recovery_rate"] <= 1
            or not 0 <= customer["engagement_score"] <= 1
        ):
            invalid_customers.append(customer["customer_id"])

    print(f"Invalid customers: {len(invalid_customers)}")

    profile_counts = {}

    for customer in customers:
        profile = customer["behavior_profile"]
        profile_counts[profile] = profile_counts.get(profile, 0) + 1

    print("\nProfile distribution:")

    for profile, count in profile_counts.items():
        print(f"  {profile}: {count}")

    avg_age = sum(
        customer["account_age_days"]
        for customer in customers
    ) / len(customers)

    avg_success_rate = sum(
        customer["payment_success_rate"]
        for customer in customers
    ) / len(customers)

    avg_monthly_value = sum(
        customer["monthly_subscription_value"]
        for customer in customers
    ) / len(customers)

    print(f"\nAverage account age: {avg_age:.2f} days")
    print(f"Average payment success rate: {avg_success_rate:.2%}")
    print(f"Average monthly subscription value: ₹{avg_monthly_value:.2f}")

    print("=======================================")


if __name__ == "__main__":
    customers = generate_customers(1000)

    print(f"Generated {len(customers)} customers")

    output_path = save_customers(customers)

    print(f"Dataset saved to: {output_path}")

    validate_customers(customers)