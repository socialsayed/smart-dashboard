"""
Training pipeline for setup quality ML model.

SCHEMA RULE:
- Must use FEATURE_COLUMNS
- Feature order is LOCKED
"""

import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier

from ml.features.schema import FEATURE_COLUMNS, SCHEMA_VERSION
from ml.features.feature_builder import build_feature_vector


DATA_PATH = "ml/data/trade_context.csv"
MODEL_PATH = "ml/models/setup_quality.pkl"


def train_model():
    df = pd.read_csv(DATA_PATH)

    # Ensure all required features exist
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    X = []
    y = []

    for _, row in df.iterrows():
        features = {col: row[col] for col in FEATURE_COLUMNS}
        X.append(build_feature_vector(features))
        y.append(int(row.get("outcome", 0)))

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(
        f"✅ Model trained successfully | "
        f"Features={len(FEATURE_COLUMNS)} | "
        f"Schema v{SCHEMA_VERSION}"
    )


if __name__ == "__main__":
    train_model()