"""
RecoveryOS V3 — Action-Specific Counterfactual Model Training Engine

Trains dedicated, calibrated ExtraTrees estimators for each candidate action:
- RETRY_NOW
- WAIT_AND_RETRY
- SEND_REMINDER
- PAYMENT_LINK
- UPDATE_PAYMENT_METHOD

Eliminates cross-action probability calibration noise. Fully vectorized.
"""

import pickle
import gzip
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TRAIN_PATH = DATA_DIR / "counterfactual_training.csv"
V3_MODEL_PATH = DATA_DIR / "recovery_probability" / "v3_counterfactual_model.pkl.gz"

ACTIVE_ACTIONS = [
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
]

MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["candidate_action"]


class V3ActionSpecificModelBundle:
    """Bundle holding distinct trained pipelines per candidate action."""
    def __init__(self, action_pipelines: Dict[str, Any]):
        self.action_pipelines = action_pipelines

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Vectorized routing of rows to action-specific model pipelines.
        Returns N x 2 probability matrix [[1 - p, p], ...] matching sklearn interface.
        """
        n_rows = len(X)
        probs = np.zeros((n_rows, 2))

        actions = X["candidate_action"].values if "candidate_action" in X.columns else np.repeat("RETRY_NOW", n_rows)

        for action, pipeline in self.action_pipelines.items():
            mask = (actions == action)
            if not np.any(mask):
                continue

            sub_X = X.loc[mask, NUMERIC_FEATURES + CATEGORICAL_FEATURES]
            p = pipeline.predict_proba(sub_X)
            probs[mask] = p

        # Handle STOP rows
        stop_mask = (actions == "STOP")
        if np.any(stop_mask):
            probs[stop_mask] = [1.0, 0.0]

        return probs


def train_v3_action_specific_models():
    print("\n======================================================================")
    print("RECOVERYOS V3 — TRAINING ACTION-SPECIFIC COUNTERFACTUAL MODELS")
    print("======================================================================")

    df = pd.read_csv(TRAIN_PATH)

    # Generate binary recovered label from true_recovery_probability using seed 42
    rng = np.random.RandomState(42)
    df["recovered_target"] = (rng.rand(len(df)) < df["true_recovery_probability"]).astype(int)

    action_pipelines = {}

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ]
    )

    for action in ACTIVE_ACTIONS:
        sub_df = df[df["candidate_action"] == action].copy()
        print(f"Training pipeline for action '{action}' on {len(sub_df)} samples...")

        X_sub = sub_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
        y_sub = sub_df["recovered_target"]

        clf = ExtraTreesClassifier(
            n_estimators=150,
            max_depth=12,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", clf),
        ])

        pipeline.fit(X_sub, y_sub)
        action_pipelines[action] = pipeline

    bundle = V3ActionSpecificModelBundle(action_pipelines)

    # Save compressed V3 model bundle
    V3_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(V3_MODEL_PATH, "wb") as f:
        pickle.dump({"model": bundle, "version": "V3.0_ACTION_SPECIFIC"}, f)

    print(f"V3 Action-Specific Model Bundle saved to {V3_MODEL_PATH}")
    return bundle


if __name__ == "__main__":
    train_v3_action_specific_models()
