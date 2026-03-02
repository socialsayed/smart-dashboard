"""
ML Setup Quality Inference (Schema-Safe & Performance-Tuned)

RULES:
- Uses locked feature schema
- Model is loaded ONCE per session (cached resource)
- Advisory only
- NEVER crashes the app
"""

import pickle
import numpy as np
import streamlit as st
from typing import Dict

from ml.features.feature_builder import build_feature_vector
from ml.features.schema import FEATURE_COLUMNS, SCHEMA_VERSION


MODEL_PATH = "ml/models/setup_quality.pkl"


# =====================================================
# 🔒 MODEL LOADER (STREAMLIT-AWARE, MEMORY SAFE)
# =====================================================
@st.cache_resource(show_spinner=False)
def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


# =====================================================
# 🤖 ML SCORING (ADVISORY ONLY)
# =====================================================
def score_setup(features: Dict) -> float | None:
    """
    Returns setup quality score between 0 and 1.
    Returns None if inference fails.
    """

    try:
        model = load_model()

        vector = build_feature_vector(features)
        X = np.array([vector], dtype=float)

        score = model.predict_proba(X)[0][1]
        return float(score)

    except Exception:
        return None