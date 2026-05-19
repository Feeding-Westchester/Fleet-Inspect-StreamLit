"""Fleet Inspect — Operators Page"""
import streamlit as st
import os
import pandas as pd
import uuid
from auth.jwt_auth import require_auth, require_permission, current_user
from db.connection import query_many, execute
from utils.mobile import inject_mobile_css, page_header
from utils.i18n import t

st.set_page_config(page_title="Fleet Inspect – Operators", page_icon="👷", layout="wide")
inject_mobile_css()
require_auth()
require_permission("operator.manage")
user = current_user()
site_id = st.session_state.get("site_id")
st.title(f"👷 {t('nav_operators')}")

operators = query_many(
    """
    SELECT o.id, o.employee_id, o.first_name, o.last_name,
           o.license_number,
           TO_VARCHAR(o.license_expires_at, 'YYYY-MM-DD') AS license_expires,
           o.active,
           COUNT(i.id) AS total_inspections
    FROM OPERATORS o
    LEFT JOIN INSPECTIONS i ON i.operator_id = o.id
    WHERE o.site_id = %s
    GROUP BY o.id, o.employee_id, o.first_name, o.last_name,
             o.license_number, o.license_expires_at, o.active
    ORDER BY o.last_name
    """,
    (site_id,)
)
if operators:
    df = pd.DataFrame(operators)
    df.columns = [c.lower() for c in df.columns]
    df["active"] = df["active"].map({True: "✅ Active", False: "❌ Inactive"})
    st.dataframe(df[["employee_id", "first_name", "last_name", "license_number",
                      "license_expires", "active", "total_inspections"]],
                 use_container_width=True, hide_index=True)
else:
    st.info(t("no_data"))

st.divider()
with st.expander("➕ Add Operator"):
    with st.form("add_operator"):
        c1, c2 = st.columns(2)
        first_name  = c1.text_input("First Name *")
        last_name   = c2.text_input("Last Name *")
        employee_id = c1.text_input("Employee ID *")
        license_num = c2.text_input("License Number")
        lic_expires = st.date_input("License Expires")
        if st.form_submit_button("Add", type="primary"):
            if not first_name or not last_name or not employee_id:
                st.error("First name, last name, and employee ID are required.")
            else:
                execute(
                    """
                    INSERT INTO OPERATORS (id, site_id, employee_id, first_name,
                        last_name, license_number, license_expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (str(uuid.uuid4()), site_id, employee_id, first_name,
                     last_name, license_num or None,
                     str(lic_expires) if lic_expires else None)
                )
                st.success(f"Operator {first_name} {last_name} added.")
                st.rerun()
