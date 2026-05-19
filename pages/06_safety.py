"""Fleet Inspect — Safety Observations"""
import streamlit as st
import os
import pandas as pd
import uuid
from auth.jwt_auth import require_auth, require_permission, has_permission, current_user
from db.connection import query_many, execute
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t
from utils.business_logic import add_safety_action

st.set_page_config(page_title="Fleet Inspect – Safety", page_icon="🦺", layout="wide")
inject_mobile_css()
require_auth()
require_permission("safety.create")
user = current_user()
site_id = st.session_state.get("site_id")
lang = user.get("preferred_lang", "en")
page_header(os.path.splitext(os.path.basename(__file__))[0], lang)
st.title(f"🦺 {t('nav_safety')}")

tab1, tab2 = st.tabs(["View Observations", "Report New"])

with tab1:
    obs = query_many(
        """
        SELECT so.id, so.category, so.severity, so.description, so.status,
               so.location,
               u.first_name || ' ' || u.last_name AS reported_by,
               a.name AS asset,
               TO_VARCHAR(so.created_at, 'YYYY-MM-DD') AS date
        FROM SAFETY_OBSERVATIONS so
        JOIN USERS u ON u.id = so.reported_by
        LEFT JOIN ASSETS a ON a.id = so.asset_id
        WHERE so.site_id = %s
        ORDER BY so.created_at DESC
        """,
        (site_id,)
    )
    if obs:
        df = pd.DataFrame(obs)
        df.columns = [c.lower() for c in df.columns]
        st.dataframe(df[["date", "category", "severity", "description",
                          "status", "location", "asset", "reported_by"]],
                     use_container_width=True, hide_index=True)

        if has_permission("safety.manage"):
            open_obs = [o for o in obs if o["STATUS"] in ("open", "under_review")]
            if open_obs:
                st.divider()
                st.subheader("Add Action to Observation")
                obs_opts = {f"{o['DATE']} – {o['DESCRIPTION'][:60]}": o["ID"] for o in open_obs}
                sel = st.selectbox("Observation", list(obs_opts.keys()))
                action_type = st.selectbox("Action Type",
                    ["corrective_action", "training", "equipment_fix", "policy_update", "other"])
                action_desc = st.text_area("Description *")
                if st.button("Add Action", type="primary"):
                    if not action_desc:
                        st.error("Description required.")
                    else:
                        add_safety_action(obs_opts[sel], user["id"], action_type, action_desc)
                        st.success("Action recorded.")
                        st.rerun()
    else:
        st.info(t("no_data"))

with tab2:
    assets = query_many(
        "SELECT id, name, tag FROM ASSETS WHERE site_id = %s AND active = TRUE ORDER BY name",
        (site_id,)
    )
    asset_opts = {"(None)": None}
    asset_opts.update({f"{a['NAME']} ({a['TAG']})": a["ID"] for a in assets})

    with st.form("new_obs"):
        category = st.selectbox(
            "Category" if lang == "en" else "Categoría",
            ["near_miss", "unsafe_condition", "unsafe_act", "positive"]
        )
        severity = st.selectbox(
            "Severity" if lang == "en" else "Gravedad",
            ["low", "medium", "high", "critical"]
        )
        description = st.text_area("Description *" if lang == "en" else "Descripción *")
        location    = st.text_input("Location" if lang == "en" else "Ubicación")
        asset_sel   = st.selectbox("Related Asset" if lang == "en" else "Activo relacionado",
                                   list(asset_opts.keys()))
        if st.form_submit_button("Submit" if lang == "en" else "Enviar", type="primary"):
            if not description:
                st.error("Description required.")
            else:
                execute(
                    """
                    INSERT INTO SAFETY_OBSERVATIONS (id, site_id, asset_id, reported_by,
                        category, severity, description, location, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'open')
                    """,
                    (str(uuid.uuid4()), site_id, asset_opts[asset_sel],
                     user["id"], category, severity, description, location or None)
                )
                st.success("Observation submitted." if lang == "en" else "Observación enviada.")
