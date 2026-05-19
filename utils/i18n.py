"""
Fleet Inspect — Bilingual (English / Spanish) translation helper.
"""

from auth.jwt_auth import current_lang

# ── String table ──────────────────────────────────────────────
_STRINGS: dict[str, dict[str, str]] = {
    # Navigation
    "nav_dashboard":        {"en": "Dashboard",          "es": "Panel"},
    "nav_inspections":      {"en": "Inspections",         "es": "Inspecciones"},
    "nav_assets":           {"en": "Assets",              "es": "Activos"},
    "nav_defects":          {"en": "Defects",             "es": "Defectos"},
    "nav_work_orders":      {"en": "Work Orders",         "es": "Órdenes de trabajo"},
    "nav_safety":           {"en": "Safety Observations", "es": "Observaciones de seguridad"},
    "nav_temp_holds":       {"en": "Temperature Holds",   "es": "Retenciones de temperatura"},
    "nav_reports":          {"en": "Reports",             "es": "Informes"},
    "nav_coaching":         {"en": "Coaching",            "es": "Capacitación"},
    "nav_notifications":    {"en": "Notifications",       "es": "Notificaciones"},
    "nav_help":             {"en": "Help",                "es": "Ayuda"},
    "nav_operators":        {"en": "Operators",           "es": "Operadores"},
    "nav_logout":           {"en": "Log out",             "es": "Cerrar sesión"},
    # Auth
    "login_title":          {"en": "Fleet Inspect",       "es": "Fleet Inspect"},
    "login_email":          {"en": "Email",               "es": "Correo electrónico"},
    "login_password":       {"en": "Password",            "es": "Contraseña"},
    "login_button":         {"en": "Sign in",             "es": "Iniciar sesión"},
    "login_error":          {"en": "Invalid email or password.", "es": "Correo o contraseña incorrectos."},
    # Inspections
    "insp_new":             {"en": "New Inspection",      "es": "Nueva inspección"},
    "insp_asset":           {"en": "Asset",               "es": "Activo"},
    "insp_operator":        {"en": "Operator",            "es": "Operador"},
    "insp_type":            {"en": "Inspection Type",     "es": "Tipo de inspección"},
    "insp_pre_trip":        {"en": "Pre-Trip",            "es": "Previo al viaje"},
    "insp_post_trip":       {"en": "Post-Trip",           "es": "Posterior al viaje"},
    "insp_periodic":        {"en": "Periodic",            "es": "Periódica"},
    "insp_rts":             {"en": "Return to Service",   "es": "Retorno al servicio"},
    "insp_submit":          {"en": "Submit Inspection",   "es": "Enviar inspección"},
    "insp_pass":            {"en": "Pass",                "es": "Aprobado"},
    "insp_fail":            {"en": "Fail",                "es": "Reprobado"},
    "insp_na":              {"en": "N/A",                 "es": "N/A"},
    "insp_notes":           {"en": "Notes",               "es": "Notas"},
    "insp_critical_warn":   {"en": "⚠️ Critical failure — asset will be placed Out of Service.",
                             "es": "⚠️ Falla crítica — el activo quedará fuera de servicio."},
    # Assets
    "asset_status_available": {"en": "Available",         "es": "Disponible"},
    "asset_status_in_use":    {"en": "In Use",            "es": "En uso"},
    "asset_status_oos":       {"en": "Out of Service",    "es": "Fuera de servicio"},
    "asset_status_maint":     {"en": "Maintenance",       "es": "Mantenimiento"},
    # General
    "save":                 {"en": "Save",                "es": "Guardar"},
    "cancel":               {"en": "Cancel",              "es": "Cancelar"},
    "submit":               {"en": "Submit",              "es": "Enviar"},
    "confirm":              {"en": "Confirm",             "es": "Confirmar"},
    "status":               {"en": "Status",              "es": "Estado"},
    "date":                 {"en": "Date",                "es": "Fecha"},
    "action":               {"en": "Action",              "es": "Acción"},
    "search":               {"en": "Search",              "es": "Buscar"},
    "filter":               {"en": "Filter",              "es": "Filtrar"},
    "export":               {"en": "Export CSV",          "es": "Exportar CSV"},
    "no_data":              {"en": "No records found.",   "es": "No se encontraron registros."},
    "loading":              {"en": "Loading…",            "es": "Cargando…"},
}


def t(key: str) -> str:
    """Translate key to the current user's language, fallback to English."""
    lang = current_lang()
    entry = _STRINGS.get(key, {})
    return entry.get(lang) or entry.get("en") or key
