"""Fleet Inspect — Login (mobile-first)"""
import streamlit as st
from auth.jwt_auth import login, is_authenticated
from utils.mobile import inject_mobile_css

st.set_page_config(
    page_title="Fleet Inspect – Sign In",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed",
)
inject_mobile_css()

if is_authenticated():
    st.switch_page("pages/01_dashboard.py")

st.markdown("""
<style>
  .login-logo  { text-align:center; font-size:3rem; margin-bottom:.25rem; }
  .login-title { text-align:center; font-size:1.4rem; font-weight:700; margin-bottom:.1rem; }
  .login-sub   { text-align:center; color:#888; font-size:.85rem; margin-bottom:1.5rem; }
</style>
<div class="login-logo">🚛</div>
<div class="login-title">Fleet Inspect</div>
<div class="login-sub">Feeding Westchester · Elmsford Warehouse</div>
""", unsafe_allow_html=True)

lang  = st.selectbox("Language / Idioma", ["English", "Español"], label_visibility="collapsed")
is_es = lang == "Español"

email    = st.text_input("Correo electrónico" if is_es else "Email",
                         placeholder="you@feedingwestchester.org")
password = st.text_input("Contraseña" if is_es else "Password", type="password")

if st.button("Iniciar sesión" if is_es else "Sign in",
             use_container_width=True, type="primary"):
    if not email or not password:
        st.warning("Ingrese correo y contraseña." if is_es else "Please enter your email and password.")
    else:
        with st.spinner("Autenticando…" if is_es else "Authenticating…"):
            me = login(email.strip(), password)
        if me:
            st.switch_page("pages/01_dashboard.py")
        else:
            st.error("Correo o contraseña incorrectos." if is_es else "Invalid email or password.")
