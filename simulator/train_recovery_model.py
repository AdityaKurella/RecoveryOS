import csv
import pickle
from pathlib import Path

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


RANDOM_STATE = 42


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
    "action_taken",
]


def load_experiences():
    path = (
        Path(__file__).parent.parent
        / "data"
        / "recovery_experiences.csv"
    )

    with open(
        path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def build_dataset(experiences):

    rows = []

    targets = []

    for experience in experiences:

        row = {}

        for feature in NUMERIC_FEATURES:
            row[feature] = float(
                experience[feature]
            )

        for feature in CATEGORICAL_FEATURES:
            row[feature] = experience[
                feature
            ]

        rows.append(row)

        targets.append(
            int(experience["recovered"])
        )

    # THIS IS THE IMPORTANT FIX.
    # Convert list of dictionaries into
    # a real 2D DataFrame.
    X = pd.DataFrame(rows)

    y = pd.Series(
        targets,
        name="recovered",
    )

    return X, y


def build_model():

    numeric_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    classifier = LogisticRegression(
        max_iter=2000,
        random_state=RANDOM_STATE,
    )

    model = Pipeline(
        [
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


def validate_dataset(
    experiences,
    X,
    y,
):

    print(
        "\n========== TRAINING DATA VALIDATION =========="
    )

    print(
        f"Experiences loaded: {len(experiences)}"
    )

    print(
        f"Feature rows: {len(X)}"
    )

    print(
        f"Feature columns: {len(X.columns)}"
    )

    print(
        f"Target rows: {len(y)}"
    )

    print(
        f"Feature matrix shape: {X.shape}"
    )

    print(
        f"Invalid target values: "
        f"{sum(value not in [0, 1] for value in y)}"
    )

    print(
        f"Missing feature values: "
        f"{int(X.isna().sum().sum())}"
    )

    print(
        "\nFeatures:"
    )

    for column in X.columns:
        print(f"  {column}")

    print(
        "=============================================="
    )


def evaluate_model(
    model,
    X,
    y,
):

    probabilities = model.predict_proba(
        X
    )[:, 1]

    predictions = (
        probabilities >= 0.5
    ).astype(int)

    accuracy = accuracy_score(
        y,
        predictions,
    )

    auc = roc_auc_score(
        y,
        probabilities,
    )

    loss = log_loss(
        y,
        probabilities,
    )

    print(
        "\n========== MODEL TRAINING RESULTS =========="
    )

    print(
        f"Training examples: {len(X)}"
    )

    print(
        f"Observed recoveries: {int(y.sum())}"
    )

    print(
        f"Observed failures: "
        f"{len(y) - int(y.sum())}"
    )

    print(
        f"Training recovery rate: {y.mean():.2%}"
    )

    print(
        f"Training accuracy: {accuracy:.4f}"
    )

    print(
        f"Training ROC-AUC: {auc:.4f}"
    )

    print(
        f"Training log loss: {loss:.4f}"
    )

    print(
        "\nClassification report:"
    )

    print(
        classification_report(
            y,
            predictions,
            zero_division=0,
        )
    )

    print(
        "Sample predicted probabilities:"
    )

    for i, probability in enumerate(
        probabilities[:10],
        start=1,
    ):

        print(
            f"  Example {i}: "
            f"{probability:.2%}"
        )

    print(
        "============================================"
    )


def save_model(model):

    path = (
        Path(__file__).parent.parent
        / "data"
        / "recovery_probability_model.pkl"
    )

    with open(
        path,
        "wb",
    ) as file:

        pickle.dump(
            model,
            file,
        )

    return path


def main():

    experiences = load_experiences()

    X, y = build_dataset(
        experiences
    )

    validate_dataset(
        experiences,
        X,
        y,
    )

    print(
        "\nTraining RecoveryOS probability model..."
    )

    model = build_model()

    model.fit(
        X,
        y,
    )

    evaluate_model(
        model,
        X,
        y,
    )

    model_path = save_model(
        model
    )

    print(
        f"\nModel saved to: {model_path}"
    )

    print(
        "\nM9B training complete. ✅"
    )


if __name__ == "__main__":
    main()