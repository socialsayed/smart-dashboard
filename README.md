## Application Flow (Color-Coded)

🟦 UI  
🟩 Logic  
🟧 Data  

```mermaid
(paste diagram here)

flowchart TD
    %% ---------- UI ----------
    A([START]):::ui --> B[Initialize Streamlit App]:::ui
    B --> C[Initialize Session State]:::ui
    C --> D[Read Sidebar Inputs<br/>(Index, Stock, Risk, Strategy)]:::ui

    %% ---------- DATA ----------
    D --> E[Load config.py]:::data
    E --> F[Fetch Live Price<br/>(Cache → NSE → Yahoo)]:::data
    F --> G[Fetch Intraday Data<br/>(3-Minute Candles)]:::data

    %% ---------- LOGIC ----------
    G --> H[Check Market Status]:::logic

    %% ---------- DECISION ----------
    H -->|Market Closed| I[Show Market Closed Message]:::ui
    H -->|Market Open| J[Calculate Indicators]:::logic

    %% ---------- LOGIC DETAILS ----------
    J --> J1[Compute VWAP]:::logic
    J --> J2[Compute ORB High / Low]:::logic
    J --> J3[Compute Volume]:::logic

    J1 --> K
    J2 --> K
    J3 --> K

    %% ---------- UI ----------
    K[Render Intraday Chart]:::ui
    K --> L[Show Strategy Context<br/>• Why this signal?<br/>• Beginner Help]:::ui

    %% ---------- DATA ----------
    L --> M[Generate Daily Watchlist]:::data
    M --> N[Get Options Sentiment (PCR)]:::data

    %% ---------- LOGIC ----------
    N --> O[Calculate Support & Resistance]:::logic
    O --> P[Run Trade Decision Engine]:::logic

    %% ---------- DECISION ----------
    P -->|Trade Allowed| Q[Show Trade Allowed Banner]:::ui
    P -->|Trade Blocked| R[Show Trade Blocked Reason]:::ui

    %% ---------- UI ----------
    Q --> S[Render Trade History & PnL]:::ui
    R --> S
    S --> T[Auto-Refresh Timer Check]:::ui
    T -->|Time Elapsed| B
    T -->|No Refresh| U([END]):::ui

    %% ---------- STYLES ----------
    classDef ui fill:#E3F2FD,stroke:#1565C0,stroke-width:1.5px,color:#0D47A1;
    classDef logic fill:#E8F5E9,stroke:#2E7D32,stroke-width:1.5px,color:#1B5E20;
    classDef data fill:#FFF3E0,stroke:#EF6C00,stroke-width:1.5px,color:#E65100;
