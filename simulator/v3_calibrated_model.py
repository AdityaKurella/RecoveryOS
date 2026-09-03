"""
RecoveryOS V3 — Calibrated Counterfactual Probability Estimator

Trains a Probability-Calibrated ExtraTrees Classifier using CalibratedClassifierCV
to improve probability calibration and net value ranking.
"""

import pickle
import gzip
from pathlib import Path
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TRAIN_PATH = DATA_DIR / "counterfactual_training.csv"
V3_CALIBRATED_MODEL_PATH = DATA_DIR / "recovery_probability" / "v3_calibrated_model.pkl.gz"

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

MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def train_v3_calibrated_model():
    print("\n======================================================================")
    print("RECOVERYOS V3 — TRAINING CALIBRATED COUNTERFACTUAL MODEL")
    print("======================================================================")

    df = pd.read_csv(TRAIN_PATH)

    # Generate binary target using seed 42
    rng = np.random.RandomState(42)
    df["recovered_target"] = (rng.rand(len(df)) < df["true_recovery_probability"]).astype(int)

    X = df[MODEL_FEATURES]
    y = df["recovered_target"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ]
    )

    clf = ExtraTreesClassifier(
        n_estimators=700,
        max_depth=16,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    # Calibrate probability predictions using sigmoid calibration
    calibrated_clf = CalibratedClassifierCV(estimator=clf, method="sigmoid", cv=3)

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", calibrated_clf),
    ])

    print("Fitting Calibrated Classifier Pipeline...")
    pipeline.fit(X, y)

    V3_CALIBRATED_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(V3_CALIBRATED_MODEL_PATH, "wb") as f:
        pickle.dump({"model": pipeline, "version": "V3.0_CALIBRATED_EXTRATREES"}, f)

    print(f"V3 Calibrated Model saved to {V3_CALIBRATED_MODEL_PATH}")
    return pipeline


if __name__ == "__main__":
    train_v3_calibrated_model()
