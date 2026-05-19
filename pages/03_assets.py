"""Fleet Inspect — Assets (mobile-first)"""
import streamlit as st
import uuid, os
from auth.jwt_auth import require_auth, has_permission, current_user
from db.connection import query_many, execute, query_one
from utils.mobile import inject_mobile_css, page_header

st.set_page_config(page_title="Fleet Inspect – Assets", page_icon="🏭",
                   layout="wide", initial_sidebar_state="expanded")
inject_mobile_css()
require_auth()

user    = current_user()
site_id = st.session_state.get("site_id")
lang    = user.get("preferred_lang", "en")
page_header(os.path.splitext(os.path.basename(__file__))[0], lang)

title = "Activos" if lang == "es" else "Assets"
st.title(f"🏭 {title}")

search = st.text_input("🔍 " + ("Buscar…" if lang == "es" else "Search…"),
                       label_visibility="collapsed",
                       placeholder="Buscar activos…" if lang == "es" else "Search assets…")
status_filter = st.selectbox(
    "Status",
    ["All / Todos", "available", "in_use", "oos", "maintenance", "retired"],
    label_visibility="collapsed",
)

sql = """SELECT a.id, a.tag, a.name, at2.label_en AS type,
                at2.label_es AS type_es, a.status, a.make, a.model, a.year,
                TO_VARCHAR(a.last_inspected,'YYYY-MM-DD HH24:MI') AS last_inspected,
                a.oos_reason
         FROM ASSETS a JOIN ASSET_TYPES at2 ON at2.id=a.asset_type_id
         WHERE a.site_id=%s AND a.active=TRUE"""
params = [site_id]
if status_filter != "All / Todos":
    sql += " AND a.status=%s"; params.append(status_filter)
if search:
    sql += " AND (LOWER(a.name) LIKE %s OR LOWER(a.tag) LIKE %s)"
    params += [f"%{search.lower()}%"] * 2
sql += " ORDER BY a.name"

assets = query_many(sql, tuple(params))

STATUS_ICON = {"available": "✅", "in_use": "🟡", "oos": "🔴",
               "maintenance": "🔧", "retired": "⚫"}
STATUS_LABEL = {
    "en": {"available":"Available","in_use":"In use","oos":"OOS",
           "maintenance":"Maintenance","retired":"Retired"},
    "es": {"available":"Disponible","in_use":"En uso","oos":"Fuera de servicio",
           "maintenance":"Mantenimiento","retired":"Retirado"},
}

for a in assets:
    ico = STATUS_ICON.get(a["STATUS"], "")
    slabel = STATUS_LABEL[lang].get(a["STATUS"], a["STATUS"])
    atype  = a["TYPE_ES"] if lang == "es" else a["TYPE"]
    sub    = f"{a['MAKE'] or ''} {a['MODEL'] or ''} {a['YEAR'] or ''}".strip()
    insp   = a["LAST_INSPECTED"] or ("Nunca" if lang == "es" else "Never")
    st.markdown(
        f'<div class="row-card">'
        f'<div><div class="row-card-title">{a["NAME"]} <span style="color:#888;font-size:12px">({a["TAG"]})</span></div>'
        f'<div class="row-card-sub">{atype}{" · " + sub if sub else ""}</div>'
        f'<div class="row-card-sub">{"Última insp." if lang=="es" else "Last insp."}: {insp}'
        f'{"  ·  " + a["OOS_REASON"] if a["OOS_REASON"] else ""}</div></div>'
        f'<div style="text-align:right"><div style="font-size:20px">{ico}</div>'
        f'<div style="font-size:11px;color:#888">{slabel}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

if not assets:
    st.info("No assets found." if lang == "en" else "Sin activos encontrados.")

# ── Add asset (fleet_admin +) ──────────────────────────────────
if has_permission("fleet.manage"):
    st.divider()
    add_label = "➕ Agregar activo" if lang == "es" else "➕ Add new asset"
    with st.expander(add_label):
        asset_types = query_many("SELECT id, label_en, label_es FROM ASSET_TYPES ORDER BY label_en")
        at_map = {(a["LABEL_ES"] if lang=="es" else a["LABEL_EN"]): a["ID"] for a in asset_types}

        name      = st.text_input("Nombre *" if lang=="es" else "Name *")
        tag       = st.text_input("Etiqueta (QR/código) *" if lang=="es" else "Tag (QR/barcode) *")
        at_label  = st.selectbox("Tipo de activo" if lang=="es" else "Asset type", list(at_map.keys()))
        make      = st.text_input("Marca" if lang=="es" else "Make")
        model     = st.text_input("Modelo" if lang=="es" else "Model")
        year      = st.number_input("Año" if lang=="es" else "Year", 1990, 2030, 2020)
        serial    = st.text_input("Número de serie" if lang=="es" else "Serial number")
        fuel_opts = {"electric":"Eléctrico","propane":"Propano","gas":"Gas","diesel":"Diesel"}
        fuel      = st.selectbox("Combustible" if lang=="es" else "Fuel type",
                                 list(fuel_opts.values()) if lang=="es" else list(fuel_opts.keys()))
        notes     = st.text_area("Notas" if lang=="es" else "Notes")

        if st.button("Guardar activo" if lang=="es" else "Save asset",
                     use_container_width=True, type="primary"):
            if not name or not tag:
                st.error("Nombre y etiqueta son requeridos." if lang=="es"
                         else "Name and tag are required.")
            else:
                fuel_key = {v: k for k, v in fuel_opts.items()}.get(fuel, fuel)
                execute(
                    """INSERT INTO ASSETS (id,site_id,asset_type_id,tag,name,
                           make,model,year,serial_number,fuel_type,notes)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (str(uuid.uuid4()), site_id, at_map[at_label], tag, name,
                     make or None, model or None, int(year),
                     serial or None, fuel_key, notes or None)
                )
                st.success(f"'{'Activo' if lang=='es' else 'Asset'} {name}' {'guardado' if lang=='es' else 'saved'}.")
                st.rerun()
