import snowflake.connector
import streamlit as st
from contextlib import contextmanager

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
        autocommit=False,
    )
    return conn


def get_conn():
    conn = _get_connection()
    try:
        conn.cursor().execute("SELECT 1")
    except Exception:
        _get_connection.clear()
        conn = _get_connection()
    return conn


@contextmanager
def cursor():
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


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def query_many(sql: str, params: tuple = ()) -> list[dict]:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() or []


def execute(sql: str, params: tuple = ()) -> int:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def execute_many(sql: str, rows: list[tuple]) -> int:
    with cursor() as cur:
        cur.executemany(sql, rows)
        return cur.rowcount