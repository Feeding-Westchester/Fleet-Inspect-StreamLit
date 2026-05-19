"""Fleet Inspect — Dashboard (mobile-first)"""
import streamlit as st
from auth.jwt_auth import require_auth, current_user, has_permission
from db.connection import query_many, query_one
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t
import os

st.set_page_config(page_title="Fleet Inspect – Dashboard", page_icon="🚛",
                   layout="wide", initial_sidebar_state="expanded")
inject_mobile_css()
require_auth()

user    = current_user()
site_id = st.session_state.get("site_id")
lang    = user.get("preferred_lang", "en")

unread = (query_one(
    "SELECT COUNT(*) AS cnt FROM NOTIFICATIONS WHERE user_id = %s AND read_at IS NULL",
    (user["id"],)
) or {}).get("CNT", 0)

page_header(os.path.splitext(os.path.basename(__file__))[0], lang, unread)

st.title("📊 " + ("Panel" if lang == "es" else "Dashboard"))

# ── KPI row — 2 cols on mobile, 5 on desktop ─────────────────
compliance = query_one(
    """SELECT COUNT(*) AS total,
              SUM(CASE WHEN overall_result='pass' THEN 1 ELSE 0 END) AS passed
       FROM INSPECTIONS WHERE submitted_at >= DATEADD('day',-30,CURRENT_TIMESTAMP())
         AND submitted_by IN (SELECT id FROM USERS WHERE site_id = %s)""",
    (site_id,)
) or {"TOTAL": 0, "PASSED": 0}
total_insp = compliance["TOTAL"] or 0
compliance_pct = round((compliance["PASSED"] or 0) / total_insp * 100, 1) if total_insp else 0

asset_stats = query_many(
    "SELECT status, COUNT(*) AS cnt FROM ASSETS WHERE site_id=%s AND active=TRUE GROUP BY status",
    (site_id,)
)
asset_map   = {r["STATUS"]: r["CNT"] for r in asset_stats}
total_assets = sum(asset_map.values())
oos_count    = asset_map.get("oos", 0)

open_defects = (query_one(
    "SELECT COUNT(*) AS cnt FROM DEFECTS d JOIN ASSETS a ON a.id=d.asset_id WHERE a.site_id=%s AND d.status IN ('open','in_progress')",
    (site_id,)
) or {}).get("CNT", 0)

open_wo = (query_one(
    "SELECT COUNT(*) AS cnt FROM WORK_ORDERS wo JOIN ASSETS a ON a.id=wo.asset_id WHERE a.site_id=%s AND wo.status IN ('open','in_progress','pending_verification')",
    (site_id,)
) or {}).get("CNT", 0)

# Two columns on mobile, five on desktop via responsive CSS
c1, c2 = st.columns(2)
c1.metric("Compliance (30d)", f"{compliance_pct}%", f"{total_insp} inspections")
c2.metric("Fleet available",  f"{asset_map.get('available',0)}/{total_assets}",
          f"{oos_count} OOS", delta_color="inverse" if oos_count else "normal")
c3, c4 = st.columns(2)
c3.metric("Open defects",     open_defects, delta_color="inverse")
c4.metric("Unread alerts",    unread,       delta_color="off")

st.divider()

# ── Recent inspections (card list — better on mobile than table) ──
st.subheader("Recent inspections" if lang == "en" else "Inspecciones recientes")
recent = query_many(
    """SELECT i.id, a.name AS asset_name, a.tag,
              o.first_name||' '||o.last_name AS operator,
              i.inspection_type, i.overall_result, i.critical_fail_count,
              TO_VARCHAR(i.submitted_at,'YYYY-MM-DD HH24:MI') AS submitted
       FROM INSPECTIONS i JOIN ASSETS a ON a.id=i.asset_id
       JOIN OPERATORS o ON o.id=i.operator_id
       WHERE a.site_id=%s ORDER BY i.submitted_at DESC LIMIT 10""",
    (site_id,)
)

badge_map = {"pass": "✅", "fail": "❌", "conditional": "⚠️"}
for r in recent:
    icon = badge_map.get(r["OVERALL_RESULT"], "")
    st.markdown(
        f'<div class="row-card">'
        f'<div><div class="row-card-title">{r["ASSET_NAME"]} <span style="color:#888;font-weight:400">({r["TAG"]})</span></div>'
        f'<div class="row-card-sub">{r["OPERATOR"]} · {r["INSPECTION_TYPE"].replace("_"," ")} · {r["SUBMITTED"]}</div></div>'
        f'<div style="font-size:20px">{icon}</div></div>',
        unsafe_allow_html=True,
    )
if not recent:
    st.info("No inspections yet." if lang == "en" else "Sin inspecciones todavía.")

st.divider()

# ── Open alerts ────────────────────────────────────────────────
st.subheader("Open alerts" if lang == "en" else "Alertas abiertas")
alerts = query_many(
    """SELECT type, title, body, TO_VARCHAR(created_at,'HH24:MI') AS t
       FROM NOTIFICATIONS WHERE user_id=%s AND read_at IS NULL
       ORDER BY created_at DESC LIMIT 8""",
    (user["id"],)
)
icon_map = {
    "oos_triggered": ("🔴", "danger"), "defect_created": ("⚠️", "warning"),
    "work_order_assigned": ("🔧", "info"), "temp_hold_pending": ("🌡️", "warning"),
    "inspection_overdue": ("⏰", "warning"), "safety_obs_created": ("🦺", "info"),
}
for a in alerts:
    ico, cls = icon_map.get(a["TYPE"], ("🔔", "info"))
    st.markdown(
        f'<div class="alert-strip alert-{cls}">'
        f'<span style="font-size:18px">{ico}</span>'
        f'<div><strong>{a["TITLE"]}</strong><br><span style="font-size:12px">{a["BODY"] or ""}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
if not alerts:
    st.success("No unread alerts." if lang == "en" else "Sin alertas sin leer.")
