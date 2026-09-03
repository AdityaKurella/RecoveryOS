import csv
from pathlib import Path


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


# ---------------------------------------------------------
# BASELINE STRATEGIES
# ---------------------------------------------------------

def always_retry(failure):
    return "RETRY_NOW"


def always_wait(failure):
    return "WAIT_AND_RETRY"


def always_remind(failure):
    return "SEND_REMINDER"


def failure_aware_rules(failure):
    reason = failure["failure_reason"]

    if reason == "NETWORK_ERROR":
        return "RETRY_NOW"

    if reason == "CARD_EXPIRED":
        return "UPDATE_PAYMENT_METHOD"

    if reason == "INSUFFICIENT_FUNDS":
        return "WAIT_AND_RETRY"

    if reason == "BANK_DECLINED":
        return "WAIT_AND_RETRY"

    if reason == "AUTHENTICATION_FAILED":
        return "UPDATE_PAYMENT_METHOD"

    if reason == "LIMIT_EXCEEDED":
        return "PAYMENT_LINK"

    return "NO_ACTION"


# ---------------------------------------------------------
# HIDDEN OUTCOME LOOKUP
# ---------------------------------------------------------

def get_probability(
    ground_truth,
    failure_id,
    action,
):
    for record in ground_truth:

        if record["failure_id"] == failure_id:

            field = (
                f"{action.lower()}_probability"
            )

            return float(record[field])

    raise ValueError(
        f"Ground truth not found: {failure_id}"
    )


# ---------------------------------------------------------
# STRATEGY EVALUATION
# ---------------------------------------------------------

def evaluate_strategy(
    strategy_name,
    strategy_function,
    failures,
    payments,
    ground_truth,
):
    payments_by_id = {
        payment["payment_id"]: payment
        for payment in payments
    }

    total_revenue_at_risk = 0.0
    expected_gross_recovery = 0.0
    intervention_cost = 0.0

    action_counts = {}

    for failure in failures:

        payment_id = failure["payment_id"]

        payment = payments_by_id[payment_id]

        amount = float(payment["amount"])

        total_revenue_at_risk += amount

        action = strategy_function(failure)

        action_counts[action] = (
            action_counts.get(action, 0) + 1
        )

        probability = get_probability(
            ground_truth,
            failure["failure_id"],
            action,
        )

        expected_gross_recovery += (
            amount * probability
        )

        intervention_cost += ACTION_COSTS[action]

    expected_net_recovery = (
        expected_gross_recovery
        - intervention_cost
    )

    recovery_rate = (
        expected_gross_recovery
        / total_revenue_at_risk
        if total_revenue_at_risk > 0
        else 0
    )

    return {
        "strategy": strategy_name,
        "failed_payments": len(failures),
        "revenue_at_risk": total_revenue_at_risk,
        "expected_gross_recovery": (
            expected_gross_recovery
        ),
        "intervention_cost": intervention_cost,
        "expected_net_recovery": (
            expected_net_recovery
        ),
        "recovery_rate": recovery_rate,
        "action_counts": action_counts,
    }


def print_results(results):

    print("\n========== BASELINE RESULTS ==========")

    for result in results:

        print(
            f"\nStrategy: "
            f"{result['strategy']}"
        )

        print(
            f"Failed payments: "
            f"{result['failed_payments']}"
        )

        print(
            f"Revenue at risk: "
            f"₹{result['revenue_at_risk']:,.2f}"
        )

        print(
            f"Expected gross recovery: "
            f"₹{result['expected_gross_recovery']:,.2f}"
        )

        print(
            f"Intervention cost: "
            f"₹{result['intervention_cost']:,.2f}"
        )

        print(
            f"Expected NET recovery: "
            f"₹{result['expected_net_recovery']:,.2f}"
        )

        print(
            f"Revenue recovery rate: "
            f"{result['recovery_rate']:.2%}"
        )

        print("Actions:")

        for action, count in (
            result["action_counts"].items()
        ):

            print(
                f"  {action}: {count}"
            )

    print(
        "\n======================================"
    )


if __name__ == "__main__":

    failures = load_csv(
        "payment_failures.csv"
    )

    payments = load_csv(
        "payments.csv"
    )

    ground_truth = load_csv(
        "recovery_ground_truth.csv"
    )

    strategies = [
        (
            "ALWAYS_RETRY",
            always_retry,
        ),
        (
            "ALWAYS_WAIT",
            always_wait,
        ),
        (
            "ALWAYS_REMIND",
            always_remind,
        ),
        (
            "FAILURE_AWARE_RULES",
            failure_aware_rules,
        ),
    ]

    results = []

    for strategy_name, strategy_function in strategies:

        result = evaluate_strategy(
            strategy_name,
            strategy_function,
            failures,
            payments,
            ground_truth,
        )

        results.append(result)

    print_results(results)