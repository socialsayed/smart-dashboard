import streamlit as st


def render_layout_header():
    """
    Layout bootstrap.
    Moved from app.py without modification.
    """

    # =====================================================
    # PAGE CONFIG
    # =====================================================
    st.set_page_config(
        page_title="Smart Market Analytics — Intraday Decision Support",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # =====================================================
    # SAFE HEADER STYLING
    # =====================================================
    st.markdown(
        """
        <style>
        header[data-testid="stHeader"] {
            background: transparent !important;
            border-bottom: none !important;
        }

        header[data-testid="stHeader"] {
            height: auto !important;
        }

        [data-testid="stMainBlockContainer"] {
            padding-top: 0.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # ALERT CONTRAST FIX
    # =====================================================
    st.markdown(
        """
        <style>
        @media (prefers-color-scheme: dark) {
            .stAlert, .stAlertInfo, .stAlert *, .stAlertInfo *, #regulatory-box {
                color: #fff !important;
                background-color: #333 !important;
            }
        }
        @media (prefers-color-scheme: light) {
            .stAlert, .stAlertInfo, .stAlert *, .stAlertInfo *, #regulatory-box {
                color: #000 !important;
                background-color: #eee !important;
            }
        }
        .stAlert, .stAlertInfo, #regulatory-box {
            color: inherit !important;
            background-color: inherit !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )