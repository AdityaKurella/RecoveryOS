import csv
from pathlib import Path
from collections import defaultdict


# ============================================================
# M10E — POLICY DIAGNOSTICS
# ============================================================

ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
]

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

TEST_PATH = DATA_DIR / "test_features.csv"
COUNTERFACTUAL_PATH = DATA_DIR / "counterfactual_training.csv"
POLICY_PATH = DATA_DIR / "ml_decision" / "m10c_policy_decisions.csv"


# ============================================================
# HELPERS
# ============================================================

def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found:\n{path}")

    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ============================================================
# LOAD DATA
# ============================================================

print("\n" + "=" * 70)
print("M10E — RECOVERYOS POLICY DIAGNOSTICS")
print("=" * 70)

print("\nLoading datasets...")

test_rows = load_csv(TEST_PATH)
counterfactual_rows = load_csv(COUNTERFACTUAL_PATH)
policy_rows = load_csv(POLICY_PATH)

print(f"Test cases:          {len(test_rows):,}")
print(f"Counterfactual rows: {len(counterfactual_rows):,}")
print(f"Policy decisions:    {len(policy_rows):,}")


# ============================================================
# BUILD LOOKUPS
# ============================================================

test_map = {
    row["failure_id"]: row
    for row in test_rows
}

policy_map = {
    row["failure_id"]: row
    for row in policy_rows
}

counterfactual_map = defaultdict(dict)

for row in counterfactual_rows:
    counterfactual_map[
        row["failure_id"]
    ][row["candidate_action"]] = row


# ============================================================
# DIAGNOSTIC RECORDS
# ============================================================

diagnostics = []

for failure_id, test in test_map.items():

    if failure_id not in policy_map:
        continue

    if failure_id not in counterfactual_map:
        continue

    policy = policy_map[failure_id]
    candidates = counterfactual_map[failure_id]

    selected_action = policy["selected_action"]

    if selected_action not in candidates:
        continue

    # --------------------------------------------------------
    # RecoveryOS selected action
    # --------------------------------------------------------

    selected = candidates[selected_action]

    selected_net = to_float(
        selected["expected_net_value"]
    )

    # --------------------------------------------------------
    # Oracle action
    # --------------------------------------------------------

    oracle = max(
        candidates.values(),
        key=lambda row: to_float(
            row["expected_net_value"]
        )
    )

    oracle_action = oracle["candidate_action"]

    oracle_net = to_float(
        oracle["expected_net_value"]
    )

    # --------------------------------------------------------
    # Opportunity loss
    # --------------------------------------------------------

    opportunity_loss = max(
        0.0,
        oracle_net - selected_net
    )

    # --------------------------------------------------------
    # Prediction probability
    # --------------------------------------------------------

    selected_probability = to_float(
        selected["true_recovery_probability"]
    )

    model_probability = to_float(
        policy.get(
            "estimated_probability",
            0
        )
    )

    amount = to_float(
        test.get(
            "amount",
            selected["amount"]
        )
    )

    failure_reason = test.get(
        "failure_reason",
        selected["failure_reason"]
    )

    behavior_profile = test.get(
        "behavior_profile",
        selected["behavior_profile"]
    )

    diagnostics.append({
        "failure_id": failure_id,
        "amount": amount,
        "failure_reason": failure_reason,
        "behavior_profile": behavior_profile,
        "selected_action": selected_action,
        "oracle_action": oracle_action,
        "selected_net": selected_net,
        "oracle_net": oracle_net,
        "opportunity_loss": opportunity_loss,
        "selected_true_probability": selected_probability,
        "model_probability": model_probability,
    })


# ============================================================
# BASIC SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("OVERALL DIAGNOSTIC")
print("=" * 70)

total_cases = len(diagnostics)

wrong_actions = [
    row
    for row in diagnostics
    if row["selected_action"] != row["oracle_action"]
]

correct_actions = [
    row
    for row in diagnostics
    if row["selected_action"] == row["oracle_action"]
]

total_opportunity_loss = sum(
    row["opportunity_loss"]
    for row in diagnostics
)

print(f"\nCases analyzed: {total_cases:,}")

