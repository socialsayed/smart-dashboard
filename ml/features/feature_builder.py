"""
Feature builder for ML inference & training.

STRICT RULE:
- Must follow FEATURE_COLUMNS order
- Missing values must degrade gracefully
"""

from typing import Dict, List
import numpy as np

from ml.features.schema import FEATURE_COLUMNS


def build_feature_vector(features: Dict) -> List[float]:
    """
    Converts feature dict → ordered list (schema-safe).

    Missing features:
    - Filled with 0.0
    - NEVER raises KeyError
    """

    vector = []

    for col in FEATURE_COLUMNS:
        val = features.get(col)

        if val is None:
            vector.append(0.0)
        else:
            try:
                vector.append(float(val))
            except Exception:
                vector.append(0.0)

    return vector