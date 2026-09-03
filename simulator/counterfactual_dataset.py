import csv
import math
import random
from pathlib import Path


# ============================================================
# M10A — COUNTERFACTUAL RECOVERY ENVIRONMENT
# ============================================================

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

# Reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)


# ============================================================
# PATHS
# ============================================================

# File is:
# simulator/counterfactual/counterfactual_dataset.py
#
# Therefore:
# parent.parent = project root
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# CSV HELPERS
# ============================================================

def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(filename, rows):
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        raise ValueError("Cannot save empty dataset.")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
        )

        writer.writeheader()
        writer.writerows(rows)

    return path


# ============================================================
# SAFE CONVERSION
# ============================================================

def to_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def to_int(value, default=0):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def clamp(value, low=0.01, high=0.99):
    return max(low, min(high, value))


# ============================================================
# SIGMOID
# ============================================================

def sigmoid(x):
    """
    Converts latent score into probability.
    """
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


# ============================================================
# PROFILE EFFECTS
# ============================================================

PROFILE_EFFECTS = {
    "reliable": {
        "base": 0.18,
        "retry": 0.12,
        "wait": 0.08,
        "reminder": 0.05,
        "link": 0.08,
        "update": 0.06,
    },

    "normal": {
        "base": 0.00,
        "retry": 0.02,
        "wait": 0.04,
        "reminder": 0.03,
        "link": 0.04,
        "update": 0.03,
    },

    "friction_prone": {
        "base": -0.16,
        "retry": -0.08,
        "wait": 0.02,
        "reminder": 0.05,
        "link": 0.08,
        "update": 0.11,
    },

    "high_value_loyal": {
        "base": 0.20,
        "retry": 0.08,
        "wait": 0.10,
        "reminder": 0.07,
        "link": 0.12,
        "update": 0.10,
    },

    "low_engagement": {
        "base": -0.20,
        "retry": -0.07,
        "wait": -0.03,
        "reminder": -0.04,
        "link": 0.03,
        "update": 0.02,
    },
}


# ============================================================
# FAILURE-REASON EFFECTS
# ============================================================

# These are NOT deterministic action mappings.
#
# The same failure reason can have different optimal actions
# depending on customer context.

FAILURE_EFFECTS = {

    "NETWORK_ERROR": {
        "base": 0.05,
        "RETRY_NOW": 0.22,
        "WAIT_AND_RETRY": 0.18,
        "SEND_REMINDER": -0.04,
        "PAYMENT_LINK": 0.03,
        "UPDATE_PAYMENT_METHOD": -0.06,
    },

    "CARD_EXPIRED": {
        "base": -0.02,
        "RETRY_NOW": -0.16,
        "WAIT_AND_RETRY": -0.12,
        "SEND_REMINDER": 0.03,
        "PAYMENT_LINK": 0.09,
        "UPDATE_PAYMENT_METHOD": 0.30,
    },

    "INSUFFICIENT_FUNDS": {
        "base": -0.04,
        "RETRY_NOW": -0.10,
        "WAIT_AND_RETRY": 0.16,
        "SEND_REMINDER": 0.11,
        "PAYMENT_LINK": 0.12,
        "UPDATE_PAYMENT_METHOD": 0.04,
    },

    "BANK_DECLINED": {
        "base": -0.05,
        "RETRY_NOW": -0.07,
        "WAIT_AND_RETRY": 0.13,
        "SEND_REMINDER": 0.07,
        "PAYMENT_LINK": 0.10,
        "UPDATE_PAYMENT_METHOD": 0.06,
    },

    "AUTHENTICATION_FAILED": {
        "base": -0.03,
        "RETRY_NOW": -0.11,
        "WAIT_AND_RETRY": -0.08,
        "SEND_REMINDER": 0.05,
        "PAYMENT_LINK": 0.11,
        "UPDATE_PAYMENT_METHOD": 0.23,
    },

    "LIMIT_EXCEEDED": {
        "base": -0.02,
        "RETRY_NOW": -0.14,
        "WAIT_AND_RETRY": -0.08,
        "SEND_REMINDER": 0.06,
        "PAYMENT_LINK": 0.22,
        "UPDATE_PAYMENT_METHOD": 0.08,
    },
}


# ============================================================
# ACTION × CONTEXT INTERACTIONS
# ============================================================

