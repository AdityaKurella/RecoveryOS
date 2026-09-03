import pickle
from pathlib import Path

import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import log_loss, roc_auc_score


# ============================================================
# M10G — PROBABILITY CALIBRATION
# ============================================================
#
# Goal:
# Improve the reliability of M10F recovery probabilities
# without touching the untouched M10D benchmark.
#
# Important:
# - Original CSV files are NOT modified.
# - M10D's 559 failures are NOT used for calibration.
# - Repeated experience observations are collapsed to one
#   observation per failure/action pair.
# - Calibration split happens at FAILURE level.
#
# ============================================================


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


COUNTERFACTUAL_PATH = (
    DATA_DIR / "counterfactual_training.csv"
)

EXPERIENCES_PATH = (
    DATA_DIR / "recovery_experiences.csv"
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


ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
]


FEATURES = [
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
    "\n========== M10G PROBABILITY CALIBRATION =========="
)


# ============================================================
# LOAD DATA
# ============================================================

counterfactual_df = pd.read_csv(
    COUNTERFACTUAL_PATH
)

experiences_df = pd.read_csv(
    EXPERIENCES_PATH
)


print(
    f"Counterfactual rows loaded: "
    f"{len(counterfactual_df)}"
)

print(
    f"Historical experiences loaded: "
    f"{len(experiences_df)}"
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



if isinstance(model_bundle, dict):

    model = model_bundle["model"]

    print(
        "Model format: M10F bundle"
    )

    print(
        "Feature version:",
        model_bundle.get(
            "feature_version",
            "unknown",
        ),
    )

else:

    model = model_bundle

    print(
        "Model format: legacy model"
    )


# ============================================================
# SOURCE SCHEMA VALIDATION
# ============================================================

print(
    "\n========== VALIDATING SOURCE SCHEMAS =========="
)


required_counterfactual = [
    "failure_id",
    "candidate_action",
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


required_experience = [
    "failure_id",
    "action_taken",
    "recovered",
]


missing_counterfactual = [
    column
    for column in required_counterfactual
    if column not in counterfactual_df.columns
]


missing_experience = [
    column
    for column in required_experience
    if column not in experiences_df.columns
]


if missing_counterfactual:

    raise ValueError(
        "Missing counterfactual columns: "
        f"{missing_counterfactual}"
    )


if missing_experience:

    raise ValueError(
        "Missing experience columns: "
        f"{missing_experience}"
    )


print(
    "Counterfactual schema: PASS"
)

print(
    "Experience schema: PASS"
)


# ============================================================
# NORMALIZE ACTION COLUMN
# ============================================================

experiences_df = experiences_df.rename(
    columns={
        "action_taken": "candidate_action"
    }
)


# ============================================================
# CHECK ORIGINAL EXPERIENCE STRUCTURE
# ============================================================

print(
    "\n========== CHECKING EXPERIENCE REPETITIONS =========="
)


original_pair_counts = (
    experiences_df
    .groupby(
        [
            "failure_id",
            "candidate_action",
        ]
    )
    .size()
)


print(
    "Unique failure/action pairs:",
    len(original_pair_counts),
)

print(
    "Total experience rows:",
    len(experiences_df),
)

print(
    "Maximum repetitions:",
    original_pair_counts.max(),
)


# ============================================================
# COLLAPSE REPEATED OBSERVATIONS
# ============================================================
#
# Every failure/action pair currently appears twice.
#
# We do not modify the original CSV.
#
# For calibration, one observation per pair prevents the
# repeated identical observation from receiving double weight.
#
# ============================================================

experience_calibration = (
    experiences_df[
        [
            "failure_id",
            "candidate_action",
            "recovered",
        ]
    ]
    .drop_duplicates(
        subset=[
            "failure_id",
            "candidate_action",
        ],
        keep="first",
    )
    .copy()
)


print(
    "Unique experience observations for calibration:",
    len(experience_calibration),
)


# ============================================================
# MERGE COUNTERFACTUAL FEATURES + OBSERVED OUTCOME
# ============================================================

print(
    "\n========== BUILDING CALIBRATION DATA =========="
)


training_df = counterfactual_df.merge(
    experience_calibration,
    on=[
        "failure_id",
        "candidate_action",
    ],
    how="inner",
)


print(
    f"Calibration rows: "
    f"{len(training_df)}"
)


# ============================================================
# DUPLICATE VALIDATION
# ============================================================

duplicate_pairs = (
    training_df[
        [
            "failure_id",
            "candidate_action",
        ]
    ]
    .duplicated()
    .sum()
)


print(
    "Duplicate failure/action pairs after collapse:",
    duplicate_pairs,
)


if duplicate_pairs > 0:

    raise ValueError(
        "Duplicate failure/action pairs remain."
    )


# ============================================================
# COVERAGE VALIDATION
# ============================================================

counterfactual_pairs = set(
    zip(
        counterfactual_df["failure_id"],
        counterfactual_df["candidate_action"],
    )
)


calibration_pairs = set(
    zip(
        training_df["failure_id"],
        training_df["candidate_action"],
    )
)


missing_pairs = (
    counterfactual_pairs
    - calibration_pairs
)


extra_pairs = (
    calibration_pairs
    - counterfactual_pairs
)


print(
    "Missing calibration pairs:",
    len(missing_pairs),
)

print(
    "Extra calibration pairs:",
    len(extra_pairs),
)


if missing_pairs:

    raise ValueError(
        "Some counterfactual pairs are missing "
        "from calibration data."
    )


if extra_pairs:

    raise ValueError(
        "Unexpected calibration pairs found."
    )


# ============================================================
# TARGET VALIDATION
# ============================================================

print(
    "\n========== VALIDATING RECOVERY TARGET =========="
)


training_df["recovered"] = pd.to_numeric(
    training_df["recovered"],
    errors="coerce",
)


invalid_targets = (
    training_df["recovered"]
    .isna()
    .sum()
)


print(
    "Missing/invalid targets:",
    invalid_targets,
)


if invalid_targets > 0:

    raise ValueError(
        "Invalid recovery targets found."
    )


training_df["recovered"] = (
    training_df["recovered"]
    .astype(int)
)


invalid_binary = (
    ~training_df["recovered"]
    .isin([0, 1])
).sum()


print(
    "Non-binary targets:",
    invalid_binary,
)


if invalid_binary > 0:

    raise ValueError(
        "Recovery target is not binary."
    )


# ============================================================
# FAILURE-LEVEL CALIBRATION SPLIT
# ============================================================

print(
    "\n========== CALIBRATION SPLIT =========="
)


unique_failures = sorted(
    training_df[
        "failure_id"
    ]
    .drop_duplicates()
    .tolist()
)


split_index = int(
    len(unique_failures) * 0.80
)


calibration_train_failures = (
    unique_failures[:split_index]
)

calibration_validation_failures = (
    unique_failures[split_index:]
)


calibration_train_df = training_df[
    training_df[
        "failure_id"
    ].isin(
        calibration_train_failures
    )
].copy()


calibration_validation_df = training_df[
    training_df[
        "failure_id"
    ].isin(
        calibration_validation_failures
    )
].copy()


print(
    "Total failures:",
    len(unique_failures),
)

print(
    "Calibration-fit failures:",
    len(calibration_train_failures),
)

print(
    "Calibration-validation failures:",
    len(calibration_validation_failures),
)

print(
    "Calibration-fit rows:",
    len(calibration_train_df),
)

print(
    "Calibration-validation rows:",
    len(calibration_validation_df),
)


# ============================================================
# GENERATE M10F PREDICTIONS
# ============================================================

print(
    "\n========== GENERATING M10F PREDICTIONS =========="
)


X_train = calibration_train_df[
    FEATURES
]

y_train = calibration_train_df[
    "recovered"
]


X_valid = calibration_validation_df[
    FEATURES
]

y_valid = calibration_validation_df[
    "recovered"
]


raw_train_prob = model.predict_proba(
    X_train
)[:, 1]


raw_valid_prob = model.predict_proba(
    X_valid
)[:, 1]


# ============================================================
# PRE-CALIBRATION METRICS
# ============================================================

print(
    "\n========== PRE-CALIBRATION VALIDATION =========="
)


raw_auc = roc_auc_score(
    y_valid,
    raw_valid_prob,
)


raw_logloss = log_loss(
    y_valid,
    raw_valid_prob,
)


print(
    f"ROC-AUC: {raw_auc:.4f}"
)

print(
    f"Log loss: {raw_logloss:.4f}"
)


# ============================================================
# GLOBAL ISOTONIC CALIBRATION
# ============================================================

print(
    "\n========== FITTING GLOBAL CALIBRATION =========="
)


global_calibrator = IsotonicRegression(
    y_min=0.001,
    y_max=0.999,
    out_of_bounds="clip",
)


global_calibrator.fit(
    raw_train_prob,
    y_train,
)


calibrated_valid_prob = (
    global_calibrator.predict(
        raw_valid_prob
    )
)


# ============================================================
# POST-CALIBRATION METRICS
# ============================================================

print(
    "\n========== POST-CALIBRATION VALIDATION =========="
)


calibrated_auc = roc_auc_score(
    y_valid,
    calibrated_valid_prob,
)


calibrated_logloss = log_loss(
    y_valid,
    calibrated_valid_prob,
)


print(
    f"ROC-AUC: {calibrated_auc:.4f}"
)

print(
    f"Log loss: {calibrated_logloss:.4f}"
)


logloss_improvement = (
    raw_logloss
    - calibrated_logloss
)


print(
    "\nLog-loss improvement:"
)

print(
    f"{logloss_improvement:+.4f}"
)


# ============================================================
# ACTION-SPECIFIC CALIBRATION
# ============================================================

print(
    "\n========== ACTION-SPECIFIC CALIBRATION =========="
)


action_calibrators = {}

action_metrics = []


for action in ACTIONS:

    train_mask = (
        calibration_train_df[
            "candidate_action"
        ]
        == action
    )

    valid_mask = (
        calibration_validation_df[
            "candidate_action"
        ]
        == action
    )


    action_train_prob = (
        raw_train_prob[
            train_mask.values
        ]
    )

    action_train_y = (
        y_train[
            train_mask.values
        ]
    )


    action_valid_prob = (
        raw_valid_prob[
            valid_mask.values
        ]
    )

    action_valid_y = (
        y_valid[
            valid_mask.values
        ]
    )


    print(
        f"\n{action}"
    )

    print(
        f"  Fit rows: "
        f"{len(action_train_prob)}"
    )

    print(
        f"  Validation rows: "
        f"{len(action_valid_prob)}"
    )


    if (
        len(action_train_prob) < 50
        or len(action_valid_prob) < 10
    ):

        print(
            "  Status: insufficient data"
        )

        continue


    if action_train_y.nunique() < 2:

        print(
            "  Status: only one target class"
        )

        continue


    calibrator = IsotonicRegression(
        y_min=0.001,
        y_max=0.999,
        out_of_bounds="clip",
    )


    calibrator.fit(
        action_train_prob,
        action_train_y,
    )


    calibrated_action_prob = (
        calibrator.predict(
            action_valid_prob
        )
    )


    raw_action_logloss = log_loss(
        action_valid_y,
        action_valid_prob,
    )


    calibrated_action_logloss = (
        log_loss(
            action_valid_y,
            calibrated_action_prob,
        )
    )


    action_calibrators[
        action
    ] = calibrator


    action_metrics.append(
        {
            "action": action,
            "validation_rows":
                len(action_valid_prob),
            "raw_log_loss":
                raw_action_logloss,
            "calibrated_log_loss":
                calibrated_action_logloss,
        }
    )


    print(
        f"  Raw log loss: "
        f"{raw_action_logloss:.4f}"
    )

    print(
        f"  Calibrated log loss: "
        f"{calibrated_action_logloss:.4f}"
    )


# ============================================================
# ACTION-LEVEL BIAS
# ============================================================

print(
    "\n========== CALIBRATION BIAS ANALYSIS =========="
)


for action in ACTIONS:

    mask = (
        calibration_validation_df[
            "candidate_action"
        ]
        == action
    )


    if mask.sum() == 0:
        continue


    actual_rate = (
        y_valid[
            mask.values
        ].mean()
    )


    raw_mean = (
        raw_valid_prob[
            mask.values
        ].mean()
    )


    calibrated_mean = (
        calibrated_valid_prob[
            mask.values
        ].mean()
    )


    print(
        f"{action:28s} "
        f"actual={actual_rate:.2%} "
        f"raw={raw_mean:.2%} "
        f"calibrated={calibrated_mean:.2%}"
    )


# ============================================================
# SAVE CALIBRATION BUNDLE
# ============================================================

calibration_bundle = {

    "feature_version":
        "M10G_v1",

    "method":
        "isotonic",

    "global_calibrator":
        global_calibrator,

    "action_calibrators":
        action_calibrators,

    "actions":
        ACTIONS,

    "features":
        FEATURES,

    "calibration_fit_failure_count":
        len(calibration_train_failures),

    "calibration_validation_failure_count":
        len(calibration_validation_failures),

    "validation_metrics": {

        "raw_roc_auc":
            raw_auc,

        "raw_log_loss":
            raw_logloss,

        "calibrated_roc_auc":
            calibrated_auc,

        "calibrated_log_loss":
            calibrated_logloss,

    },

    "action_metrics":
        action_metrics,
}


CALIBRATION_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


with open(
    CALIBRATION_PATH,
    "wb",
) as f:

    pickle.dump(
        calibration_bundle,
        f,
    )


# ============================================================
# FINAL REPORT
# ============================================================

print(
    "\n========== M10G SUMMARY =========="
)

print(
    f"Raw validation ROC-AUC: "
    f"{raw_auc:.4f}"
)

print(
    f"Calibrated validation ROC-AUC: "
    f"{calibrated_auc:.4f}"
)

print(
    f"Raw validation log loss: "
    f"{raw_logloss:.4f}"
)

print(
    f"Calibrated validation log loss: "
    f"{calibrated_logloss:.4f}"
)

print(
    f"Log-loss improvement: "
    f"{logloss_improvement:+.4f}"
)

print(
    "\nCalibration bundle saved to:"
)

print(
    CALIBRATION_PATH
)

print(
    "\nM10G calibration complete. OK"
)