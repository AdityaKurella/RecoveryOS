import pickle
from pathlib import Path

import pandas as pd


# ============================================================
# M10C — COUNTERFACTUAL RECOVERY POLICY OPTIMIZER
# ============================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

TEST_FEATURES_PATH = DATA_DIR / "test_features.csv"
MODEL_PATH = DATA_DIR / "recovery_probability" / "counterfactual_model.pkl"
OUTPUT_PATH = DATA_DIR / "ml_decision" / "m10c_policy_decisions.csv"


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


# These exist in test_features.csv
BASE_FEATURES = [
    "amount",
    "account_age_days",
    "successful_payments",
    "failed_payments",
    "total_payments",
    "payment_success_rate",
    "historical_recovery_rate",
    "engagement_score",
    "failure_reason",
    "behavior_profile",
]

# Model receives these 11 features
MODEL_FEATURES = BASE_FEATURES + [
    "candidate_action"
]


# ============================================================
# LOAD TEST CASES
# ============================================================

print("\n========== M10C COUNTERFACTUAL POLICY OPTIMIZER ==========")

test_df = pd.read_csv(TEST_FEATURES_PATH)

print(f"Test cases loaded: {len(test_df)}")


# ============================================================
# VALIDATE TEST DATA
# ============================================================

print("\n========== TEST DATA VALIDATION ==========")

missing_columns = [
    col
    for col in BASE_FEATURES
    if col not in test_df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required feature columns: {missing_columns}"
    )


if "failure_id" not in test_df.columns:
    raise ValueError("Missing failure_id column")


duplicate_ids = test_df["failure_id"].duplicated().sum()

if duplicate_ids > 0:
    raise ValueError(
        f"Duplicate failure IDs found: {duplicate_ids}"
    )


missing_values = (
    test_df[BASE_FEATURES]
    .isnull()
    .sum()
    .sum()
)

if missing_values > 0:
    raise ValueError(
        f"Missing feature values found: {missing_values}"
    )


print(f"Required base fields: {len(BASE_FEATURES)}")
print(f"Duplicate failure IDs: {duplicate_ids}")
print(f"Missing feature values: {missing_values}")
print("Candidate actions: generated internally by M10C")
print("Validation: PASS")


# ============================================================
# LOAD M10F MODEL
# ============================================================

print("\n========== LOADING M10F MODEL ==========")

import gzip

if MODEL_PATH.with_name("counterfactual_model.pkl.gz").exists():
    with gzip.open(MODEL_PATH.with_name("counterfactual_model.pkl.gz"), "rb") as f:
        model_bundle = pickle.load(f)
elif MODEL_PATH.exists():
    try:
        with gzip.open(MODEL_PATH, "rb") as f:
            model_bundle = pickle.load(f)
    except Exception:
        with open(MODEL_PATH, "rb") as f:
            model_bundle = pickle.load(f)
else:
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH} or {MODEL_PATH.with_name('counterfactual_model.pkl.gz')}")



if isinstance(model_bundle, dict) and "model" in model_bundle:

    model = model_bundle["model"]

    print("Model format: M10F model bundle")

    print(
        "Feature version:",
        model_bundle.get("feature_version", "unknown")
    )

    print(
        "Training failures:",
        model_bundle.get("train_failure_count", "unknown")
    )

    print(
        "Held-out failures:",
        model_bundle.get("validation_failure_count", "unknown")
    )

    held_out_metrics = model_bundle.get(
        "held_out_metrics"
    )

    if held_out_metrics:
        print("\nM10F held-out evidence:")

        for metric, value in held_out_metrics.items():

            if isinstance(value, float):
                print(f"{metric}: {value:.4f}")

            else:
                print(f"{metric}: {value}")

else:

    model = model_bundle

    print("Model format: legacy raw sklearn model")


print("Model loaded successfully.")


# ============================================================
# MODEL FEATURE COMPATIBILITY
# ============================================================

print("\n========== MODEL COMPATIBILITY CHECK ==========")