print(
    f"Oracle action matched: "
    f"{len(correct_actions):,} "
    f"({len(correct_actions) / total_cases:.2%})"
)

print(
    f"Oracle action mismatched: "
    f"{len(wrong_actions):,} "
    f"({len(wrong_actions) / total_cases:.2%})"
)

print(
    f"Total opportunity loss: "
    f"₹{total_opportunity_loss:,.2f}"
)


# ============================================================
# ACTION CONFUSION
# ============================================================

print("\n" + "=" * 70)
print("RECOVERYOS ACTION → ORACLE ACTION")
print("=" * 70)

confusion = defaultdict(int)

for row in diagnostics:
    confusion[
        (
            row["selected_action"],
            row["oracle_action"]
        )
    ] += 1

for selected_action in ACTIONS:

    print(
        f"\nRecoveryOS chose: "
        f"{selected_action}"
    )

    matching = []

    for oracle_action in ACTIONS:

        count = confusion[
            (
                selected_action,
                oracle_action
            )
        ]

        if count > 0:
            matching.append(
                (oracle_action, count)
            )

    matching.sort(
        key=lambda x: x[1],
        reverse=True
    )

    for oracle_action, count in matching:

        print(
            f"  → Oracle: "
            f"{oracle_action:<25} "
            f"{count}"
        )


# ============================================================
# LOSS BY SELECTED ACTION
# ============================================================

print("\n" + "=" * 70)
print("OPPORTUNITY LOSS BY RECOVERYOS ACTION")
print("=" * 70)

action_stats = defaultdict(
    lambda: {
        "cases": 0,
        "wrong": 0,
        "loss": 0.0,
    }
)

for row in diagnostics:

    action = row["selected_action"]

    action_stats[action]["cases"] += 1

    if action != row["oracle_action"]:
        action_stats[action]["wrong"] += 1

    action_stats[action]["loss"] += (
        row["opportunity_loss"]
    )

for action in ACTIONS:

    stats = action_stats[action]

    cases = stats["cases"]

    wrong_rate = (
        stats["wrong"] / cases
        if cases else 0
    )

    average_loss = (
        stats["loss"] / cases
        if cases else 0
    )

    print(
        f"\n{action}"
    )

    print(
        f"  Cases: {cases}"
    )

    print(
        f"  Wrong decisions: "
        f"{stats['wrong']} "
        f"({wrong_rate:.2%})"
    )

    print(
        f"  Total opportunity loss: "
        f"₹{stats['loss']:,.2f}"
    )

    print(
        f"  Avg loss/case: "
        f"₹{average_loss:,.2f}"
    )


# ============================================================
# FAILURE REASON ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("DIAGNOSTICS BY FAILURE REASON")
print("=" * 70)

reason_stats = defaultdict(
    lambda: {
        "cases": 0,
        "wrong": 0,
        "loss": 0.0,
    }
)

for row in diagnostics:

    reason = row["failure_reason"]

    reason_stats[reason]["cases"] += 1

    if row["selected_action"] != row["oracle_action"]:
        reason_stats[reason]["wrong"] += 1

    reason_stats[reason]["loss"] += (
        row["opportunity_loss"]
    )

reason_order = sorted(
    reason_stats.items(),
    key=lambda x: x[1]["loss"],
    reverse=True
)

for reason, stats in reason_order:

    cases = stats["cases"]

    wrong_rate = (
        stats["wrong"] / cases
        if cases else 0
    )

    print(
        f"\n{reason}"
    )

    print(
        f"  Cases: {cases}"
    )

    print(
        f"  Wrong: {stats['wrong']} "
        f"({wrong_rate:.2%})"
    )

    print(
        f"  Opportunity loss: "
        f"₹{stats['loss']:,.2f}"
    )


# ============================================================
# BEHAVIOR PROFILE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("DIAGNOSTICS BY CUSTOMER PROFILE")
print("=" * 70)

profile_stats = defaultdict(
    lambda: {
        "cases": 0,
        "wrong": 0,
        "loss": 0.0,
    }
)

