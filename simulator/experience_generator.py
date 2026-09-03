import csv
import random
from pathlib import Path


random.seed(42)


# ============================================================
# CONFIGURATION
# ============================================================

EXPERIENCES_PER_FAILURE = 10

ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
]


ACTION_COSTS = {
    "RETRY_NOW": 2.00,
    "WAIT_AND_RETRY": 2.00,
    "SEND_REMINDER": 1.00,
    "PAYMENT_LINK": 3.00,
    "UPDATE_PAYMENT_METHOD": 3.00,
}


# ============================================================
# DATA LOADING
# ============================================================

def load_csv(filename):
    """
    Load a CSV file from the project's data directory.
    """

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

        return list(
            csv.DictReader(file)
        )


# ============================================================
# BALANCED HISTORICAL ACTIONS
# ============================================================

def get_balanced_historical_actions():
    """
    Return exactly two examples of every action.

    Five actions × two observations = ten experiences
    for every failure.

    The order is shuffled so the generated dataset does
    not always contain actions in the same sequence.
    """

    actions = []

    for action in ACTIONS:

        actions.append(action)
        actions.append(action)

    random.shuffle(actions)

    return actions


# ============================================================
# GROUND-TRUTH PROBABILITY
# ============================================================

def get_probability(
    ground_truth_record,
    action,
):
    """
    Read the hidden recovery probability for a specific
    action from the ground-truth record.

    The probability is used only to simulate the historical
    outcome. It is NOT written into the training dataset.
    """

    probability_field = (
        f"{action.lower()}_probability"
    )

    return float(
        ground_truth_record[
            probability_field
        ]
    )


# ============================================================
# EXPERIENCE GENERATION
# ============================================================

def generate_experiences(
    ground_truth,
    customers,
    payments,
):
    """
    Generate historical recovery experiences.

    For every failed payment:

        RETRY_NOW                 × 2
        WAIT_AND_RETRY            × 2
        SEND_REMINDER             × 2
        PAYMENT_LINK              × 2
        UPDATE_PAYMENT_METHOD     × 2

    Total:

        5 actions × 2 = 10 experiences/failure
    """

    # --------------------------------------------------------
    # Create fast lookup dictionaries.
    # --------------------------------------------------------

    customers_by_id = {
        customer["customer_id"]: customer
        for customer in customers
    }

    payments_by_id = {
        payment["payment_id"]: payment
        for payment in payments
    }

    experiences = []

    experience_number = 1

    # --------------------------------------------------------
    # Process every ground-truth failure.
    # --------------------------------------------------------

    for truth in ground_truth:

        customer_id = truth[
            "customer_id"
        ]

        payment_id = truth[
            "payment_id"
        ]

        failure_id = truth[
            "failure_id"
        ]

        customer = customers_by_id[
            customer_id
        ]

        payment = payments_by_id[
            payment_id
        ]

        failure_reason = truth[
            "failure_reason"
        ]

        # ----------------------------------------------------
        # Get balanced action list.
        # ----------------------------------------------------

        historical_actions = (
            get_balanced_historical_actions()
        )

        # ----------------------------------------------------
        # Generate exactly 10 experiences.
        # ----------------------------------------------------

        for action in historical_actions:

            # ------------------------------------------------
            # Hidden simulator probability.
            # ------------------------------------------------

            true_probability = (
                get_probability(
                    truth,
                    action,
                )
            )

            # ------------------------------------------------
            # Simulate actual historical outcome.
            # ------------------------------------------------

            recovered = (
                random.random()
                < true_probability
            )

            # ------------------------------------------------
            # Payment amount.
            # ------------------------------------------------

            amount = float(
                payment["amount"]
            )

            # ------------------------------------------------
            # Recovered amount.
            # ------------------------------------------------

            if recovered:

                recovered_amount = amount

            else:

                recovered_amount = 0.0

            # ------------------------------------------------
            # Action cost.
            # ------------------------------------------------

            action_cost = ACTION_COSTS[
                action
            ]

            # ------------------------------------------------
            # Net recovered value.
            # ------------------------------------------------

            net_value = (
                recovered_amount
                - action_cost
            )

            # ------------------------------------------------
            # Create experience record.
            # ------------------------------------------------

            experience = {

                # --------------------------------------------
                # IDs
                # --------------------------------------------

                "experience_id":
                    f"EXP_{experience_number:07d}",

                "failure_id":
                    failure_id,

                "payment_id":
                    payment_id,

                "customer_id":
                    customer_id,

                "subscription_id":
                    truth[
                        "subscription_id"
                    ],

                # --------------------------------------------
                # PAYMENT
                # --------------------------------------------

                "amount":
                    amount,

                # --------------------------------------------
                # FAILURE
                # --------------------------------------------

                "failure_reason":
                    failure_reason,

                # --------------------------------------------
                # CUSTOMER FEATURES
                # --------------------------------------------

                "account_age_days":
                    int(
                        customer[
                            "account_age_days"
                        ]
                    ),

                "successful_payments":
                    int(
                        customer[
                            "successful_payments"
                        ]
                    ),

                "failed_payments":
                    int(
                        customer[
                            "failed_payments"
                        ]
                    ),

                "total_payments":
                    int(
                        customer[
                            "total_payments"
                        ]
                    ),

                "payment_success_rate":
                    float(
                        customer[
                            "payment_success_rate"
                        ]
                    ),

                "historical_recovery_rate":
                    float(
                        customer[
                            "historical_recovery_rate"
                        ]
                    ),

                "engagement_score":
                    float(
                        customer[
                            "engagement_score"
                        ]
                    ),

                "behavior_profile":
                    customer[
                        "behavior_profile"
                    ],

                # --------------------------------------------
                # ACTION
                # --------------------------------------------

                "action_taken":
                    action,

                "action_cost":
                    action_cost,

                # --------------------------------------------
                # OUTCOME
                # --------------------------------------------

                "recovered":
                    int(
                        recovered
                    ),

                "recovered_amount":
                    recovered_amount,

                "net_value":
                    net_value,
            }

            experiences.append(
                experience
            )

            experience_number += 1

    return experiences