if isinstance(model_bundle, dict):

    bundle_numeric = model_bundle.get(
        "numeric_features",
        []
    )

    bundle_categorical = model_bundle.get(
        "categorical_features",
        []
    )

    expected_model_features = (
        bundle_numeric +
        bundle_categorical
    )

    print(
        f"Model expects: "
        f"{len(expected_model_features)} features"
    )

    missing_base_features = [
        col
        for col in expected_model_features
        if col != "candidate_action"
        and col not in test_df.columns
    ]

    if missing_base_features:

        raise ValueError(
            "Test data is missing model base features: "
            f"{missing_base_features}"
        )

    if "candidate_action" not in expected_model_features:

        raise ValueError(
            "M10F model does not contain "
            "candidate_action as a feature."
        )

    print(
        "candidate_action: generated after "
        "candidate expansion"
    )

print("Feature compatibility: PASS")


# ============================================================
# GENERATE FAILURE × ACTION CANDIDATES
# ============================================================

print("\n========== GENERATING CANDIDATE ACTIONS ==========")

candidate_rows = []

for _, row in test_df.iterrows():

    for action in ACTIONS:

        candidate = row.copy()

        candidate["candidate_action"] = action

        candidate_rows.append(candidate)


candidate_df = pd.DataFrame(candidate_rows)


expected_rows = (
    len(test_df) *
    len(ACTIONS)
)

print(
    f"Candidate rows generated: "
    f"{len(candidate_df)}"
)

print(
    f"Expected candidate rows: "
    f"{expected_rows}"
)


if len(candidate_df) != expected_rows:

    raise ValueError(
        f"Expected {expected_rows} candidate rows, "
        f"got {len(candidate_df)}"
    )


# Validate generated actions

generated_actions = set(
    candidate_df["candidate_action"]
)

missing_actions = set(ACTIONS) - generated_actions

extra_actions = (
    generated_actions - set(ACTIONS)
)

if missing_actions or extra_actions:

    raise ValueError(
        f"Missing actions: {missing_actions}; "
        f"Extra actions: {extra_actions}"
    )


print("Five-action candidate coverage: PASS")
print("Candidate generation: PASS")


# ============================================================
# PREDICT RECOVERY PROBABILITIES
# ============================================================

print("\n========== PREDICTING RECOVERY PROBABILITIES ==========")

X = candidate_df[MODEL_FEATURES]

probabilities = model.predict_proba(X)[:, 1]

candidate_df[
    "estimated_recovery_probability"
] = probabilities


# ============================================================
# PROBABILITY VALIDATION
# ============================================================

invalid_probability_count = (
    (
        candidate_df[
            "estimated_recovery_probability"
        ] < 0
    )
    |
    (
        candidate_df[
            "estimated_recovery_probability"
        ] > 1
    )
).sum()


if invalid_probability_count > 0:

    raise ValueError(
        "Invalid recovery probabilities detected: "
        f"{invalid_probability_count}"
    )


print(
    f"Probability predictions: "
    f"{len(probabilities)}"
)

print(
    f"Minimum probability: "
    f"{probabilities.min():.4f}"
)

print(
    f"Maximum probability: "
    f"{probabilities.max():.4f}"
)

print("Probability validation: PASS")


# ============================================================
# EXPECTED ECONOMIC VALUE
# ============================================================

print(
    "\n========== CALCULATING EXPECTED NET RECOVERY =========="
)

candidate_df[
    "expected_gross_recovery"
] = (
    candidate_df["amount"]
    *
    candidate_df[
        "estimated_recovery_probability"
    ]
)


candidate_df[
    "intervention_cost"
] = (
    candidate_df[
        "candidate_action"
    ].map(ACTION_COSTS)
)


candidate_df[
    "expected_net_recovery"
] = (
    candidate_df[
        "expected_gross_recovery"
    ]
    -
    candidate_df[
        "intervention_cost"
    ]
)


# ============================================================
# SELECT BEST ACTION
# ============================================================

print(
    "\n========== SELECTING RECOVERYOS ACTION =========="
)

