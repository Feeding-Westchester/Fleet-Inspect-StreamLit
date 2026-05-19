"""Fleet Inspect — Notifications"""
import streamlit as st
import os
from auth.jwt_auth import require_auth, current_user
from db.connection import query_many, execute
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t

st.set_page_config(page_title="Fleet Inspect – Notifications", page_icon="🔔", layout="wide")
inject_mobile_css()
require_auth()
user = current_user()
st.title(f"🔔 {t('nav_notifications')}")

show_read = st.checkbox("Show read notifications")
sql = "SELECT id, type, title, body, entity_type, entity_id, read_at, TO_VARCHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created FROM NOTIFICATIONS WHERE user_id = %s"
params = [user["id"]]
if not show_read:
    sql += " AND read_at IS NULL"
sql += " ORDER BY created_at DESC"

notifs = query_many(sql, tuple(params))

if notifs:
    unread_ids = [n["ID"] for n in notifs if n["READ_AT"] is None]
    if unread_ids and st.button("Mark all as read"):
        for nid in unread_ids:
            execute(
                "UPDATE NOTIFICATIONS SET read_at = CURRENT_TIMESTAMP() WHERE id = %s",
                (nid,)
            )
        st.rerun()

    for n in notifs:
        is_read = n["READ_AT"] is not None
        icon = {
            "defect_created": "⚠️", "oos_triggered": "🔴",
            "work_order_assigned": "🔧", "temp_hold_pending": "🌡️",
            "inspection_overdue": "⏰", "safety_obs_created": "🦺",
        }.get(n["TYPE"], "🔔")
        with st.container():
            col1, col2 = st.columns([9, 1])
            with col1:
                opacity = "0.5" if is_read else "1.0"
                st.markdown(
                    f'<div style="opacity:{opacity}"><b>{icon} {n["TITLE"]}</b> '
                    f'<span style="color:gray;font-size:0.8em">{n["CREATED"]}</span><br>'
                    f'{n["BODY"] or ""}</div>',
                    unsafe_allow_html=True
                )
            with col2:
                if not is_read:
                    if st.button("✓", key=f"read_{n['ID']}"):
                        execute(
                            "UPDATE NOTIFICATIONS SET read_at = CURRENT_TIMESTAMP() WHERE id = %s",
                            (n["ID"],)
                        )
                        st.rerun()
            st.divider()
else:
    st.success("No unread notifications." if not show_read else "No notifications found.")
