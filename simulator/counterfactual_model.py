import csv
import pickle
from pathlib import Path

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    log_loss,
    classification_report,
)


# ============================================================
# M10F — IMPROVED COUNTERFACTUAL RECOVERY MODEL
# ============================================================
#
# Goals:
# 1. Preserve the existing M10C interface.
# 2. Prevent failure-level data leakage.
# 3. Evaluate on genuinely held-out failures.
# 4. Improve nonlinear action/context learning.
# 5. Do NOT use hidden true probabilities as features.
#
# IMPORTANT:
# The model only sees observable context + candidate action.
#
# The hidden:
#     true_recovery_probability
#
# is NEVER used as an input feature.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

ACTIONS = [
    "RETRY_NOW",
    "WAIT_AND_RETRY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "UPDATE_PAYMENT_METHOD",
]

NUMERIC_FEATURES = [
    "amount",
    "account_age_days",
    "successful_payments",
    "failed_payments",
    "total_payments",
    "payment_success_rate",
    "historical_recovery_rate",
    "engagement_score",
]

CATEGORICAL_FEATURES = [
    "failure_reason",
    "behavior_profile",
    "candidate_action",
]

TARGET = "recovered"

RANDOM_STATE = 42

# Hold out failures, NOT individual rows.
TEST_SIZE = 0.20


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_PATH = (
    DATA_DIR /
    "counterfactual_training.csv"
)

EXPERIENCE_PATH = (
    DATA_DIR /
    "recovery_experiences.csv"
)

MODEL_DIR = (
    DATA_DIR /
    "recovery_probability"
)

MODEL_PATH = (
    MODEL_DIR /
    "counterfactual_model.pkl"
)


# ============================================================
# CSV LOADER
# ============================================================