# ============================================================
# SAVE EXPERIENCES
# ============================================================

def save_experiences(
    experiences
):

    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "recovery_experiences.csv"
    )

    fieldnames = [
        "experience_id",
        "failure_id",
        "payment_id",
        "customer_id",
        "subscription_id",
        "amount",
        "failure_reason",
        "account_age_days",
        "successful_payments",
        "failed_payments",
        "total_payments",
        "payment_success_rate",
        "historical_recovery_rate",
        "engagement_score",
        "behavior_profile",
        "action_taken",
        "action_cost",
        "recovered",
        "recovered_amount",
        "net_value",
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
            experiences
        )

    return output_path


# ============================================================
# VALIDATION
# ============================================================

def validate_experiences(
    experiences,
    ground_truth,
):
    """
    Validate the generated historical dataset.
    """

    print(
        "\n========== EXPERIENCE VALIDATION =========="
    )

    # --------------------------------------------------------
    # Expected count
    # --------------------------------------------------------

    expected_count = (
        len(ground_truth)
        * EXPERIENCES_PER_FAILURE
    )

    print(
        f"Ground-truth opportunities: "
        f"{len(ground_truth)}"
    )

    print(
        f"Experiences per failure: "
        f"{EXPERIENCES_PER_FAILURE}"
    )

    print(
        f"Expected experiences: "
        f"{expected_count}"
    )

    print(
        f"Actual experiences: "
        f"{len(experiences)}"
    )

    count_correct = (
        len(experiences)
        == expected_count
    )

    print(
        f"Experience count correct: "
        f"{'YES ✅' if count_correct else 'NO ❌'}"
    )

    # --------------------------------------------------------
    # Duplicate experience IDs
    # --------------------------------------------------------

    experience_ids = [
        experience["experience_id"]
        for experience in experiences
    ]

    duplicate_ids = (
        len(experience_ids)
        - len(set(experience_ids))
    )

    print(
        f"Duplicate experience IDs: "
        f"{duplicate_ids}"
    )

    # --------------------------------------------------------
    # Invalid actions
    # --------------------------------------------------------

    invalid_actions = [
        experience
        for experience in experiences
        if experience["action_taken"]
        not in ACTIONS
    ]

    print(
        f"Invalid actions: "
        f"{len(invalid_actions)}"
    )

    # --------------------------------------------------------
    # Invalid recovery outcomes
    # --------------------------------------------------------

    invalid_outcomes = [
        experience
        for experience in experiences
        if int(
            experience["recovered"]
        )
        not in {0, 1}
    ]

    print(
        f"Invalid recovery outcomes: "
        f"{len(invalid_outcomes)}"
    )

    # --------------------------------------------------------
    # Invalid payment amounts
    # --------------------------------------------------------

    invalid_amounts = [
        experience
        for experience in experiences
        if float(
            experience["amount"]
        ) <= 0
    ]

    print(
        f"Invalid payment amounts: "
        f"{len(invalid_amounts)}"
    )

    # --------------------------------------------------------
    # Invalid recovered amounts
    # --------------------------------------------------------

    invalid_recovered_amounts = []

    for experience in experiences:

        amount = float(
            experience["amount"]
        )

        recovered = int(
            experience["recovered"]
        )

        recovered_amount = float(
            experience["recovered_amount"]
        )

        if recovered == 1:

            if recovered_amount != amount:

                invalid_recovered_amounts.append(
                    experience
                )

        else:

            if recovered_amount != 0:

                invalid_recovered_amounts.append(
                    experience
                )

    print(
        f"Invalid recovered amounts: "
        f"{len(invalid_recovered_amounts)}"
    )

    # --------------------------------------------------------
    # Action distribution
    # --------------------------------------------------------

    action_counts = {}

    for experience in experiences:

        action = experience[
            "action_taken"
        ]

        action_counts[action] = (
            action_counts.get(
                action,
                0,
            )
            + 1
        )

    print(
        "\nHistorical action distribution:"
    )

    for action in ACTIONS:

        count = action_counts.get(
            action,
            0,
        )

        percentage = (
            count
            / len(experiences)
            * 100
            if experiences
            else 0
        )

        print(
            f"{action}: "
            f"{count} "
            f"({percentage:.2f}%)"
        )

    # --------------------------------------------------------
    # Per-failure action balance
    # --------------------------------------------------------

    failure_action_counts = {}

    for experience in experiences:

        failure_id = experience[
            "failure_id"
        ]

        action = experience[
            "action_taken"
        ]

        if failure_id not in (
            failure_action_counts
        ):

            failure_action_counts[
                failure_id
            ] = {}

        failure_action_counts[
            failure_id
        ][action] = (
            failure_action_counts[
                failure_id
            ].get(
                action,
                0,
            )
            + 1
        )

    unbalanced_failures = []

    for failure_id, counts in (
        failure_action_counts.items()
    ):

        for action in ACTIONS:

            if counts.get(
                action,
                0,
            ) != 2:

                unbalanced_failures.append(
                    failure_id
                )

                break

    print(
        f"\nFailures with incorrect "
        f"action balance: "
        f"{len(unbalanced_failures)}"
    )

    # --------------------------------------------------------
    # Failure distribution
    # --------------------------------------------------------

    failure_counts = {}

    for experience in experiences:

        reason = experience[
            "failure_reason"
        ]

        failure_counts[reason] = (
            failure_counts.get(
                reason,
                0,
            )
            + 1
        )

    print(
        "\nFailure distribution:"
    )

    for reason, count in sorted(
        failure_counts.items()
    ):

        print(
            f"{reason}: {count}"
        )

    # --------------------------------------------------------
    # Historical recovery rate
    # --------------------------------------------------------

    recovered_count = sum(
        int(
            experience["recovered"]
        )
        for experience in experiences
    )

    recovery_rate = (
        recovered_count
        / len(experiences)
        if experiences
        else 0
    )

    print(
        f"\nHistorical recovery rate: "
        f"{recovery_rate:.2%}"
    )

    # --------------------------------------------------------
    # Recovery rate by action
    # --------------------------------------------------------

    print(
        "\nRecovery rate by action:"
    )

    for action in ACTIONS:

        action_experiences = [
            experience
            for experience in experiences
            if experience[
                "action_taken"
            ] == action
        ]

        if action_experiences:

            action_recovery_rate = (
                sum(
                    int(
                        experience[
                            "recovered"
                        ]
                    )
                    for experience
                    in action_experiences
                )
                / len(
                    action_experiences
                )
            )

        else:

            action_recovery_rate = 0

        print(
            f"{action}: "
            f"{action_recovery_rate:.2%}"
        )

    # --------------------------------------------------------
    # Sample
    # --------------------------------------------------------

    if experiences:

        sample = experiences[0]

        print(
            "\nSample recovery experience:"
        )

        print(
            f"Experience: "
            f"{sample['experience_id']}"
        )

        print(
            f"Failure: "
            f"{sample['failure_id']}"
        )

        print(
            f"Amount: "
            f"₹{float(sample['amount']):,.2f}"
        )

        print(
            f"Failure reason: "
            f"{sample['failure_reason']}"
        )

        print(
            f"Action: "
            f"{sample['action_taken']}"
        )

        print(
            f"Recovered: "
            f"{'YES' if int(sample['recovered']) else 'NO'}"
        )

        print(
            f"Recovered amount: "
            f"₹{float(sample['recovered_amount']):,.2f}"
        )

        print(
            f"Net value: "
            f"₹{float(sample['net_value']):,.2f}"
        )

    print(
        "==========================================="
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    customers = load_csv(
        "customers.csv"
    )

    payments = load_csv(
        "payments.csv"
    )

    ground_truth = load_csv(
        "recovery_ground_truth.csv"
    )

    # --------------------------------------------------------
    # Generate experiences
    # --------------------------------------------------------

    experiences = generate_experiences(
        ground_truth,
        customers,
        payments,
    )

    print(
        f"Generated {len(experiences)} "
        f"historical recovery experiences"
    )

    # --------------------------------------------------------
    # Save dataset
    # --------------------------------------------------------

    output_path = save_experiences(
        experiences
    )

    print(
        f"Dataset saved to: "
        f"{output_path}"
    )

    # --------------------------------------------------------
    # Validate dataset
    # --------------------------------------------------------

    validate_experiences(
        experiences,
        ground_truth,
    )