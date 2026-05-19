"""
Fleet Inspect — Reports
Dashboard: compliance, fleet health, operator stats, alerts.
Requires: reports.read permission.
"""
import streamlit as st
import os
import pandas as pd
from auth.jwt_auth import require_auth, require_permission, current_user
from db.connection import query_many, query_one
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t

st.set_page_config(page_title="Fleet Inspect – Reports", page_icon="📈", layout="wide")
inject_mobile_css()
require_auth()
require_permission("reports.read")
user = current_user()
site_id = st.session_state.get("site_id")
st.title(f"📈 {t('nav_reports')}")

tab_compliance, tab_fleet, tab_ops, tab_alerts = st.tabs(
    ["Compliance", "Fleet Health", "Operators", "Alerts"]
)

# ── Date range selector ───────────────────────────────────────
with st.sidebar:
    st.subheader("Date Range")
    days = st.slider("Last N days", 7, 90, 30)

# ── Compliance Report ─────────────────────────────────────────
with tab_compliance:
    st.subheader("Inspection Compliance")

    compliance_data = query_many(
        f"""
        SELECT
            TO_VARCHAR(DATE_TRUNC('day', submitted_at), 'YYYY-MM-DD') AS day,
            COUNT(*) AS total,
            SUM(CASE WHEN overall_result = 'pass' THEN 1 ELSE 0 END) AS passed,
            SUM(CASE WHEN overall_result = 'fail' THEN 1 ELSE 0 END) AS failed,
            SUM(critical_fail_count) AS critical_fails
        FROM INSPECTIONS i
        JOIN ASSETS a ON a.id = i.asset_id
        WHERE a.site_id = %s
          AND i.submitted_at >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        GROUP BY 1 ORDER BY 1
        """,
        (site_id,)
    )
    if compliance_data:
        df = pd.DataFrame(compliance_data)
        df.columns = [c.lower() for c in df.columns]
        df["pass_rate"] = (df["passed"] / df["total"] * 100).round(1)
        st.line_chart(df.set_index("day")[["passed", "failed"]])

        totals = df[["total", "passed", "failed", "critical_fails"]].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Inspections", int(totals["total"]))
        c2.metric("Pass Rate",
                  f"{round(totals['passed']/totals['total']*100, 1)}%" if totals["total"] else "N/A")
        c3.metric("Critical Failures", int(totals["critical_fails"]))

        st.subheader("By Inspection Type")
        by_type = query_many(
            f"""
            SELECT inspection_type,
                   COUNT(*) AS total,
                   SUM(CASE WHEN overall_result='pass' THEN 1 ELSE 0 END) AS passed
            FROM INSPECTIONS i JOIN ASSETS a ON a.id = i.asset_id
            WHERE a.site_id = %s
              AND i.submitted_at >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
            GROUP BY inspection_type ORDER BY total DESC
            """,
            (site_id,)
        )
        if by_type:
            df_type = pd.DataFrame(by_type)
            df_type.columns = [c.lower() for c in df_type.columns]
            df_type["pass_rate"] = (df_type["passed"] / df_type["total"] * 100).round(1)
            st.dataframe(df_type, use_container_width=True, hide_index=True)
        st.download_button("Export CSV", df.to_csv(index=False), "compliance.csv", "text/csv")
    else:
        st.info(t("no_data"))

# ── Fleet Health Report ───────────────────────────────────────
with tab_fleet:
    st.subheader("Fleet Health")
    fleet_data = query_many(
        """
        SELECT a.tag, a.name, at2.label_en AS type, a.status,
               TO_VARCHAR(a.last_inspected, 'YYYY-MM-DD') AS last_inspected,
               TO_VARCHAR(a.oos_since, 'YYYY-MM-DD') AS oos_since,
               a.oos_reason,
               COUNT(DISTINCT d.id) AS open_defects,
               COUNT(DISTINCT wo.id) AS open_work_orders
        FROM ASSETS a
        JOIN ASSET_TYPES at2 ON at2.id = a.asset_type_id
        LEFT JOIN DEFECTS d ON d.asset_id = a.id AND d.status IN ('open','in_progress')
        LEFT JOIN WORK_ORDERS wo ON wo.asset_id = a.id AND wo.status IN ('open','in_progress')
        WHERE a.site_id = %s AND a.active = TRUE
        GROUP BY a.tag, a.name, at2.label_en, a.status, a.last_inspected, a.oos_since, a.oos_reason
        ORDER BY a.status, a.name
        """,
        (site_id,)
    )
    if fleet_data:
        df = pd.DataFrame(fleet_data)
        df.columns = [c.lower() for c in df.columns]
        df["status"] = df["status"].map({
            "available": "✅ Available", "in_use": "🟡 In Use",
            "oos": "🔴 OOS", "maintenance": "🔧 Maintenance"
        }).fillna(df["status"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        oos_pct = len([r for r in fleet_data if r["STATUS"] == "oos"]) / len(fleet_data) * 100
        if oos_pct > 20:
            st.error(f"⚠️ {oos_pct:.1f}% of assets are OOS — exceeds 20% site policy threshold.")
        st.download_button("Export CSV", df.to_csv(index=False), "fleet_health.csv", "text/csv")
    else:
        st.info(t("no_data"))

# ── Operator Report ───────────────────────────────────────────
with tab_ops:
    st.subheader("Operator Performance")
    ops_data = query_many(
        f"""
        SELECT o.first_name || ' ' || o.last_name AS operator,
               o.employee_id,
               COUNT(i.id) AS inspections,
               SUM(CASE WHEN i.overall_result='pass' THEN 1 ELSE 0 END) AS passed,
               SUM(i.critical_fail_count) AS critical_fails
        FROM OPERATORS o
        LEFT JOIN INSPECTIONS i ON i.operator_id = o.id
          AND i.submitted_at >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        WHERE o.site_id = %s AND o.active = TRUE
        GROUP BY o.first_name, o.last_name, o.employee_id
        ORDER BY inspections DESC
        """,
        (site_id,)
    )
    if ops_data:
        df = pd.DataFrame(ops_data)
        df.columns = [c.lower() for c in df.columns]
        df["pass_rate"] = df.apply(
            lambda r: f"{round(r['passed']/r['inspections']*100,1)}%"
            if r["inspections"] > 0 else "N/A", axis=1
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Export CSV", df.to_csv(index=False), "operators.csv", "text/csv")
    else:
        st.info(t("no_data"))

# ── Alerts Report ─────────────────────────────────────────────
with tab_alerts:
    st.subheader("System Alerts")
    alerts_data = query_many(
        f"""
        SELECT n.type, n.title, n.body,
               u.first_name || ' ' || u.last_name AS recipient,
               TO_VARCHAR(n.created_at, 'YYYY-MM-DD HH24:MI') AS created,
               CASE WHEN n.read_at IS NULL THEN 'Unread' ELSE 'Read' END AS read_status
        FROM NOTIFICATIONS n
        JOIN USERS u ON u.id = n.user_id
        WHERE u.site_id = %s
          AND n.created_at >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        ORDER BY n.created_at DESC
        """,
        (site_id,)
    )
    if alerts_data:
        df = pd.DataFrame(alerts_data)
        df.columns = [c.lower() for c in df.columns]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts in this period.")