def load_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Required file not found:\n{path}"
        )

    with open(
        path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


# ============================================================
# LOAD HISTORICAL EXPERIENCES
# ============================================================

def load_observed_experiences():

    experiences = load_csv(
        EXPERIENCE_PATH
    )

    print(
        f"Historical experiences loaded: "
        f"{len(experiences)}"
    )

    return experiences


# ============================================================
# BUILD OBSERVED OUTCOME LOOKUP
# ============================================================

def build_observed_lookup(experiences):

    observed = {}

    for experience in experiences:

        failure_id = (
            experience["failure_id"]
        )

        action = (
            experience["action_taken"]
        )

        key = (
            failure_id,
            action,
        )

        if key not in observed:
            observed[key] = []

        observed[key].append(
            int(
                experience["recovered"]
            )
        )

    return observed


# ============================================================
# BUILD TRAINING DATA
# ============================================================

def build_training_data(
    counterfactual_rows,
    experiences,
):
    """
    Build supervised examples.

    Observable features:
        customer/failure context
        +
        candidate action

    Target:
        observed historical recovery

    Hidden counterfactual probabilities are NOT
    used as model inputs.
    """

    observed = (
        build_observed_lookup(
            experiences
        )
    )

    training_rows = []

    for row in counterfactual_rows:

        failure_id = (
            row["failure_id"]
        )

        action = (
            row["candidate_action"]
        )

        key = (
            failure_id,
            action,
        )

        outcomes = observed.get(
            key
        )

        if not outcomes:
            continue

        for outcome in outcomes:

            training_rows.append(
                {
                    "failure_id":
                        failure_id,

                    "amount":
                        float(
                            row["amount"]
                        ),

                    "account_age_days":
                        float(
                            row[
                                "account_age_days"
                            ]
                        ),

                    "successful_payments":
                        float(
                            row[
                                "successful_payments"
                            ]
                        ),

                    "failed_payments":
                        float(
                            row[
                                "failed_payments"
                            ]
                        ),

                    "total_payments":
                        float(
                            row[
                                "total_payments"
                            ]
                        ),

                    "payment_success_rate":
                        float(
                            row[
                                "payment_success_rate"
                            ]
                        ),

                    "historical_recovery_rate":
                        float(
                            row[
                                "historical_recovery_rate"
                            ]
                        ),

                    "engagement_score":
                        float(
                            row[
                                "engagement_score"
                            ]
                        ),

                    "failure_reason":
                        row[
                            "failure_reason"
                        ],

                    "behavior_profile":
                        row[
                            "behavior_profile"
                        ],

                    "candidate_action":
                        action,

                    TARGET:
                        int(outcome),
                }
            )

    return training_rows


# ============================================================
# VALIDATE TRAINING DATA
# ============================================================

def validate_training_data(rows):

    print(
        "\n========== "
        "M10F TRAINING DATA VALIDATION "
        "=========="
    )

    print(
        f"Training rows: "
        f"{len(rows)}"
    )

    if not rows:

        raise ValueError(
            "No training rows were created."
        )

    # --------------------------------------------------------
    # Target validation
    # --------------------------------------------------------

    invalid_targets = [
        row
        for row in rows
        if row[TARGET] not in {0, 1}
    ]

    print(
        f"Invalid targets: "
        f"{len(invalid_targets)}"
    )

    # --------------------------------------------------------
    # Required feature validation
    # --------------------------------------------------------

    required_fields = (
        NUMERIC_FEATURES
        + CATEGORICAL_FEATURES
        + [TARGET]
    )

    missing_values = 0

    for row in rows:

        for field in required_fields:

            if (
                field not in row
                or row[field] is None
                or row[field] == ""
            ):

                missing_values += 1

    print(
        f"Missing feature values: "
        f"{missing_values}"
    )

    if invalid_targets:

        raise ValueError(
            "Invalid target values detected."
        )

    if missing_values:

        raise ValueError(
            "Missing feature values detected."
        )

    # --------------------------------------------------------
    # Action distribution
    # --------------------------------------------------------

    action_counts = {}

    for row in rows:

        action = (
            row["candidate_action"]
        )

        action_counts[action] = (
            action_counts.get(
                action,
                0
            )
            + 1
        )

    print(
        "\nObserved training examples by action:"
    )

    for action in ACTIONS:

        print(
            f"{action}: "
            f"{action_counts.get(action, 0)}"
        )

    # --------------------------------------------------------
    # Target distribution
    # --------------------------------------------------------

    recoveries = sum(
        row[TARGET]
        for row in rows
    )

    failures = (
        len(rows)
        - recoveries
    )

    recovery_rate = (
        recoveries /
        len(rows)
    )

    print(
        f"\nObserved recoveries: "
        f"{recoveries}"
    )

    print(
        f"Observed failures: "
        f"{failures}"
    )

    print(
        f"Observed recovery rate: "
        f"{recovery_rate:.2%}"
    )

    print(
        "=============================================="
    )


# ============================================================
# BUILD MODEL
# ============================================================

def build_model():

    # --------------------------------------------------------
    # Preprocessing
    # --------------------------------------------------------

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                "passthrough",
                NUMERIC_FEATURES,
            ),

            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    # --------------------------------------------------------
    # Extra Trees
    # --------------------------------------------------------
    #
    # Compared with the previous Random Forest:
    #
    # - more randomized tree construction
    # - strong nonlinear interaction learning
    # - good fit for mixed categorical/numeric features
    # - no changes required to M10C
    #
    # --------------------------------------------------------

    classifier = ExtraTreesClassifier(
        n_estimators=700,
        max_depth=16,
        min_samples_leaf=4,
        max_features="sqrt",
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    # --------------------------------------------------------
    # Complete pipeline
    # --------------------------------------------------------

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),

            (
                "classifier",
                classifier,
            ),
        ]
    )

    return model


# ============================================================
# BUILD DATAFRAME
# ============================================================

def dataframe_from_rows(rows):

    feature_columns = (
        NUMERIC_FEATURES
        + CATEGORICAL_FEATURES
    )

    X = pd.DataFrame(
        [
            {
                feature:
                    row[feature]
                for feature in feature_columns
            }
            for row in rows
        ],
        columns=feature_columns,
    )

    # Convert numeric fields.
    for feature in NUMERIC_FEATURES:

        X[feature] = pd.to_numeric(
            X[feature],
            errors="coerce",
        )

    y = pd.Series(
        [
            int(
                row[TARGET]
            )
            for row in rows
        ],
        name=TARGET,
    )

    return X, y


# ============================================================
# FAILURE-LEVEL HOLDOUT
# ============================================================

