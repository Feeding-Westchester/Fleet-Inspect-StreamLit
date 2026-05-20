"""
Fleet Inspect — Snowflake connection module.

Reads credentials from Streamlit secrets (st.secrets) which maps to
.streamlit/secrets.toml locally and the Streamlit Cloud secrets UI in prod.

Required secrets keys:
    [snowflake]
    account   = "xy12345.us-east-1"
    user      = "FLEET_INSPECT_SVC"
    password  = "..."
    warehouse = "FLEET_WH"
    database  = "FLEET_INSPECT"
    schema    = "CORE"
    role      = "FLEET_INSPECT_ROLE"
"""

import snowflake.connector
import streamlit as st
from contextlib import contextmanager
import functools

# ── Connection cache ──────────────────────────────────────────
# st.cache_resource keeps one connection per Streamlit session worker.

@st.cache_resource(show_spinner=False)
def _get_connection():
    sf = st.secrets["snowflake"]
  conn = snowflake.connector.connect(
    account=sf["account"],
    user=sf["user"],
    password=sf["password"],
    warehouse=sf["warehouse"],
    database=sf["database"],
    schema=sf["schema"],
    role=sf.get("role", "FLEET_INSPECT_ROLE"),
    session_parameters={
        "TIMEZONE": "America/New_York",
        "AUTOCOMMIT": False,
    },
)
conn.cursor().execute(f"USE WAREHOUSE {sf['warehouse']}")
conn.cursor().execute(f"USE DATABASE {sf['database']}")
conn.cursor().execute(f"USE SCHEMA {sf['schema']}")
    return conn


def get_conn():
    """Return the cached Snowflake connection, reconnecting if needed."""
    conn = _get_connection()
    try:
        conn.cursor().execute("SELECT 1")
    except Exception:
        # Clear cache and reconnect
        _get_connection.clear()
        conn = _get_connection()
    return conn


@contextmanager
def cursor():
    """Context manager that yields a DictCursor and commits on success."""
    conn = get_conn()
    cur = conn.cursor(snowflake.connector.DictCursor)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


# ── Query helpers ─────────────────────────────────────────────

def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Return first row as dict or None."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def query_many(sql: str, params: tuple = ()) -> list[dict]:
    """Return all rows as list of dicts."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() or []


def execute(sql: str, params: tuple = ()) -> int:
    """Execute a DML statement. Returns rowcount."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def execute_many(sql: str, rows: list[tuple]) -> int:
    """Bulk insert/update. Returns total rowcount."""
    with cursor() as cur:
        cur.executemany(sql, rows)
        return cur.rowcount
