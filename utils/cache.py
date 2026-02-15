import streamlit as st

def init_state(defaults):
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
