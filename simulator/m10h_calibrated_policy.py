import pickle
from pathlib import Path

import pandas as pd


# ============================================================
# M10H — CALIBRATED POLICY OPTIMIZER
# ============================================================
#
# M10F:
#   Predict recovery probability
#
# M10G:
#   Calibrate those probabilities
#
# M10H:
#   Use calibrated probabilities to maximize expected NET
#   recovered revenue.
#
# IMPORTANT:
# - Does NOT modify M10C.
# - Does NOT use M10D ground truth.
# - Uses the existing 559 test failures only for prediction.
# - M10D will perform the final hidden evaluation.
#
# ============================================================


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


TEST_FEATURES_PATH = (
    DATA_DIR / "test_features.csv"
)

MODEL_PATH = (
    DATA_DIR
    / "recovery_probability"
    / "counterfactual_model.pkl"
)

CALIBRATION_PATH = (
    DATA_DIR
    / "recovery_probability"
    / "m10g_calibration.pkl"
)

OUTPUT_PATH = (
    DATA_DIR
    / "ml_decision"
    / "m10h_calibrated_policy_decisions.csv"
)


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


BASE_FEATURES = [
    "failure_id",
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
]


MODEL_FEATURES = [
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
    "candidate_action",
]


# ============================================================
# START
# ============================================================

print(
    "\n========== M10H CALIBRATED POLICY OPTIMIZER =========="
)


# ============================================================
# LOAD TEST DATA
# ============================================================

test_df = pd.read_csv(
    TEST_FEATURES_PATH
)


print(
    f"Test cases loaded: {len(test_df)}"
)


# ============================================================
# VALIDATE TEST DATA
# ============================================================

missing_columns = [
    column
    for column in BASE_FEATURES
    if column not in test_df.columns
]


if missing_columns:

    raise ValueError(
        "Missing test columns: "
        f"{missing_columns}"
    )


duplicate_ids = (
    test_df["failure_id"]
    .duplicated()
    .sum()
)


print(
    f"Duplicate failure IDs: {duplicate_ids}"
)


if duplicate_ids > 0:

    raise ValueError(
        "Duplicate failure IDs found."
    )


missing_values = (
    test_df[BASE_FEATURES]
    .isna()
    .sum()
    .sum()
)


print(
    f"Missing required values: "
    f"{missing_values}"
)


if missing_values > 0:

    raise ValueError(
        "Missing values found in test data."
    )


# ============================================================
# LOAD M10F MODEL
# ============================================================

print(
    "\n========== LOADING M10F MODEL =========="
)


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



if not isinstance(
    model_bundle,
    dict,
):

    raise ValueError(
        "Expected M10F model bundle."
    )


model = model_bundle["model"]


print(
    "Model feature version:",
    model_bundle.get(
        "feature_version",
        "unknown",
    ),
)


# ============================================================
# LOAD M10G CALIBRATION
# ============================================================

print(
    "\n========== LOADING M10G CALIBRATION =========="
)


with open(
    CALIBRATION_PATH,
    "rb",
) as f:

    calibration_bundle = pickle.load(f)


if not isinstance(
    calibration_bundle,
    dict,
):

    raise ValueError(
        "Invalid M10G calibration bundle."
    )


global_calibrator = (
    calibration_bundle[
        "global_calibrator"
    ]
)


action_calibrators = (
    calibration_bundle[
        "action_calibrators"
    ]
)


print(
    "Calibration version:",
    calibration_bundle.get(
        "feature_version",
        "unknown",
    ),
)


print(
    "Action calibrators available:",
    len(action_calibrators),
)


missing_calibrators = [
    action
    for action in ACTIONS
    if action not in action_calibrators
]


if missing_calibrators:

    raise ValueError(
        "Missing action calibrators: "
        f"{missing_calibrators}"
    )


# ============================================================
# CANDIDATE ACTION EXPANSION
# ============================================================

print(
    "\n========== GENERATING CANDIDATE ACTIONS =========="
)


candidate_frames = []


for action in ACTIONS:

    candidate = test_df.copy()

    candidate[
        "candidate_action"
    ] = action

    candidate_frames.append(
        candidate
    )


candidate_df = pd.concat(
    candidate_frames,
    ignore_index=True,
)


print(
    f"Candidate rows generated: "
    f"{len(candidate_df)}"
)


expected_candidate_rows = (
    len(test_df)
    * len(ACTIONS)
)


if len(candidate_df) != expected_candidate_rows:

    raise ValueError(
        "Unexpected candidate row count."
    )


# ============================================================
# RAW M10F PREDICTIONS
# ============================================================

print(
    "\n========== GENERATING M10F PREDICTIONS =========="
)


X = candidate_df[
    MODEL_FEATURES
]


raw_probabilities = model.predict_proba(
    X
)[:, 1]


candidate_df[
    "raw_probability"
] = raw_probabilities


# ============================================================
# APPLY ACTION-SPECIFIC CALIBRATION
# ============================================================

print(
    "\n========== APPLYING M10G CALIBRATION =========="
)


candidate_df[
    "calibrated_probability"
] = 0.0


for action in ACTIONS:

    mask = (
        candidate_df[
            "candidate_action"
        ]
        == action
    )


    action_raw = (
        candidate_df.loc[
            mask,
            "raw_probability"
        ]
        .to_numpy()
    )


    calibrator = (
        action_calibrators[
            action
        ]
    )


    calibrated = (
        calibrator.predict(
            action_raw
        )
    )


    candidate_df.loc[
        mask,
        "calibrated_probability"
    ] = calibrated


# ============================================================
# PROBABILITY VALIDATION
# ============================================================

invalid_probabilities = (
    (
        candidate_df[
            "calibrated_probability"
        ]
        < 0
    )
    |
    (
        candidate_df[
            "calibrated_probability"
        ]
        > 1
    )
).sum()


print(
    "Invalid calibrated probabilities:",
    invalid_probabilities,
)


if invalid_probabilities > 0:

    raise ValueError(
        "Invalid calibrated probabilities."
    )


print(
    "Calibrated probability range:",
    f"{candidate_df['calibrated_probability'].min():.4f}",
    "to",
    f"{candidate_df['calibrated_probability'].max():.4f}",
)


# ============================================================
# EXPECTED ECONOMIC VALUE
# ============================================================

print(
    "\n========== CALCULATING EXPECTED NET VALUE =========="
)


candidate_df[
    "action_cost"
] = candidate_df[
    "candidate_action"
].map(
    ACTION_COSTS
)


candidate_df[
    "expected_gross_recovery"
] = (
    candidate_df["amount"]
    *
    candidate_df[
        "calibrated_probability"
    ]
)


candidate_df[
    "expected_net_value"
] = (
    candidate_df[
        "expected_gross_recovery"
    ]
    -
    candidate_df["action_cost"]
)


# ============================================================
# SELECT BEST ACTION
# ============================================================

candidate_df = candidate_df.sort_values(
    [
        "failure_id",
        "expected_net_value",
    ],
    ascending=[
        True,
        False,
    ],
)


decisions = (
    candidate_df
    .groupby(
        "failure_id",
        as_index=False,
    )
    .first()
)


# ============================================================
# VALIDATE DECISION COUNT
# ============================================================

print(
    "\n========== DECISION VALIDATION =========="
)


expected_decisions = len(test_df)

actual_decisions = len(decisions)


print(
    "Expected decisions:",
    expected_decisions,
)

print(
    "Actual decisions:",
    actual_decisions,
)


if actual_decisions != expected_decisions:

    raise ValueError(
        "Incorrect number of decisions."
    )


decision_duplicates = (
    decisions[
        "failure_id"
    ]
    .duplicated()
    .sum()
)


print(
    "Duplicate decision IDs:",
    decision_duplicates,
)


if decision_duplicates > 0:

    raise ValueError(
        "Duplicate decisions found."
    )


# ============================================================
# ACTION VALIDATION
# ============================================================

invalid_actions = (
    ~decisions[
        "candidate_action"
    ].isin(ACTIONS)
).sum()


print(
    "Invalid selected actions:",
    invalid_actions,
)


if invalid_actions > 0:

    raise ValueError(
        "Invalid selected action detected."
    )


# ============================================================
# COVERAGE
# ============================================================

test_ids = set(
    test_df[
        "failure_id"
    ]
)


decision_ids = set(
    decisions[
        "failure_id"
    ]
)


missing_decisions = (
    test_ids
    - decision_ids
)


extra_decisions = (
    decision_ids
    - test_ids
)


print(
    "Missing decisions:",
    len(missing_decisions),
)

print(
    "Extra decisions:",
    len(extra_decisions),
)


if missing_decisions:

    raise ValueError(
        "Some test failures have no decision."
    )


if extra_decisions:

    raise ValueError(
        "Unexpected failure IDs in decisions."
    )


# ============================================================
# ECONOMIC SUMMARY
# ============================================================

revenue_at_risk = (
    decisions["amount"]
    .sum()
)


expected_gross = (
    decisions[
        "expected_gross_recovery"
    ]
    .sum()
)


intervention_cost = (
    decisions["action_cost"]
    .sum()
)


expected_net = (
    expected_gross
    -
    intervention_cost
)


expected_recovery_rate = (
    expected_gross
    /
    revenue_at_risk
)


print(
    "\n========== M10H ECONOMIC SUMMARY =========="
)


print(
    f"Revenue at risk: "
    f"₹{revenue_at_risk:,.2f}"
)


print(
    f"Expected gross recovery: "
    f"₹{expected_gross:,.2f}"
)


print(
    f"Intervention cost: "
    f"₹{intervention_cost:,.2f}"
)


print(
    f"Expected NET recovery: "
    f"₹{expected_net:,.2f}"
)


print(
    f"Expected recovery rate: "
    f"{expected_recovery_rate:.2%}"
)


# ============================================================
# ACTION DISTRIBUTION
# ============================================================

print(
    "\n========== SELECTED ACTIONS =========="
)


action_distribution = (
    decisions[
        "candidate_action"
    ]
    .value_counts()
    .reindex(
        ACTIONS,
        fill_value=0,
    )
)


for action, count in (
    action_distribution.items()
):

    print(
        f"{action:28s} {count}"
    )


# ============================================================
# SAMPLE DECISIONS
# ============================================================

print(
    "\n========== SAMPLE DECISIONS =========="
)


sample_columns = [
    "failure_id",
    "failure_reason",
    "amount",
    "candidate_action",
    "raw_probability",
    "calibrated_probability",
    "action_cost",
    "expected_net_value",
]


print(
    decisions[
        sample_columns
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# SAVE OUTPUT
# ============================================================

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


output_columns = [
    "failure_id",
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
    "candidate_action",
    "raw_probability",
    "calibrated_probability",
    "action_cost",
    "expected_gross_recovery",
    "expected_net_value",
]


decisions[
    output_columns
].to_csv(
    OUTPUT_PATH,
    index=False,
)


print(
    "\nOutput saved to:"
)

print(
    OUTPUT_PATH
)


print(
    "\nM10H calibrated policy generation complete. OK"
)