def split_by_failure_id(rows):

    """
    Split at failure_id level.

    This is critical.

    Every failure has multiple candidate actions.
    Random row splitting could put:

        FAIL_001
        RETRY_NOW

    in training while:

        FAIL_001
        PAYMENT_LINK

    is in validation.

    That would leak failure-specific information.

    Instead, ALL rows belonging to a failure stay
    in the same split.
    """

    unique_failure_ids = sorted(
        {
            row["failure_id"]
            for row in rows
        }
    )

    if len(unique_failure_ids) < 10:

        raise ValueError(
            "Too few unique failures for "
            "a reliable holdout."
        )

    # Deterministic shuffle.
    rng = pd.Series(
        unique_failure_ids
    ).sample(
        frac=1.0,
        random_state=RANDOM_STATE,
    )

    shuffled_ids = (
        rng.tolist()
    )

    validation_count = max(
        1,
        int(
            len(shuffled_ids)
            * TEST_SIZE
        )
    )

    validation_ids = set(
        shuffled_ids[
            :validation_count
        ]
    )

    train_rows = [
        row
        for row in rows
        if row["failure_id"]
        not in validation_ids
    ]

    validation_rows = [
        row
        for row in rows
        if row["failure_id"]
        in validation_ids
    ]

    return (
        train_rows,
        validation_rows,
        validation_ids,
    )


# ============================================================
# EVALUATE MODEL
# ============================================================

def evaluate_model(
    model,
    X,
    y,
    label,
):

    probabilities = (
        model.predict_proba(X)[:, 1]
    )

    predictions = (
        probabilities >= 0.5
    ).astype(int)

    accuracy = accuracy_score(
        y,
        predictions,
    )

    try:

        roc_auc = roc_auc_score(
            y,
            probabilities,
        )

    except ValueError:

        roc_auc = 0.0

    logloss = log_loss(
        y,
        probabilities,
    )

    print(
        f"\n========== "
        f"{label.upper()} MODEL RESULTS "
        f"=========="
    )

    print(
        f"Examples: "
        f"{len(y)}"
    )

    print(
        f"Feature matrix shape: "
        f"{X.shape}"
    )

    print(
        f"Accuracy: "
        f"{accuracy:.4f}"
    )

    print(
        f"ROC-AUC: "
        f"{roc_auc:.4f}"
    )

    print(
        f"Log loss: "
        f"{logloss:.4f}"
    )

    print(
        "\nClassification report:"
    )

    print(
        classification_report(
            y,
            predictions,
            digits=2,
            zero_division=0,
        )
    )

    return {
        "accuracy": accuracy,
        "roc_auc": roc_auc,
        "log_loss": logloss,
    }


# ============================================================
# ACTION-LEVEL VALIDATION
# ============================================================

def evaluate_action_predictions(
    model,
    validation_rows,
):

    print(
        "\n========== "
        "HELD-OUT ACTION ANALYSIS "
        "=========="
    )

    X_validation, y_validation = (
        dataframe_from_rows(
            validation_rows
        )
    )

    probabilities = (
        model.predict_proba(
            X_validation
        )[:, 1]
    )

    validation_df = (
        X_validation.copy()
    )

    validation_df[
        "actual_recovered"
    ] = y_validation.values

    validation_df[
        "predicted_probability"
    ] = probabilities

    validation_df[
        "failure_id"
    ] = [
        row["failure_id"]
        for row in validation_rows
    ]

    print(
        "\nHeld-out recovery probability "
        "by candidate action:"
    )

    for action in ACTIONS:

        mask = (
            validation_df[
                "candidate_action"
            ]
            == action
        )

        action_rows = (
            validation_df[mask]
        )

        if len(action_rows) == 0:
            continue

        actual_rate = (
            action_rows[
                "actual_recovered"
            ].mean()
        )

        predicted_rate = (
            action_rows[
                "predicted_probability"
            ].mean()
        )

        print(
            f"{action:<25}"
            f" Actual: {actual_rate:.2%}   "
            f"Predicted: {predicted_rate:.2%}"
        )


# ============================================================
# TRAIN MODEL
# ============================================================

