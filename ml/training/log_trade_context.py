import os
import pandas as pd
from datetime import datetime

PAPER_TRADES_DIR = "data/paper_trades"
OUTPUT_DIR = "ml/data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "trade_context.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

rows = []

if not os.path.exists(PAPER_TRADES_DIR):
    print("❌ No paper_trades directory found.")
    exit()

for fname in os.listdir(PAPER_TRADES_DIR):
    if not fname.endswith(".csv"):
        continue

    path = os.path.join(PAPER_TRADES_DIR, fname)

    try:
        df = pd.read_csv(path)
    except Exception:
        continue

    for _, r in df.iterrows():
        if r.get("Status") != "CLOSED":
            continue

        rows.append({
            "symbol": r.get("Symbol"),
            "side": r.get("Side"),
            "qty": r.get("Qty", 1),
            "pnl": r.get("PnL", 0),
            "strategy": r.get("Strategy"),
            "options_bias": r.get("Options Bias"),
            "hour": (
                int(str(r.get("Entry Time")).split(":")[0])
                if isinstance(r.get("Entry Time"), str)
                else None
            ),
            "target": 1 if r.get("PnL", 0) > 0 else 0,
            "timestamp": datetime.now().isoformat()
        })

if not rows:
    print("⚠️ No CLOSED trades found. Close at least one paper trade.")
    exit()

df_out = pd.DataFrame(rows)
df_out.to_csv(OUTPUT_FILE, index=False)

print(f"✅ Trade context saved to {OUTPUT_FILE}")