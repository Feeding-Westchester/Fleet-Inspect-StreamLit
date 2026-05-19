"""
Fleet Inspect — Mobile-first CSS + layout helpers.

Call inject_mobile_css() at the top of every page (after set_page_config).
This patches Streamlit's default layout to be usable on a phone browser.

Key decisions:
- Sidebar hidden on mobile (<768px), replaced by a sticky bottom nav bar
- All st.columns() calls should use mobile_cols() so they stack on narrow screens
- Tap targets minimum 44px (WCAG / Apple HIG)
- Forms go full-width, no side-by-side inputs on mobile
- Tables replaced with card lists on pages where that's appropriate
"""

import streamlit as st
from auth.jwt_auth import has_permission, current_user, logout


MOBILE_CSS = """
<style>
/* ── Viewport ── */
@viewport { width: device-width; }

/* ── Hide Streamlit chrome on mobile ── */
@media (max-width: 768px) {
    [data-testid="stSidebar"]          { display: none !important; }
    [data-testid="collapsedControl"]   { display: none !important; }
    .block-container {
        padding: 0.75rem 0.75rem 5rem !important;
        max-width: 100% !important;
    }
}

/* ── Bottom nav bar (mobile only) ── */
.mobile-nav {
    display: none;
}
@media (max-width: 768px) {
    .mobile-nav {
        display: flex;
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: var(--background-color, #ffffff);
        border-top: 1px solid rgba(0,0,0,0.1);
        z-index: 9999;
        height: 56px;
        align-items: stretch;
    }
    .mobile-nav a {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        text-decoration: none;
        color: #888;
        font-size: 10px;
        font-weight: 500;
        padding: 4px 0;
        min-height: 44px;
        -webkit-tap-highlight-color: transparent;
        transition: color 0.15s;
    }
    .mobile-nav a.active { color: #534AB7; }
    .mobile-nav a svg    { width: 22px; height: 22px; stroke-width: 1.8; }
    .mobile-nav .nav-badge {
        position: absolute;
        top: 4px; right: calc(50% - 18px);
        background: #E24B4A;
        color: white;
        font-size: 9px;
        min-width: 16px; height: 16px;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        padding: 0 3px;
    }
    .mobile-nav a { position: relative; }
}

/* ── Desktop: keep sidebar, hide bottom nav ── */
@media (min-width: 769px) {
    .mobile-nav { display: none !important; }
}

/* ── Global tap target minimum ── */
button, .stButton > button, select, input, textarea {
    min-height: 44px !important;
    font-size: 16px !important;  /* prevents iOS zoom on focus */
}

/* ── Streamlit button full-width on mobile ── */
@media (max-width: 768px) {
    .stButton > button { width: 100% !important; }

    /* Stack columns on mobile */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* Full-width selects and inputs */
    .stSelectbox, .stTextInput, .stTextArea, .stNumberInput {
        width: 100% !important;
    }

    /* Tighter metric cards */
    [data-testid="stMetric"] {
        padding: 0.5rem !important;
    }

    /* Reduce heading size */
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.1rem !important; }
    h3 { font-size: 1rem !important; }

    /* Expanders full width */
    .streamlit-expanderHeader { font-size: 15px !important; }

    /* Dataframes scroll horizontally instead of overflowing */
    [data-testid="stDataFrame"] { overflow-x: auto !important; }
}

/* ── Checklist item cards ── */
.checklist-card {
    border: 1px solid rgba(0,0,0,0.1);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 10px;
    background: white;
}
.checklist-card.critical-item {
    border-left: 4px solid #E24B4A;
}

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}
.badge-pass    { background:#EAF3DE; color:#27500A; }
.badge-fail    { background:#FCEBEB; color:#791F1F; }
.badge-oos     { background:#FCEBEB; color:#791F1F; }
.badge-avail   { background:#EAF3DE; color:#27500A; }
.badge-inuse   { background:#FAEEDA; color:#633806; }
.badge-maint   { background:#E6F1FB; color:#0C447C; }
.badge-open    { background:#FAEEDA; color:#633806; }
.badge-crit    { background:#FCEBEB; color:#791F1F; }
.badge-pending { background:#FAEEDA; color:#633806; }
.badge-verified{ background:#EAF3DE; color:#27500A; }

/* ── Asset / inspection row cards (replaces tables on mobile) ── */
.row-card {
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: white;
}
.row-card-title   { font-size: 14px; font-weight: 600; color: #1a1a1a; }
.row-card-sub     { font-size: 12px; color: #666; margin-top: 2px; }

/* ── Alert strips ── */
.alert-strip {
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    font-size: 13px;
    display: flex;
    gap: 8px;
    align-items: flex-start;
}
.alert-danger  { background:#FCEBEB; color:#791F1F; border-left: 3px solid #E24B4A; border-radius: 0 8px 8px 0; }
.alert-info    { background:#E6F1FB; color:#0C447C; border-left: 3px solid #378ADD; border-radius: 0 8px 8px 0; }
.alert-warning { background:#FAEEDA; color:#633806; border-left: 3px solid #EF9F27; border-radius: 0 8px 8px 0; }
.alert-success { background:#EAF3DE; color:#27500A; border-left: 3px solid #639922; border-radius: 0 8px 8px 0; }
</style>
"""