for row in diagnostics:

    profile = row["behavior_profile"]

    profile_stats[profile]["cases"] += 1

    if row["selected_action"] != row["oracle_action"]:
        profile_stats[profile]["wrong"] += 1

    profile_stats[profile]["loss"] += (
        row["opportunity_loss"]
    )

profile_order = sorted(
    profile_stats.items(),
    key=lambda x: x[1]["loss"],
    reverse=True
)

for profile, stats in profile_order:

    cases = stats["cases"]

    wrong_rate = (
        stats["wrong"] / cases
        if cases else 0
    )

    print(
        f"\n{profile}"
    )

    print(
        f"  Cases: {cases}"
    )

    print(
        f"  Wrong: {stats['wrong']} "
        f"({wrong_rate:.2%})"
    )

    print(
        f"  Opportunity loss: "
        f"₹{stats['loss']:,.2f}"
    )


# ============================================================
# AMOUNT SEGMENTS
# ============================================================

def amount_segment(amount):

    if amount < 1000:
        return "< ₹1K"

    if amount < 3000:
        return "₹1K–₹3K"

    if amount < 5000:
        return "₹3K–₹5K"

    return "₹5K+"


print("\n" + "=" * 70)
print("DIAGNOSTICS BY PAYMENT VALUE")
print("=" * 70)

amount_stats = defaultdict(
    lambda: {
        "cases": 0,
        "wrong": 0,
        "loss": 0.0,
    }
)

for row in diagnostics:

    segment = amount_segment(
        row["amount"]
    )

    amount_stats[segment]["cases"] += 1

    if row["selected_action"] != row["oracle_action"]:
        amount_stats[segment]["wrong"] += 1

    amount_stats[segment]["loss"] += (
        row["opportunity_loss"]
    )

for segment in [
    "< ₹1K",
    "₹1K–₹3K",
    "₹3K–₹5K",
    "₹5K+",
]:

    stats = amount_stats[segment]

    cases = stats["cases"]

    wrong_rate = (
        stats["wrong"] / cases
        if cases else 0
    )

    print(
        f"\n{segment}"
    )

    print(
        f"  Cases: {cases}"
    )

    print(
        f"  Wrong: {stats['wrong']} "
        f"({wrong_rate:.2%})"
    )

    print(
        f"  Opportunity loss: "
        f"₹{stats['loss']:,.2f}"
    )


# ============================================================
# TOP 20 LOST CASES
# ============================================================

print("\n" + "=" * 70)
print("TOP 20 HIGHEST-VALUE POLICY MISTAKES")
print("=" * 70)

top_losses = sorted(
    wrong_actions,
    key=lambda row: row["opportunity_loss"],
    reverse=True
)[:20]

for index, row in enumerate(
    top_losses,
    start=1
):

    print(
        f"\n{index}. "
        f"{row['failure_id']}"
    )

    print(
        f"   Reason: "
        f"{row['failure_reason']}"
    )

    print(
        f"   Profile: "
        f"{row['behavior_profile']}"
    )

    print(
        f"   Amount: "
        f"₹{row['amount']:,.2f}"
    )

    print(
        f"   RecoveryOS: "
        f"{row['selected_action']}"
    )

    print(
        f"   Oracle: "
        f"{row['oracle_action']}"
    )

    print(
        f"   RecoveryOS NET: "
        f"₹{row['selected_net']:,.2f}"
    )

    print(
        f"   Oracle NET: "
        f"₹{row['oracle_net']:,.2f}"
    )

    print(
        f"   Opportunity loss: "
        f"₹{row['opportunity_loss']:,.2f}"
    )


# ============================================================
# SAVE DIAGNOSTIC CSV
# ============================================================

output_path = (
    DATA_DIR
    / "evaluation"
    / "m10e_policy_diagnostics.csv"
)

output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    output_path,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    fieldnames = list(
        diagnostics[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(diagnostics)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("M10E COMPLETE")
print("=" * 70)

print(
    f"\nDiagnostic file saved to:"
    f"\n{output_path}"
)

print(
    "\nNo datasets, models, or policies were modified."
)

print(
    "\nM10E diagnostic analysis complete. ✅"
)