def action_context_effect(
    action,
    payment_success_rate,
    historical_recovery_rate,
    engagement_score,
    amount,
    account_age_days,
):
    """
    Context-dependent action effects.

    Important:
    The effect is not simply:
        failure_reason -> fixed action

    Instead, customer/payment context changes which action
    becomes economically attractive.
    """

    effect = 0.0

    # --------------------------------------------------------
    # Payment reliability
    # --------------------------------------------------------

    if action == "RETRY_NOW":
        effect += (payment_success_rate - 0.50) * 0.90

    elif action == "WAIT_AND_RETRY":
        effect += (payment_success_rate - 0.50) * 0.55

    elif action == "SEND_REMINDER":
        effect += (payment_success_rate - 0.50) * 0.25

    elif action == "PAYMENT_LINK":
        effect += (payment_success_rate - 0.50) * 0.40

    elif action == "UPDATE_PAYMENT_METHOD":
        effect += (payment_success_rate - 0.50) * 0.30

    # --------------------------------------------------------
    # Historical recovery behavior
    # --------------------------------------------------------

    recovery_delta = historical_recovery_rate - 0.50

    if action == "RETRY_NOW":
        effect += recovery_delta * 0.55

    elif action == "WAIT_AND_RETRY":
        effect += recovery_delta * 0.45

    elif action == "SEND_REMINDER":
        effect += recovery_delta * 0.35

    elif action == "PAYMENT_LINK":
        effect += recovery_delta * 0.65

    elif action == "UPDATE_PAYMENT_METHOD":
        effect += recovery_delta * 0.60

    # --------------------------------------------------------
    # Engagement
    # --------------------------------------------------------

    engagement_delta = engagement_score - 0.50

    if action == "SEND_REMINDER":
        effect += engagement_delta * 0.80

    elif action == "PAYMENT_LINK":
        effect += engagement_delta * 0.60

    elif action == "UPDATE_PAYMENT_METHOD":
        effect += engagement_delta * 0.45

    elif action == "RETRY_NOW":
        effect += engagement_delta * 0.25

    elif action == "WAIT_AND_RETRY":
        effect += engagement_delta * 0.35

    # --------------------------------------------------------
    # Amount/value interaction
    # --------------------------------------------------------

    # Normalize amount roughly around typical subscription values.
    amount_factor = math.log1p(max(amount, 0)) / 10.0

    if action == "PAYMENT_LINK":
        effect += amount_factor * 0.055

    elif action == "UPDATE_PAYMENT_METHOD":
        effect += amount_factor * 0.045

    elif action == "SEND_REMINDER":
        effect += amount_factor * 0.020

    # --------------------------------------------------------
    # Account age / relationship strength
    # --------------------------------------------------------

    age_factor = min(account_age_days / 1000.0, 1.0)

    if action == "RETRY_NOW":
        effect += age_factor * 0.035

    elif action == "WAIT_AND_RETRY":
        effect += age_factor * 0.045

    elif action == "PAYMENT_LINK":
        effect += age_factor * 0.055

    elif action == "UPDATE_PAYMENT_METHOD":
        effect += age_factor * 0.045

    # --------------------------------------------------------
    # Nonlinear interactions
    # --------------------------------------------------------

    if action == "PAYMENT_LINK":
        effect += (
            max(0.0, engagement_score - 0.55)
            * max(0.0, historical_recovery_rate - 0.55)
            * 0.90
        )

    if action == "UPDATE_PAYMENT_METHOD":
        effect += (
            max(0.0, engagement_score - 0.50)
            * max(0.0, payment_success_rate - 0.75)
            * 0.85
        )

    if action == "RETRY_NOW":
        effect += (
            max(0.0, payment_success_rate - 0.80)
            * max(0.0, historical_recovery_rate - 0.60)
            * 0.75
        )

    if action == "WAIT_AND_RETRY":
        effect += (
            max(0.0, 0.75 - payment_success_rate)
            * max(0.0, historical_recovery_rate - 0.45)
            * 0.60
        )

    return effect


# ============================================================
# HIDDEN ENVIRONMENT NOISE
# ============================================================

def hidden_noise():
    """
    Hidden environment factor.

    This represents information unavailable to the policy model,
    such as temporary issuer conditions, user timing, device
    context, or other latent factors.

    It prevents the benchmark from becoming perfectly
    deterministic.
    """

    return random.gauss(0.0, 0.10)


# ============================================================
# TRUE RECOVERY PROBABILITY
# ============================================================

