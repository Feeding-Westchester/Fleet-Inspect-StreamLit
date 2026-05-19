"""Fleet Inspect — Defects Page"""
import streamlit as st
import os
import pandas as pd
from auth.jwt_auth import require_auth, has_permission, current_user
from db.connection import query_many, execute
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t

st.set_page_config(page_title="Fleet Inspect – Defects", page_icon="⚠️", layout="wide")
inject_mobile_css()
require_auth()
user = current_user()
site_id = st.session_state.get("site_id")
st.title(f"⚠️ {t('nav_defects')}")

status_filter = st.selectbox(t("filter"), ["All", "open", "in_progress", "resolved", "closed"])

sql = """
SELECT d.id, a.name AS asset, a.tag, d.severity, d.description, d.status,
       d.auto_generated, d.oos_triggered,
       u.first_name || ' ' || u.last_name AS reported_by,
       TO_VARCHAR(d.created_at, 'YYYY-MM-DD') AS reported_date,
       TO_VARCHAR(d.resolved_at, 'YYYY-MM-DD') AS resolved_date
FROM DEFECTS d
JOIN ASSETS a ON a.id = d.asset_id
JOIN USERS u ON u.id = d.reported_by
WHERE a.site_id = %s
"""
params = [site_id]
if status_filter != "All":
    sql += " AND d.status = %s"
    params.append(status_filter)
sql += " ORDER BY d.created_at DESC"

defects = query_many(sql, tuple(params))
if defects:
    df = pd.DataFrame(defects)
    df.columns = [c.lower() for c in df.columns]
    df["severity"] = df["severity"].map(
        {"critical": "🔴 Critical", "major": "🟠 Major", "minor": "🟡 Minor"}
    ).fillna(df["severity"])
    df["auto_generated"] = df["auto_generated"].map({True: "Yes", False: "No"})
    df["oos_triggered"]  = df["oos_triggered"].map({True: "Yes", False: "No"})
    st.dataframe(df[["reported_date", "asset", "tag", "severity", "description",
                      "status", "auto_generated", "oos_triggered", "reported_by"]],
                 use_container_width=True, hide_index=True)

    # Quick resolve for fleet_admin / maintenance_tech
    if has_permission("defect.manage"):
        st.divider()
        open_defects = [d for d in defects if d["STATUS"] in ("open", "in_progress")]
        if open_defects:
            defect_opts = {f"{d['ASSET']} – {d['DESCRIPTION'][:60]}": d["ID"] for d in open_defects}
            sel = st.selectbox("Resolve Defect", list(defect_opts.keys()))
            res_notes = st.text_area("Resolution Notes *")
            if st.button("Mark Resolved", type="primary"):
                if not res_notes:
                    st.error("Resolution notes are required.")
                else:
                    execute(
                        """
                        UPDATE DEFECTS SET status = 'resolved',
                            resolved_at = CURRENT_TIMESTAMP(), resolved_by = %s,
                            resolution_notes = %s, updated_at = CURRENT_TIMESTAMP()
                        WHERE id = %s
                        """,
                        (user["id"], res_notes, defect_opts[sel])
                    )
                    st.success("Defect marked resolved.")
                    st.rerun()
else:
    st.info(t("no_data"))
