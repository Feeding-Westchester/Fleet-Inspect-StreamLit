"""Fleet Inspect — Temperature Holds"""
import streamlit as st
import os
import pandas as pd
import uuid
from auth.jwt_auth import require_auth, has_permission, current_user
from db.connection import query_many, execute
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t
from utils.business_logic import review_temp_hold

st.set_page_config(page_title="Fleet Inspect – Temp Holds", page_icon="🌡️", layout="wide")
inject_mobile_css()
require_auth()
user = current_user()
site_id = st.session_state.get("site_id")
lang = user.get("preferred_lang", "en")
page_header(os.path.splitext(os.path.basename(__file__))[0], lang)
st.title(f"🌡️ {t('nav_temp_holds')}")

tab1, tab2 = st.tabs(["View Holds", "Report New Hold"])

with tab1:
    holds = query_many(
        """
        SELECT th.id, a.name AS asset, th.temp_reading, th.temp_unit,
               th.threshold_min, th.threshold_max, th.product_desc,
               th.status, th.review_notes,
               u.first_name || ' ' || u.last_name AS reported_by,
               TO_VARCHAR(th.created_at, 'YYYY-MM-DD HH24:MI') AS reported_at
        FROM TEMPERATURE_HOLDS th
        JOIN ASSETS a ON a.id = th.asset_id
        JOIN USERS u ON u.id = th.reported_by
        WHERE a.site_id = %s
        ORDER BY th.created_at DESC
        """,
        (site_id,)
    )
    if holds:
        df = pd.DataFrame(holds)
        df.columns = [c.lower() for c in df.columns]
        df["status"] = df["status"].map({
            "pending": "⏳ Pending", "approved": "✅ Approved",
            "rejected": "❌ Rejected", "escalated": "🚨 Escalated"
        }).fillna(df["status"])
        st.dataframe(df[["reported_at", "asset", "temp_reading", "temp_unit",
                          "product_desc", "status", "reported_by"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info(t("no_data"))

    # Approve / reject (supervisor+)
    if has_permission("approval.temperature") and holds:
        pending = [h for h in holds if h["STATUS"] == "pending"]
        if pending:
            st.divider()
            st.subheader("Review Pending Holds")
            hold_opts = {
                f"{h['ASSET']} — {h['TEMP_READING']}°{h['TEMP_UNIT']} ({h['REPORTED_AT']})": h["ID"]
                for h in pending
            }
            sel = st.selectbox("Select Hold", list(hold_opts.keys()))
            review_notes = st.text_area("Review Notes")
            c1, c2 = st.columns(2)
            if c1.button("✅ Approve", type="primary"):
                review_temp_hold(hold_opts[sel], "approve", user["id"], site_id, review_notes)
                st.success("Hold approved.")
                st.rerun()
            if c2.button("❌ Reject"):
                review_temp_hold(hold_opts[sel], "reject", user["id"], site_id, review_notes)
                st.warning("Hold rejected.")
                st.rerun()

with tab2:
    assets = query_many(
        "SELECT id, name, tag FROM ASSETS WHERE site_id = %s AND active = TRUE ORDER BY name",
        (site_id,)
    )
    asset_opts = {f"{a['NAME']} ({a['TAG']})": a["ID"] for a in assets}
    with st.form("new_hold"):
        asset_sel    = st.selectbox("Asset *", list(asset_opts.keys()))
        temp_reading = st.number_input("Temperature Reading *", step=0.1)
        temp_unit    = st.radio("Unit", ["F", "C"], horizontal=True)
        thr_min      = st.number_input("Min Threshold")
        thr_max      = st.number_input("Max Threshold")
        product_desc = st.text_input("Product Description")
        if st.form_submit_button("Report Hold", type="primary"):
            execute(
                """
                INSERT INTO TEMPERATURE_HOLDS (id, asset_id, reported_by, temp_reading,
                    temp_unit, threshold_min, threshold_max, product_desc, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """,
                (str(uuid.uuid4()), asset_opts[asset_sel], user["id"],
                 temp_reading, temp_unit,
                 thr_min if thr_min != 0 else None,
                 thr_max if thr_max != 0 else None,
                 product_desc or None)
            )
            st.success("Temperature hold reported. Awaiting supervisor review.")