# ── SVG icons for bottom nav ──────────────────────────────────
_ICONS = {
    "dashboard": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    "inspection": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12l2 2 4-4"/></svg>',
    "assets": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg>',
    "alerts": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>',
    "more": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>',
}


def _nav_link(icon_key: str, label: str, page: str, current: str, badge: int = 0) -> str:
    active = "active" if current == page else ""
    badge_html = f'<span class="nav-badge">{badge}</span>' if badge > 0 else ""
    return (
        f'<a href="{page}" class="{active}">'
        f'{_ICONS[icon_key]}{badge_html}'
        f'<span>{label}</span>'
        f'</a>'
    )


def inject_mobile_css():
    """Call once per page after set_page_config."""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def bottom_nav(current_page: str, unread_count: int = 0, lang: str = "en"):
    """
    Renders a fixed bottom navigation bar (visible on mobile only).
    current_page should match the page filename stem, e.g. '01_dashboard'.
    """
    labels = {
        "en": {"home": "Home", "inspect": "Inspect",
               "assets": "Assets", "alerts": "Alerts", "more": "More"},
        "es": {"home": "Inicio", "inspect": "Inspeccionar",
               "assets": "Activos", "alerts": "Alertas", "more": "Más"},
    }[lang]

    # Map page stems to nav keys
    page_map = {
        "01_dashboard":       "dashboard",
        "02_new_inspection":  "inspection",
        "03_assets":          "assets",
        "11_notifications":   "alerts",
    }
    active = page_map.get(current_page, "more")

    html = '<nav class="mobile-nav" role="navigation" aria-label="Main navigation">'
    html += _nav_link("dashboard", labels["home"],    "01_dashboard.py",      active)
    html += _nav_link("inspection", labels["inspect"], "02_new_inspection.py", active)
    html += _nav_link("assets",    labels["assets"],  "03_assets.py",         active)
    html += _nav_link("alerts",    labels["alerts"],  "11_notifications.py",  active, unread_count)
    html += _nav_link("more",      labels["more"],    "01_dashboard.py",      active)
    html += '</nav>'
    st.markdown(html, unsafe_allow_html=True)


def sidebar_nav(lang: str = "en"):
    """
    Full sidebar nav for desktop. Hidden on mobile via CSS.
    Call inside a `with st.sidebar:` block.
    """
    user = current_user()
    t = {
        "en": {
            "dashboard": "Dashboard", "inspections": "New inspection",
            "assets": "Assets", "defects": "Defects", "workorders": "Work orders",
            "safety": "Safety observations", "temp": "Temperature holds",
            "reports": "Reports", "operators": "Operators", "coaching": "Coaching",
            "notifications": "Notifications", "help": "Help", "logout": "Log out",
        },
        "es": {
            "dashboard": "Panel", "inspections": "Nueva inspección",
            "assets": "Activos", "defects": "Defectos", "workorders": "Órdenes de trabajo",
            "safety": "Observaciones de seguridad", "temp": "Retenciones de temperatura",
            "reports": "Informes", "operators": "Operadores", "coaching": "Capacitación",
            "notifications": "Notificaciones", "help": "Ayuda", "logout": "Cerrar sesión",
        },
    }[lang]

    st.markdown("### 🚛 Fleet Inspect")
    if user:
        st.caption(f"👤 {user['first_name']} {user['last_name']}")
        st.caption(f"📍 {st.session_state.get('role_name','').replace('_',' ').title()}")
    st.divider()

    st.page_link("pages/01_dashboard.py",      label=t["dashboard"],      icon="📊")
    st.page_link("pages/02_new_inspection.py", label=t["inspections"],    icon="📋")
    st.page_link("pages/03_assets.py",         label=t["assets"],         icon="🏭")
    st.page_link("pages/04_defects.py",        label=t["defects"],        icon="⚠️")
    st.page_link("pages/05_work_orders.py",    label=t["workorders"],     icon="🔧")
    st.page_link("pages/06_safety.py",         label=t["safety"],         icon="🦺")
    st.page_link("pages/07_temp_holds.py",     label=t["temp"],           icon="🌡️")
    if has_permission("reports.read"):
        st.page_link("pages/08_reports.py",    label=t["reports"],        icon="📈")
    if has_permission("operator.manage"):
        st.page_link("pages/09_operators.py",  label=t["operators"],      icon="👷")
    st.page_link("pages/10_coaching.py",       label=t["coaching"],       icon="📝")
    st.page_link("pages/11_notifications.py",  label=t["notifications"],  icon="🔔")
    st.page_link("pages/12_help.py",           label=t["help"],           icon="❓")
    st.divider()
    if st.button(t["logout"], use_container_width=True):
        logout()
        st.switch_page("pages/00_login.py")


def page_header(title: str, lang: str = "en", unread: int = 0):
    """Renders sidebar (desktop) + bottom nav (mobile) + page title."""
    with st.sidebar:
        sidebar_nav(lang)
    bottom_nav(
        current_page=title,   # caller passes __file__ stem
        unread_count=unread,
        lang=lang,
    )
