"""Fleet Inspect — New Inspection (mobile-first)"""
import streamlit as st
import os
from auth.jwt_auth import require_auth, require_permission, current_user
from db.connection import query_many, query_one
from utils.mobile import inject_mobile_css, page_header
from utils.business_logic import submit_inspection, start_session

st.set_page_config(page_title="Fleet Inspect – Inspect", page_icon="📋",
                   layout="wide", initial_sidebar_state="expanded")
inject_mobile_css()
require_auth()
require_permission("inspection.create")

user    = current_user()
site_id = st.session_state.get("site_id")
lang    = user.get("preferred_lang", "en")
page_header(os.path.splitext(os.path.basename(__file__))[0], lang)

L = {
    "title":      {"en": "New inspection",      "es": "Nueva inspección"},
    "asset":      {"en": "Asset",               "es": "Activo"},
    "operator":   {"en": "Operator",            "es": "Operador"},
    "type":       {"en": "Inspection type",     "es": "Tipo de inspección"},
    "pre":        {"en": "Pre-trip",            "es": "Previo al viaje"},
    "post":       {"en": "Post-trip",           "es": "Posterior al viaje"},
    "periodic":   {"en": "Periodic",            "es": "Periódica"},
    "rts":        {"en": "Return to service",   "es": "Retorno al servicio"},
    "submit":     {"en": "Submit inspection",   "es": "Enviar inspección"},
    "pass":       {"en": "Pass",                "es": "Pasar"},
    "fail":       {"en": "Fail",                "es": "Fallar"},
    "na":         {"en": "N/A",                 "es": "N/A"},
    "notes":      {"en": "Notes (optional)",    "es": "Notas (opcional)"},
    "crit_warn":  {"en": "⚠️ Critical — asset will be placed Out of Service on fail.",
                   "es": "⚠️ Crítico — el activo quedará fuera de servicio si falla."},
    "no_assets":  {"en": "No available assets.", "es": "Sin activos disponibles."},
    "no_ops":     {"en": "No active operators.", "es": "Sin operadores activos."},
    "no_tmpl":    {"en": "No checklist template found for this asset type.",
                   "es": "No se encontró plantilla para este tipo de activo."},
    "loading":    {"en": "Submitting…",         "es": "Enviando…"},
}
def t(k): return L[k][lang]

st.title(f"📋 {t('title')}")

# ── Step 1: Asset ──────────────────────────────────────────────
assets = query_many(
    "SELECT id, name, tag, asset_type_id FROM ASSETS WHERE site_id=%s AND active=TRUE AND status IN ('available','in_use') ORDER BY name",
    (site_id,)
)
if not assets:
    st.warning(t("no_assets")); st.stop()

asset_opts = {f"{a['NAME']} ({a['TAG']})": a for a in assets}
sel_asset_label = st.selectbox(t("asset"), list(asset_opts.keys()))
sel_asset = asset_opts[sel_asset_label]

# ── Step 2: Operator ───────────────────────────────────────────
operators = query_many(
    "SELECT id, first_name, last_name, employee_id FROM OPERATORS WHERE site_id=%s AND active=TRUE ORDER BY last_name",
    (site_id,)
)
if not operators:
    st.warning(t("no_ops")); st.stop()

op_opts = {f"{o['LAST_NAME']}, {o['FIRST_NAME']} ({o['EMPLOYEE_ID']})": o for o in operators}
sel_op_label = st.selectbox(t("operator"), list(op_opts.keys()))
sel_op = op_opts[sel_op_label]

# ── Step 3: Type ───────────────────────────────────────────────
type_map = {t("pre"): "pre_trip", t("post"): "post_trip",
            t("periodic"): "periodic", t("rts"): "return_to_service"}
insp_type = type_map[st.selectbox(t("type"), list(type_map.keys()))]

# ── Step 4: Template ───────────────────────────────────────────
template = query_one(
    """SELECT id, name_en, name_es FROM CHECKLIST_TEMPLATES
       WHERE asset_type_id=%s AND active=TRUE AND (site_id=%s OR site_id IS NULL)
       ORDER BY site_id DESC NULLS LAST, version DESC LIMIT 1""",
    (sel_asset["ASSET_TYPE_ID"], site_id)
)
if not template:
    st.error(t("no_tmpl")); st.stop()

