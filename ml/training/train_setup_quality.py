import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

DATA_FILE = "ml/data/trade_context.csv"
MODEL_PATH = "ml/models/setup_quality.pkl"

# =====================================================
# LOAD DATA
# =====================================================
if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(
        "❌ trade_context.csv not found. Run log_trade_context.py first."
    )

df = pd.read_csv(DATA_FILE)

# =====================================================
# TARGET
# =====================================================
y = df["target"]

# =====================================================
# FEATURE CLEANING & ENCODING
# =====================================================
X = df.drop(
    columns=["target", "timestamp", "symbol"],
    errors="ignore"
)

# --- Encode SIDE ---
if "side" in X.columns:
    X["side"] = X["side"].map({
        "BUY": 1,
        "SELL": -1
    }).fillna(0)

# --- Encode OPTIONS BIAS ---
if "options_bias" in X.columns:
    X["options_bias"] = X["options_bias"].map({
        "BULLISH": 1,
        "NEUTRAL": 0,
        "BEARISH": -1
    }).fillna(0)

# --- Encode STRATEGY (simple ordinal) ---
if "strategy" in X.columns:
    X["strategy"] = X["strategy"].astype("category").cat.codes

# --- Final safety ---
X = X.fillna(0)

# =====================================================
# TRAIN / TEST SPLIT
# =====================================================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y if y.nunique() > 1 else None
)

# =====================================================
# MODEL
# =====================================================
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=6,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# =====================================================
# SAVE MODEL
# =====================================================
os.makedirs("ml/models", exist_ok=True)
joblib.dump(model, MODEL_PATH)

accuracy = model.score(X_test, y_test)

print("✅ Model trained successfully")
print(f"📊 Validation Accuracy: {accuracy:.2%}")
print(f"💾 Model saved to {MODEL_PATH}")