def train_model(rows):

    # --------------------------------------------------------
    # Failure-level split
    # --------------------------------------------------------

    (
        train_rows,
        validation_rows,
        validation_ids,
    ) = split_by_failure_id(
        rows
    )

    print(
        "\n========== "
        "M10F FAILURE-LEVEL SPLIT "
        "=========="
    )

    print(
        f"Total unique failures: "
        f"{len(set(row['failure_id'] for row in rows))}"
    )

    print(
        f"Training failures: "
        f"{len(set(row['failure_id'] for row in train_rows))}"
    )

    print(
        f"Held-out failures: "
        f"{len(validation_ids)}"
    )

    print(
        f"Training rows: "
        f"{len(train_rows)}"
    )

    print(
        f"Held-out rows: "
        f"{len(validation_rows)}"
    )

    # --------------------------------------------------------
    # Build matrices
    # --------------------------------------------------------

    X_train, y_train = (
        dataframe_from_rows(
            train_rows
        )
    )

    X_validation, y_validation = (
        dataframe_from_rows(
            validation_rows
        )
    )

    # --------------------------------------------------------
    # Validate matrices
    # --------------------------------------------------------

    if X_train.isnull().any().any():

        raise ValueError(
            "Training feature matrix contains "
            "missing values."
        )

    if X_validation.isnull().any().any():

        raise ValueError(
            "Validation feature matrix contains "
            "missing values."
        )

    if X_train.shape[1] != 11:

        raise ValueError(
            f"Expected 11 features, got "
            f"{X_train.shape[1]}"
        )

    # --------------------------------------------------------
    # Build model
    # --------------------------------------------------------

    model = build_model()

    print(
        "\nTraining improved "
        "counterfactual RecoveryOS model..."
    )

    print(
        f"Training feature matrix: "
        f"{X_train.shape}"
    )

    print(
        f"Held-out feature matrix: "
        f"{X_validation.shape}"
    )

    # --------------------------------------------------------
    # Train ONLY on training failures
    # --------------------------------------------------------

    model.fit(
        X_train,
        y_train,
    )

    # --------------------------------------------------------
    # Training evaluation
    # --------------------------------------------------------

    train_metrics = evaluate_model(
        model=model,
        X=X_train,
        y=y_train,
        label="TRAINING",
    )

    # --------------------------------------------------------
    # Held-out evaluation
    # --------------------------------------------------------

    validation_metrics = evaluate_model(
        model=model,
        X=X_validation,
        y=y_validation,
        label="HELD-OUT",
    )

    # --------------------------------------------------------
    # Action analysis
    # --------------------------------------------------------

    evaluate_action_predictions(
        model=model,
        validation_rows=validation_rows,
    )

    # --------------------------------------------------------
    # Generalization gap
    # --------------------------------------------------------

    roc_gap = (
        train_metrics["roc_auc"]
        -
        validation_metrics["roc_auc"]
    )

    logloss_gap = (
        validation_metrics["log_loss"]
        -
        train_metrics["log_loss"]
    )

    print(
        "\n========== "
        "GENERALIZATION CHECK "
        "=========="
    )

    print(
        f"Training ROC-AUC: "
        f"{train_metrics['roc_auc']:.4f}"
    )

    print(
        f"Held-out ROC-AUC: "
        f"{validation_metrics['roc_auc']:.4f}"
    )

    print(
        f"ROC-AUC gap: "
        f"{roc_gap:.4f}"
    )

    print(
        f"Training log loss: "
        f"{train_metrics['log_loss']:.4f}"
    )

    print(
        f"Held-out log loss: "
        f"{validation_metrics['log_loss']:.4f}"
    )

    print(
        f"Log-loss gap: "
        f"{logloss_gap:.4f}"
    )

    # --------------------------------------------------------
    # Store metadata with model
    # --------------------------------------------------------

    model_bundle = {
        "model": model,
        "feature_version": "M10F_v1",
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "actions": ACTIONS,
        "random_state": RANDOM_STATE,
        "holdout_fraction": TEST_SIZE,
        "train_failure_count": len(
            set(
                row["failure_id"]
                for row in train_rows
            )
        ),
        "validation_failure_count": len(
            validation_ids
        ),
        "held_out_metrics": validation_metrics,
    }

    return model_bundle


# ============================================================
# SAVE MODEL
# ============================================================

def save_model(model_bundle):

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        MODEL_PATH,
        "wb",
    ) as file:

        pickle.dump(
            model_bundle,
            file,
        )

    return MODEL_PATH


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== "
        "M10F IMPROVED COUNTERFACTUAL MODEL "
        "=========="
    )

    # --------------------------------------------------------
    # Load counterfactual dataset
    # --------------------------------------------------------

    counterfactual_rows = load_csv(
        INPUT_PATH
    )

    print(
        f"Counterfactual rows loaded: "
        f"{len(counterfactual_rows)}"
    )

    # --------------------------------------------------------
    # Load historical experiences
    # --------------------------------------------------------

    experiences = (
        load_observed_experiences()
    )

    # --------------------------------------------------------
    # Build training examples
    # --------------------------------------------------------

    training_rows = (
        build_training_data(
            counterfactual_rows,
            experiences,
        )
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_training_data(
        training_rows
    )

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    model_bundle = train_model(
        training_rows
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = save_model(
        model_bundle
    )

    print(
        f"\nModel saved to:"
        f"\n{output_path}"
    )

    print(
        "\nM10F improved model "
        "training complete. ✅"
    )

    print(
        "\nIMPORTANT:"
        "\nHeld-out metrics above are the "
        "generalization evidence."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()