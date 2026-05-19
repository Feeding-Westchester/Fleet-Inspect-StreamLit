"""
Fleet Inspect — Main Entry Point
Streamlit multi-page app. This file is the root; all pages live in /pages/.
"""
import streamlit as st
from auth.jwt_auth import is_authenticated

st.set_page_config(
    page_title="Fleet Inspect",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

if is_authenticated():
    st.switch_page("pages/01_dashboard.py")
else:
    st.switch_page("pages/00_login.py")