candidate_df = candidate_df.sort_values(
    [
        "failure_id",
        "expected_net_recovery",
    ],
    ascending=[
        True,
        False,
    ],
)


selected_df = (
    candidate_df
    .groupby(
        "failure_id",
        as_index=False
    )
    .first()
)


# ============================================================
# FINAL DECISION VALIDATION
# ============================================================

if len(selected_df) != len(test_df):

    raise ValueError(
        "Policy optimizer did not produce "
        "exactly one decision per failure."
    )


if selected_df[
    "failure_id"
].duplicated().any():

    raise ValueError(
        "Duplicate failure IDs found "
        "in final policy."
    )


# ============================================================
# REVENUE SUMMARY
# ============================================================

revenue_at_risk = (
    selected_df["amount"].sum()
)


expected_gross_recovery = (
    selected_df[
        "expected_gross_recovery"
    ].sum()
)


intervention_cost = (
    selected_df[
        "intervention_cost"
    ].sum()
)


expected_net_recovery = (
    selected_df[
        "expected_net_recovery"
    ].sum()
)


expected_recovery_rate = (
    expected_gross_recovery /
    revenue_at_risk
    if revenue_at_risk > 0
    else 0
)


# ============================================================
# ACTION DISTRIBUTION
# ============================================================

action_distribution = (
    selected_df[
        "candidate_action"
    ].value_counts()
)


# ============================================================
# OUTPUT
# ============================================================

output_columns = [
    "failure_id",
    "customer_id",
    "subscription_id",
    "amount",
    "failure_reason",
    "behavior_profile",
    "candidate_action",
    "estimated_recovery_probability",
    "expected_gross_recovery",
    "intervention_cost",
    "expected_net_recovery",
]


output_df = selected_df[
    output_columns
].copy()


OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


output_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ============================================================
# FINAL REPORT
# ============================================================

print("\n========== M10C POLICY RESULTS ==========")

print(
    f"Failures evaluated: "
    f"{len(selected_df)}"
)

print(
    f"Revenue at risk: "
    f"₹{revenue_at_risk:,.2f}"
)

print(
    f"Expected gross recovery: "
    f"₹{expected_gross_recovery:,.2f}"
)

print(
    f"Intervention cost: "
    f"₹{intervention_cost:,.2f}"
)

print(
    f"Expected NET recovery: "
    f"₹{expected_net_recovery:,.2f}"
)

print(
    f"Expected recovery rate: "
    f"{expected_recovery_rate * 100:.2f}%"
)


print("\nSelected action distribution:")

for action in ACTIONS:

    count = action_distribution.get(
        action,
        0
    )

    percentage = (
        count /
        len(selected_df) *
        100
        if len(selected_df) > 0
        else 0
    )

    print(
        f"{action:28s}"
        f"{count:4d}"
        f" ({percentage:6.2f}%)"
    )


# ============================================================
# SAMPLE DECISIONS
# ============================================================

print(
    "\n========== SAMPLE POLICY DECISIONS =========="
)

sample_columns = [
    "failure_id",
    "amount",
    "failure_reason",
    "behavior_profile",
    "candidate_action",
    "estimated_recovery_probability",
    "expected_net_recovery",
]


print(
    output_df[
        sample_columns
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\n========== FINAL VALIDATION ==========")

print(
    f"Expected decisions: "
    f"{len(test_df)}"
)

print(
    f"Actual decisions:   "
    f"{len(output_df)}"
)

print(
    f"Duplicate decisions: "
    f"{output_df['failure_id'].duplicated().sum()}"
)

print(
    f"Invalid probabilities: "
    f"{invalid_probability_count}"
)

print(
    f"Five-action candidate coverage: "
    f"{len(candidate_df) == expected_rows}"
)

print(
    f"Unique failure coverage: "
    f"{output_df['failure_id'].nunique() == len(test_df)}"
)


print(
    "\nM10C policy optimization complete. ✅"
)

print("\nSaved to:")
print(OUTPUT_PATH)