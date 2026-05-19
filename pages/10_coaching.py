"""Fleet Inspect — Coaching"""
import streamlit as st
import os
import pandas as pd
import uuid
from auth.jwt_auth import require_auth, has_permission, current_user
from db.connection import query_many, execute
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t

st.set_page_config(page_title="Fleet Inspect – Coaching", page_icon="📝", layout="wide")
inject_mobile_css()
require_auth()
require_permission("coaching.read_self")
user = current_user()
site_id = st.session_state.get("site_id")
st.title(f"📝 {t('nav_coaching')}")

can_manage = has_permission("operator.manage")

if can_manage:
    tab1, tab2 = st.tabs(["All Operators", "My Notes"])
else:
    tab1, tab2 = None, st.container(), 

# ── Manager view ──────────────────────────────────────────────
if can_manage:
    with tab1:
        operators = query_many(
            """
            SELECT o.id, o.first_name || ' ' || o.last_name AS name, o.employee_id
            FROM OPERATORS o WHERE o.site_id = %s AND o.active = TRUE ORDER BY o.last_name
            """,
            (site_id,)
        )
        if operators:
            op_opts = {o["NAME"]: o["ID"] for o in operators}
            sel_op = st.selectbox("Select Operator", list(op_opts.keys()))
            op_id = op_opts[sel_op]

            notes = query_many(
                """
                SELECT cn.note_type, cn.body, cn.private,
                       u.first_name || ' ' || u.last_name AS author,
                       TO_VARCHAR(cn.created_at, 'YYYY-MM-DD') AS date
                FROM COACHING_NOTES cn
                JOIN USERS u ON u.id = cn.authored_by
                WHERE cn.operator_id = %s
                ORDER BY cn.created_at DESC
                """,
                (op_id,)
            )
            if notes:
                for n in notes:
                    icon = {"general": "💬", "corrective": "⚠️",
                            "commendation": "🌟", "training": "📚"}.get(n["NOTE_TYPE"], "📝")
                    priv = " 🔒" if n["PRIVATE"] else ""
                    st.markdown(f"**{icon} {n['NOTE_TYPE'].title()}{priv}** — {n['DATE']} by {n['AUTHOR']}")
                    st.write(n["BODY"])
                    st.divider()
            else:
                st.info("No coaching notes for this operator.")

            st.subheader("Add Note")
            with st.form("add_note"):
                note_type = st.selectbox("Type", ["general", "corrective", "commendation", "training"])
                body = st.text_area("Note *")
                private = st.checkbox("Private (visible to managers only)")
                if st.form_submit_button("Add Note", type="primary"):
                    if not body:
                        st.error("Note body is required.")
                    else:
                        execute(
                            """
                            INSERT INTO COACHING_NOTES (id, operator_id, authored_by,
                                note_type, body, private)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (str(uuid.uuid4()), op_id, user["id"],
                             note_type, body, private)
                        )
                        st.success("Note added.")
                        st.rerun()

# ── Self view ─────────────────────────────────────────────────
self_tab = tab2 if can_manage else tab2
with self_tab if can_manage else st.container():
    # Find operator record for current user
    my_op = query_many(
        """
        SELECT o.id FROM OPERATORS o
        JOIN USERS u ON u.id = o.user_id
        WHERE u.id = %s
        """,
        (user["id"],)
    )
    if my_op:
        my_notes = query_many(
            """
            SELECT cn.note_type, cn.body,
                   u.first_name || ' ' || u.last_name AS author,
                   TO_VARCHAR(cn.created_at, 'YYYY-MM-DD') AS date
            FROM COACHING_NOTES cn
            JOIN USERS u ON u.id = cn.authored_by
            WHERE cn.operator_id = %s AND cn.private = FALSE
            ORDER BY cn.created_at DESC
            """,
            (my_op[0]["ID"],)
        )
        if my_notes:
            for n in my_notes:
                icon = {"general": "💬", "corrective": "⚠️",
                        "commendation": "🌟", "training": "📚"}.get(n["NOTE_TYPE"], "📝")
                st.markdown(f"**{icon} {n['NOTE_TYPE'].title()}** — {n['DATE']} by {n['AUTHOR']}")
                st.write(n["BODY"])
                st.divider()
        else:
            st.info("No coaching notes on your record.")
    else:
        st.info("No operator record linked to your account.")
