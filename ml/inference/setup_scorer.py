import joblib
import numpy as np

MODEL_PATH = "ml/models/setup_quality.pkl"

_model = None

def load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model

def score_setup(features: dict) -> int:
    model = load_model()
    X = np.array([list(features.values())])
    prob = model.predict_proba(X)[0][1]
    return int(prob * 100)