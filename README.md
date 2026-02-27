# 🧠 Smart Market Analytics Dashboard

A **subscription-based market analytics and decision-support software** designed to help traders evaluate intraday market structure, risk conditions, and setup quality using transparent, rule-based logic.

> ⚠️ IMPORTANT  
> This platform does **not** provide investment advice, trading recommendations, or trade execution services.  
> It is **not registered with SEBI as an Investment Advisor**.

---

## 🎯 What This Platform Is

Smart Market Analytics Dashboard is a professional-grade **analytics and discipline tool** that helps users:

- Analyze **intraday market structure** (Price, VWAP, ORB, trend)
- Understand **contextual sentiment** using options data and PCR
- Apply **rule-based evaluation** to intraday trade setups
- Practice discipline using an **educational paper trading simulator**
- Review **why** a setup is considered eligible or not using explainable rules
- View **historical setup quality context** using optional ML models

The platform is designed to support **independent decision-making**, not to replace it.

---

## 🚫 What This Platform Is NOT

- ❌ Not a SEBI-registered investment advisory service  
- ❌ Not a stock recommendation or tips platform  
- ❌ Not a trading signal generator  
- ❌ Not an auto-trading or execution system  
- ❌ Not a portfolio management service  
- ❌ Not a prediction or accuracy-based product  

---

## 🧱 High-Level Architecture

```text
User / Browser
      │
      ▼
Streamlit UI (app.py)
      │
      ├── services/        → Market data (Price, Charts, Options, PCR)
      ├── logic/           → Rule-based evaluation & discipline engine
      ├── utils/           → Charts, caching, formatting
      ├── ml/              → Optional advisory ML (schema-locked)
      └── data_service/    → Shared FastAPI backend for live prices
```

**Core design principle:**

> **UI orchestrates · Logic evaluates · ML advises (never decides)**

---

## 📂 Project Structure

```text
smart-dashboard/
│
├── app.py                     # Streamlit UI & orchestration
├── config.py                  # Configuration
│
├── services/                  # Market data services
│   ├── prices.py
│   ├── charts.py
│   ├── options.py
│   ├── nifty_options.py
│   └── market_time.py
│
├── logic/                     # Core rule-based evaluation
│   ├── evaluate_setup.py
│   ├── trade_confidence.py
│   ├── decision.py
│   ├── market_opportunity_scanner.py
│   ├── levels.py
│   └── risk.py
│
├── utils/
│   ├── charts.py
│   ├── cache.py
│   └── formatters.py
│
├── data/
│   ├── watchlist.py
│   └── paper_trades/
│
├── data_service/
│   ├── app.py
│   ├── cache.py
│   └── fetchers/
│       └── prices.py
│
├── ml/
│   ├── features/
│   ├── inference/
│   ├── training/
│   ├── models/
│   └── data/
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🧠 Decision & Evaluation Philosophy

- **Eligibility ≠ Recommendation**
- Rule-based evaluation only
- ML is advisory, never decisive

---

## 💰 Subscription & Legal

Subscription fees are charged **only for access to the software platform**.

This platform is **not registered with SEBI as an Investment Advisor** and does **not provide investment advice**.

---

## 🚀 Getting Started

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 📘 Final Note

> **Process > Outcome**  
> **Discipline > Frequency**  
> **Analytics, not advice**
