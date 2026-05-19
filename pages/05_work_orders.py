"""Fleet Inspect — Work Orders Page"""
import streamlit as st
import os
import pandas as pd
import uuid
from auth.jwt_auth import require_auth, has_permission, current_user
from db.connection import query_many, execute, query_one
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t
from utils.business_logic import verify_work_order

st.set_page_config(page_title="Fleet Inspect – Work Orders", page_icon="🔧", layout="wide")
inject_mobile_css()
require_auth()
user = current_user()
site_id = st.session_state.get("site_id")
st.title(f"🔧 {t('nav_work_orders')}")

status_filter = st.selectbox(
    t("filter"),
    ["All", "open", "in_progress", "pending_verification", "verified", "closed"]
)

sql = """
SELECT wo.id, a.name AS asset, a.tag, wo.priority, wo.status,
       wo.description,
       u.first_name || ' ' || u.last_name AS created_by,
       TO_VARCHAR(wo.created_at, 'YYYY-MM-DD') AS created_date,
       TO_VARCHAR(wo.verified_at, 'YYYY-MM-DD') AS verified_date
FROM WORK_ORDERS wo
JOIN ASSETS a ON a.id = wo.asset_id
JOIN USERS u ON u.id = wo.created_by
WHERE a.site_id = %s
"""
params = [site_id]
if status_filter != "All":
    sql += " AND wo.status = %s"
    params.append(status_filter)
sql += " ORDER BY wo.created_at DESC"

work_orders = query_many(sql, tuple(params))

if work_orders:
    df = pd.DataFrame(work_orders)
    df.columns = [c.lower() for c in df.columns]
    df["priority"] = df["priority"].map({
        "critical": "🔴 Critical", "high": "🟠 High",
        "normal": "🟡 Normal", "low": "🟢 Low"
    }).fillna(df["priority"])
    st.dataframe(df[["created_date", "asset", "tag", "priority",
                      "status", "description", "created_by"]],
                 use_container_width=True, hide_index=True)
else:
    st.info(t("no_data"))

# ── Create work order ─────────────────────────────────────────
if has_permission("workorder.create"):
    st.divider()
    with st.expander("➕ Create Work Order"):
        assets = query_many(
            "SELECT id, name, tag FROM ASSETS WHERE site_id = %s AND active = TRUE ORDER BY name",
            (site_id,)
        )
        asset_opts = {f"{a['NAME']} ({a['TAG']})": a["ID"] for a in assets}
        with st.form("create_wo"):
            asset_sel = st.selectbox("Asset *", list(asset_opts.keys()))
            priority  = st.selectbox("Priority", ["normal", "high", "critical", "low"])
            desc      = st.text_area("Description *")
            if st.form_submit_button("Create", type="primary"):
                if not desc:
                    st.error("Description required.")
                else:
                    execute(
                        """
                        INSERT INTO WORK_ORDERS (id, asset_id, created_by, priority,
                            status, description)
                        VALUES (%s, %s, %s, %s, 'open', %s)
                        """,
                        (str(uuid.uuid4()), asset_opts[asset_sel],
                         user["id"], priority, desc)
                    )
                    st.success("Work order created.")
                    st.rerun()

# ── Verify work order ─────────────────────────────────────────
if has_permission("workorder.verify"):
    st.divider()
    pending = [wo for wo in work_orders
               if wo["STATUS"] in ("in_progress", "pending_verification")]
    if pending:
        st.subheader("Verify Completed Work")
        wo_opts = {f"{wo['ASSET']} – {wo['DESCRIPTION'][:60]}": wo["ID"] for wo in pending}
        sel_wo  = st.selectbox("Select Work Order", list(wo_opts.keys()))
        ver_notes = st.text_area("Verification Notes")
        if st.button("✅ Verify & Return to Service", type="primary"):
            result = verify_work_order(wo_opts[sel_wo], user["id"], site_id, ver_notes)
            if result.get("error"):
                st.error(result["error"])
            else:
                st.success("Work order verified. Asset returned to service.")
                st.rerun()
