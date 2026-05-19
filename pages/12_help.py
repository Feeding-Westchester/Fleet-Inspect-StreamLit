"""Fleet Inspect — Help Articles"""
import streamlit as st
import os
from auth.jwt_auth import require_auth, current_user
from db.connection import query_many
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t

st.set_page_config(page_title="Fleet Inspect – Help", page_icon="❓", layout="wide")
inject_mobile_css()
require_auth()
user = current_user()
lang = user.get("preferred_lang", "en")
page_header(os.path.splitext(os.path.basename(__file__))[0], lang)
st.title(f"❓ {t('nav_help')}")

search = st.text_input(t("search"), placeholder="Search help articles…")

articles = query_many(
    f"""
    SELECT id, slug, category,
           {'title_es' if lang=='es' else 'title_en'} AS title,
           {'body_es' if lang=='es' else 'body_en'} AS body,
           sort_order
    FROM HELP_ARTICLES
    WHERE published = TRUE
      {'AND (LOWER(title_en) LIKE %s OR LOWER(title_es) LIKE %s OR LOWER(body_en) LIKE %s)' if search else ''}
    ORDER BY category, sort_order
    """,
    (f"%{search.lower()}%",) * 3 if search else ()
)

if articles:
    current_cat = None
    for a in articles:
        if a["CATEGORY"] != current_cat:
            st.subheader(a["CATEGORY"] or "General")
            current_cat = a["CATEGORY"]
        with st.expander(a["TITLE"] or a["SLUG"]):
            st.markdown(a["BODY"] or "_Content coming soon._")
else:
    st.info("No help articles found." if not search else f"No results for '{search}'.")

st.divider()
st.caption("Fleet Inspect — Feeding Westchester | Elmsford, NY 10523")
st.caption("Compliance: OSHA 1910.178 · DOT 49 CFR 396 · FDA FSMA · AIB International")