def calculate_true_probability(
    failure_reason,
    behavior_profile,
    payment_success_rate,
    historical_recovery_rate,
    engagement_score,
    amount,
    account_age_days,
    action,
):
    """
    Hidden data-generating process.

    This function represents the environment's true probability
    of recovery for each possible intervention.

    The model in M10B does NOT see this function.
    """

    failure_config = FAILURE_EFFECTS.get(
        failure_reason,
        {
            "base": 0.0,
            "RETRY_NOW": 0.0,
            "WAIT_AND_RETRY": 0.0,
            "SEND_REMINDER": 0.0,
            "PAYMENT_LINK": 0.0,
            "UPDATE_PAYMENT_METHOD": 0.0,
        },
    )

    profile_config = PROFILE_EFFECTS.get(
        behavior_profile,
        PROFILE_EFFECTS["normal"],
    )

    action_key = action.lower().replace("_", "")

    if action == "RETRY_NOW":
        profile_action_effect = profile_config["retry"]
    elif action == "WAIT_AND_RETRY":
        profile_action_effect = profile_config["wait"]
    elif action == "SEND_REMINDER":
        profile_action_effect = profile_config["reminder"]
    elif action == "PAYMENT_LINK":
        profile_action_effect = profile_config["link"]
    else:
        profile_action_effect = profile_config["update"]

    score = 0.0

    # General customer recovery tendency
    score += profile_config["base"]

    # Failure reason baseline
    score += failure_config["base"]

    # Action-specific failure effect
    score += failure_config.get(action, 0.0)

    # Profile × action interaction
    score += profile_action_effect

    # Context × action interaction
    score += action_context_effect(
        action=action,
        payment_success_rate=payment_success_rate,
        historical_recovery_rate=historical_recovery_rate,
        engagement_score=engagement_score,
        amount=amount,
        account_age_days=account_age_days,
    )

    # --------------------------------------------------------
    # Additional observable relationships
    # --------------------------------------------------------

    score += (payment_success_rate - 0.80) * 0.70
    score += (historical_recovery_rate - 0.50) * 0.55
    score += (engagement_score - 0.50) * 0.45

    # High-value customers can be more recoverable,
    # but high amount itself should not guarantee recovery.
    score += min(amount / 10000.0, 1.0) * 0.035

    # Account relationship strength
    score += min(account_age_days / 1500.0, 1.0) * 0.04

    # Hidden randomness
    score += hidden_noise()

    # Convert latent score into probability.
    probability = sigmoid(score * 2.1)

    return clamp(probability, 0.02, 0.95)


# ============================================================
# BUILD COUNTERFACTUAL DATASET
# ============================================================

