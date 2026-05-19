"""
Fleet Inspect — Authentication & Authorization
Replaces Supabase Auth with JWT (PyJWT) + bcrypt + Snowflake USERS table.

Session state keys used throughout the app:
    st.session_state["user"]         — dict: id, email, first_name, last_name, preferred_lang
    st.session_state["permissions"]  — set of permission code strings
    st.session_state["role_name"]    — primary role name string
    st.session_state["site_id"]      — active site id
"""

import jwt
import bcrypt
import streamlit as st
from datetime import datetime, timezone, timedelta
from db.connection import query_one, query_many, execute

# ── Config ────────────────────────────────────────────────────
JWT_SECRET = st.secrets.get("jwt", {}).get("secret", "change-me-in-prod")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = 60
REFRESH_TOKEN_TTL_DAYS = 7


# ── Token creation ────────────────────────────────────────────

def _make_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MIN),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _make_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Decode and verify a JWT. Returns payload dict or None on failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Login / logout ────────────────────────────────────────────

def login(email: str, password: str) -> dict | None:
    """
    Authenticate user. On success populates st.session_state and returns
    the 'me' context dict. Returns None on bad credentials.
    """
    user = query_one(
        "SELECT * FROM USERS WHERE LOWER(email) = LOWER(%s) AND active = TRUE",
        (email,)
    )
    if not user:
        return None

    if not bcrypt.checkpw(password.encode(), user["PASSWORD_HASH"].encode()):
        return None

    # Update last login
    execute(
        "UPDATE USERS SET last_login_at = CURRENT_TIMESTAMP() WHERE id = %s",
        (user["ID"],)
    )

    me = _build_me_context(user)
    _populate_session(user, me)
    return me


def logout():
    """Clear session state."""
    for key in ["user", "permissions", "role_name", "site_id", "access_token"]:
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    return "user" in st.session_state and st.session_state["user"] is not None


def require_auth():
    """Call at the top of any page that requires login. Redirects to login if not authed."""
    if not is_authenticated():
        st.switch_page("pages/00_login.py")


# ── Permissions ───────────────────────────────────────────────

def _build_me_context(user: dict) -> dict:
    user_id = user["ID"]

    role_grants = query_many(
        """
        SELECT rg.id, r.name AS role_name, r.label AS role_label, rg.site_id
        FROM USER_ROLE_GRANTS rg
        JOIN ROLES r ON r.id = rg.role_id
        WHERE rg.user_id = %s AND rg.revoked_at IS NULL
        """,
        (user_id,)
    )

    role_names = [g["ROLE_NAME"] for g in role_grants]

    permissions = query_many(
        """
        SELECT DISTINCT p.code
        FROM ROLE_PERMISSIONS rp
        JOIN PERMISSIONS p ON p.id = rp.permission_id
        JOIN USER_ROLE_GRANTS rg ON rg.role_id = rp.role_id
        WHERE rg.user_id = %s AND rg.revoked_at IS NULL
        """,
        (user_id,)
    )
    perm_codes = {p["CODE"] for p in permissions}

    sites = query_many(
        """
        SELECT DISTINCT s.id, s.name, s.timezone
        FROM SITES s
        JOIN USER_ROLE_GRANTS rg ON (rg.site_id = s.id OR rg.site_id IS NULL)
        WHERE rg.user_id = %s AND rg.revoked_at IS NULL AND s.active = TRUE
        """,
        (user_id,)
    )

    return {
        "user": {
            "id": user["ID"],
            "email": user["EMAIL"],
            "first_name": user["FIRST_NAME"],
            "last_name": user["LAST_NAME"],
            "employee_id": user["EMPLOYEE_ID"],
            "preferred_lang": user["PREFERRED_LANG"],
            "site_id": user["SITE_ID"],
        },
        "role_grants": role_grants,
        "permissions": list(perm_codes),
        "sites": sites,
        "primary_role": role_names[0] if role_names else None,
    }


def _populate_session(user: dict, me: dict):
    st.session_state["user"] = me["user"]
    st.session_state["permissions"] = set(me["permissions"])
    st.session_state["role_name"] = me["primary_role"]
    st.session_state["site_id"] = user["SITE_ID"]
    st.session_state["access_token"] = _make_access_token(user["ID"])


def has_permission(code: str) -> bool:
    perms = st.session_state.get("permissions", set())
    return code in perms


def require_permission(code: str):
    """Show error and stop rendering if user lacks permission."""
    if not has_permission(code):
        st.error("⛔ You don't have permission to access this page.")
        st.stop()


def current_user() -> dict | None:
    return st.session_state.get("user")


def current_lang() -> str:
    user = current_user()
    return user.get("preferred_lang", "en") if user else "en"