tmpl_name = template["NAME_ES"] if lang == "es" else template["NAME_EN"]
st.caption(f"📄 {tmpl_name}")

items = query_many(
    """SELECT id, sort_order, category_en, category_es, label_en, label_es,
              response_type, critical, help_text_en, help_text_es
       FROM CHECKLIST_ITEMS WHERE template_id=%s AND active=TRUE ORDER BY sort_order""",
    (template["ID"],)
)
if not items:
    st.error("Checklist has no items."); st.stop()

# ── Step 5: Checklist form ─────────────────────────────────────
st.divider()
responses = []
current_cat = None

with st.form("inspection_form", border=False):
    for item in items:
        cat = item["CATEGORY_ES"] if lang == "es" else item["CATEGORY_EN"]
        if cat and cat != current_cat:
            st.markdown(f"#### {cat}")
            current_cat = cat

        label = item["LABEL_ES"] if lang == "es" else item["LABEL_EN"]
        help_  = (item["HELP_TEXT_ES"] if lang == "es" else item["HELP_TEXT_EN"]) or ""

        # Critical badge
        crit_badge = " 🔴" if item["CRITICAL"] else ""
        if item["CRITICAL"]:
            st.markdown(
                f'<div class="alert-strip alert-warning" style="margin-bottom:4px">'
                f'<small>{t("crit_warn")}</small></div>',
                unsafe_allow_html=True,
            )

        if item["RESPONSE_TYPE"] == "pass_fail":
            st.markdown(f"**{label}{crit_badge}**")
            if help_:
                st.caption(help_)
            # st.segmented_control renders as a pill toggle — selected option
            # is clearly highlighted with the theme's primaryColor (#534AB7).
            # Much more legible than radio buttons on a phone screen.
            r = st.segmented_control(
                label,
                options=[t("pass"), t("fail"), t("na")],
                key=f"r_{item['ID']}",
                label_visibility="collapsed",
                default=t("pass"),
            )
            result = {t("pass"): "pass", t("fail"): "fail"}.get(r, "na")
            notes = st.text_input(t("notes"), key=f"n_{item['ID']}",
                                  label_visibility="collapsed")
            responses.append({"item_id": item["ID"], "result": result,
                               "notes": notes or None})

        elif item["RESPONSE_TYPE"] == "numeric":
            val = st.number_input(f"**{label}**", key=f"num_{item['ID']}")
            responses.append({"item_id": item["ID"], "result": "pass", "numeric_value": val})

        elif item["RESPONSE_TYPE"] == "text":
            val = st.text_area(f"**{label}**", key=f"txt_{item['ID']}")
            responses.append({"item_id": item["ID"],
                               "result": "pass" if val else "fail", "text_value": val})
        st.divider()

    submitted = st.form_submit_button(t("submit"), type="primary", use_container_width=True)

if submitted:
    with st.spinner(t("loading")):
        session = start_session(site_id, sel_asset["ID"], sel_op["ID"], user["id"])
        result  = submit_inspection(
            session_id=session["id"], asset_id=sel_asset["ID"],
            operator_id=sel_op["ID"], submitted_by=user["id"],
            template_id=template["ID"], inspection_type=insp_type,
            responses=responses, site_id=site_id,
        )
    if result.get("error"):
        st.error(result["error"])
    elif result["result"] == "pass":
        st.success(f"✅ {'Inspección aprobada' if lang=='es' else 'Inspection passed'}! ID: {result['id'][:8]}")
    else:
        st.error(f"❌ {'Inspección reprobada' if lang=='es' else 'Inspection failed'}. "
                 f"{'Fallas críticas' if lang=='es' else 'Critical failures'}: {result['critical_fail_count']}")
        if result["oos_triggered"]:
            st.error("🚫 " + ("Activo fuera de servicio. Orden de trabajo creada automáticamente."
                               if lang == "es" else
                               "Asset placed Out of Service. Work order auto-created."))