def build_counterfactual_dataset(
    ground_truth,
    customers,
    payments,
):
    print("\n" + "=" * 70)
    print("M10A — BUILDING COUNTERFACTUAL RECOVERY DATASET")
    print("=" * 70)

    customer_map = {
        row["customer_id"]: row
        for row in customers
    }

    payment_map = {
        row["payment_id"]: row
        for row in payments
    }

    rows = []

    missing_customers = 0
    missing_payments = 0

    for truth in ground_truth:

        customer_id = truth["customer_id"]
        payment_id = truth.get("payment_id", "")

        customer = customer_map.get(customer_id)

        if customer is None:
            missing_customers += 1
            continue

        payment = payment_map.get(payment_id)

        # Payment lookup is optional because the ground-truth file
        # may already contain the required payment fields.
        if payment is None and payment_id:
            missing_payments += 1

        amount = to_float(
            truth.get(
                "amount",
                payment.get("amount", 0) if payment else 0
            )
        )

        failure_reason = truth.get(
            "failure_reason",
            payment.get("failure_reason", "UNKNOWN")
            if payment else "UNKNOWN"
        )

        account_age_days = to_int(
            customer.get("account_age_days", 0)
        )

        successful_payments = to_int(
            customer.get("successful_payments", 0)
        )

        failed_payments = to_int(
            customer.get("failed_payments", 0)
        )

        total_payments = to_int(
            customer.get(
                "total_payments",
                successful_payments + failed_payments
            )
        )

        payment_success_rate = to_float(
            customer.get("payment_success_rate", 0.5)
        )

        historical_recovery_rate = to_float(
            customer.get("historical_recovery_rate", 0.5)
        )

        engagement_score = to_float(
            customer.get("engagement_score", 0.5)
        )

        behavior_profile = customer.get(
            "behavior_profile",
            "normal"
        )

        # ----------------------------------------------------
        # Generate all possible counterfactual actions.
        # ----------------------------------------------------

        for action in ACTIONS:

            probability = calculate_true_probability(
                failure_reason=failure_reason,
                behavior_profile=behavior_profile,
                payment_success_rate=payment_success_rate,
                historical_recovery_rate=historical_recovery_rate,
                engagement_score=engagement_score,
                amount=amount,
                account_age_days=account_age_days,
                action=action,
            )

            action_cost = ACTION_COSTS[action]

            expected_gross_recovery = amount * probability

            expected_net_value = (
                expected_gross_recovery - action_cost
            )

            counterfactual_id = (
                f"{truth['failure_id']}__{action}"
            )

            rows.append({
                "counterfactual_id": counterfactual_id,

                "failure_id": truth["failure_id"],

                "payment_id": payment_id,

                "subscription_id": truth.get(
                    "subscription_id",
                    ""
                ),

                "customer_id": customer_id,

                "amount": f"{amount:.2f}",

                "failure_reason": failure_reason,

                "account_age_days": account_age_days,

                "successful_payments": successful_payments,

                "failed_payments": failed_payments,

                "total_payments": total_payments,

                "payment_success_rate": (
                    f"{payment_success_rate:.6f}"
                ),

                "historical_recovery_rate": (
                    f"{historical_recovery_rate:.6f}"
                ),

                "engagement_score": (
                    f"{engagement_score:.6f}"
                ),

                "behavior_profile": behavior_profile,

                "candidate_action": action,

                "action_cost": f"{action_cost:.2f}",

                "true_recovery_probability": (
                    f"{probability:.6f}"
                ),

                "expected_gross_recovery": (
                    f"{expected_gross_recovery:.2f}"
                ),

                "expected_net_value": (
                    f"{expected_net_value:.2f}"
                ),
            })

    # ========================================================
    # SAVE
    # ========================================================

    output_path = save_csv(
        "counterfactual_training.csv",
        rows
    )

    print(f"\nGenerated rows: {len(rows):,}")
    print(f"Expected rows:  {len(ground_truth) * len(ACTIONS):,}")

    print(f"\nMissing customers: {missing_customers}")
    print(f"Missing payments:  {missing_payments}")

    print(f"\nSaved:")
    print(output_path)

    return rows


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(rows, ground_truth):

    print("\n" + "=" * 70)
    print("M10A — VALIDATION")
    print("=" * 70)

    expected_rows = len(ground_truth) * len(ACTIONS)

    # --------------------------------------------------------
    # Row count
    # --------------------------------------------------------

    row_count_pass = len(rows) == expected_rows

    print(
        f"Row count: "
        f"{'PASS' if row_count_pass else 'FAIL'} "
        f"({len(rows):,}/{expected_rows:,})"
    )

    # --------------------------------------------------------
    # Duplicate IDs
    # --------------------------------------------------------

    ids = [
        row["counterfactual_id"]
        for row in rows
    ]

    duplicate_ids = len(ids) - len(set(ids))

    print(
        f"Duplicate counterfactual IDs: "
        f"{'PASS' if duplicate_ids == 0 else 'FAIL'} "
        f"({duplicate_ids})"
    )

    # --------------------------------------------------------
    # Action coverage
    # --------------------------------------------------------

    action_counts = {
        action: 0
        for action in ACTIONS
    }

    for row in rows:
        action = row["candidate_action"]

        if action in action_counts:
            action_counts[action] += 1

    action_coverage_pass = all(
        action_counts[action] == len(ground_truth)
        for action in ACTIONS
    )

    print(
        f"Action coverage: "
        f"{'PASS' if action_coverage_pass else 'FAIL'}"
    )

    for action, count in action_counts.items():
        print(f"  {action:<25} {count:,}")

    # --------------------------------------------------------
    # Probability validation
    # --------------------------------------------------------

    invalid_probabilities = 0

    for row in rows:
        probability = to_float(
            row["true_recovery_probability"]
        )

        if not 0.0 < probability < 1.0:
            invalid_probabilities += 1

    print(
        f"Probability range: "
        f"{'PASS' if invalid_probabilities == 0 else 'FAIL'} "
        f"({invalid_probabilities} invalid)"
    )

    # --------------------------------------------------------
    # Amount validation
    # --------------------------------------------------------

    invalid_amounts = 0

    for row in rows:
        if to_float(row["amount"]) <= 0:
            invalid_amounts += 1

    print(
        f"Amount validation: "
        f"{'PASS' if invalid_amounts == 0 else 'FAIL'} "
        f"({invalid_amounts} invalid)"
    )

    # --------------------------------------------------------
    # Net value validation
    # --------------------------------------------------------

    invalid_net_values = 0

    for row in rows:

        amount = to_float(row["amount"])
        probability = to_float(
            row["true_recovery_probability"]
        )
        cost = to_float(row["action_cost"])

        expected_net = (
            amount * probability - cost
        )

        recorded_net = to_float(
            row["expected_net_value"]
        )

        if abs(expected_net - recorded_net) > 0.02:
            invalid_net_values += 1

    print(
        f"Expected net values: "
        f"{'PASS' if invalid_net_values == 0 else 'FAIL'} "
        f"({invalid_net_values} invalid)"
    )

    # --------------------------------------------------------
    # Average probability by action
    # --------------------------------------------------------

    print("\nAverage recovery probability by action:")

    for action in ACTIONS:

        action_rows = [
            row
            for row in rows
            if row["candidate_action"] == action
        ]

        probabilities = [
            to_float(
                row["true_recovery_probability"]
            )
            for row in action_rows
        ]

        avg_probability = (
            sum(probabilities) / len(probabilities)
            if probabilities else 0
        )

        print(
            f"  {action:<25} "
            f"{avg_probability:.2%}"
        )

    # --------------------------------------------------------
    # Oracle best action
    # --------------------------------------------------------

    grouped = {}

    for row in rows:

        failure_id = row["failure_id"]

        grouped.setdefault(
            failure_id,
            []
        ).append(row)

    oracle_counts = {
        action: 0
        for action in ACTIONS
    }

    for failure_id, candidates in grouped.items():

        best = max(
            candidates,
            key=lambda x: to_float(
                x["expected_net_value"]
            )
        )

        oracle_counts[
            best["candidate_action"]
        ] += 1

    print("\nOracle best-action distribution:")

    for action, count in oracle_counts.items():

        percentage = (
            count / len(grouped)
            if grouped else 0
        )

        print(
            f"  {action:<25} "
            f"{count:>5} "
            f"({percentage:.2%})"
        )

    # --------------------------------------------------------
    # Critical diversity check
    # --------------------------------------------------------

    # Count how many failures have different optimal actions
    # within the same failure reason.

    reason_action_sets = {}

    for failure_id, candidates in grouped.items():

        reason = candidates[0]["failure_reason"]

        best = max(
            candidates,
            key=lambda x: to_float(
                x["expected_net_value"]
            )
        )

        reason_action_sets.setdefault(
            reason,
            set()
        ).add(
            best["candidate_action"]
        )

    print("\nOptimal-action diversity by failure reason:")

    diversity_pass = True

    for reason, actions in reason_action_sets.items():

        print(
            f"  {reason:<25} "
            f"{len(actions)} optimal action type(s): "
            f"{', '.join(sorted(actions))}"
        )

        if len(actions) < 2:
            diversity_pass = False

    print(
        f"\nContextual action diversity: "
        f"{'PASS' if diversity_pass else 'WARNING'}"
    )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    all_pass = (
        row_count_pass
        and duplicate_ids == 0
        and action_coverage_pass
        and invalid_probabilities == 0
        and invalid_amounts == 0
        and invalid_net_values == 0
    )

    print("\n" + "-" * 70)

    if all_pass:
        print("M10A VALIDATION: PASS")
    else:
        print("M10A VALIDATION: FAIL")

    print("-" * 70)

    return all_pass


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\nRecoveryOS")
    print("M10A — Counterfactual Dataset Generator")

    print(f"\nProject root:")
    print(BASE_DIR)

    print(f"\nData directory:")
    print(DATA_DIR)

    print("\nLoading source datasets...")

    customers = load_csv("customers.csv")
    payments = load_csv("payments.csv")
    ground_truth = load_csv("recovery_ground_truth.csv")

    print(f"Customers:    {len(customers):,}")
    print(f"Payments:     {len(payments):,}")
    print(f"Ground truth: {len(ground_truth):,}")

    rows = build_counterfactual_dataset(
        ground_truth=ground_truth,
        customers=customers,
        payments=payments,
    )

    success = validate_dataset(
        rows=rows,
        ground_truth=ground_truth,
    )

    if not success:
        raise SystemExit(
            "\nM10A failed validation. "
            "Do not continue to M10B."
        )

    print("\nM10A completed successfully.")