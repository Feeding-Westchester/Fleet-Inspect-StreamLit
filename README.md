# Feeding Westchester Fleet Inspect — Snowflake + Streamlit

Safety inspection platform for 34 fleet assets at the Elmsford, NY warehouse.
Ported from Node.js/Express + Supabase to **Python/Streamlit + Snowflake**.

Covers: OSHA 1910.178 · DOT 49 CFR 396 · FDA FSMA · AIB International  
Users: 10 (4 managers, 6 operators) | Languages: English / Spanish

---

## Architecture

```
Browser
  └── Streamlit (Python, multi-page)
        ├── auth/jwt_auth.py       — login, JWT, RBAC (7 roles, 22 permissions)
        ├── db/connection.py       — Snowflake connector (cached)
        ├── utils/business_logic.py — inspection cascade, OOS, work orders
        ├── utils/i18n.py          — English/Spanish translation
        └── pages/
              00_login.py          — authentication
              01_dashboard.py      — KPIs, recent inspections, alerts
              02_new_inspection.py — bilingual checklist form
              03_assets.py         — 34 fleet assets, add/edit
              04_defects.py        — defect tracking + resolution
              05_work_orders.py    — create, assign, verify
              06_safety.py         — safety observations + actions
              07_temp_holds.py     — FDA FSMA temperature holds
              08_reports.py        — compliance, fleet health, operator stats
              09_operators.py      — operator roster management
              10_coaching.py       — coaching notes (self + manager views)
              11_notifications.py  — in-app notification inbox
              12_help.py           — bilingual help articles
        └── db/
              01_schema.sql        — 39-table Snowflake DDL
              02_seed.sql          — roles, permissions, test users
```

## Snowflake Setup (IT)

```sql
-- Run once as ACCOUNTADMIN
CREATE DATABASE FLEET_INSPECT;
CREATE SCHEMA FLEET_INSPECT.CORE;
CREATE WAREHOUSE FLEET_WH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=300 AUTO_RESUME=TRUE;

CREATE ROLE FLEET_INSPECT_ROLE;
GRANT USAGE ON DATABASE FLEET_INSPECT TO ROLE FLEET_INSPECT_ROLE;
GRANT USAGE ON SCHEMA FLEET_INSPECT.CORE TO ROLE FLEET_INSPECT_ROLE;
GRANT ALL ON ALL TABLES IN SCHEMA FLEET_INSPECT.CORE TO ROLE FLEET_INSPECT_ROLE;
GRANT ALL ON FUTURE TABLES IN SCHEMA FLEET_INSPECT.CORE TO ROLE FLEET_INSPECT_ROLE;
GRANT USAGE ON WAREHOUSE FLEET_WH TO ROLE FLEET_INSPECT_ROLE;

CREATE USER FLEET_INSPECT_SVC
    PASSWORD = '<generate-strong-password>'
    DEFAULT_ROLE = FLEET_INSPECT_ROLE
    DEFAULT_WAREHOUSE = FLEET_WH
    DEFAULT_NAMESPACE = 'FLEET_INSPECT.CORE';
GRANT ROLE FLEET_INSPECT_ROLE TO USER FLEET_INSPECT_SVC;

-- Then run db/01_schema.sql and db/02_seed.sql in FLEET_INSPECT.CORE context
```

## Local Development

```bash
# 1. Clone
git clone https://github.com/Feeding-Westchester/fleet-inspect-api
cd fleet-inspect-snowflake

# 2. Python environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Secrets
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with real Snowflake credentials

# 4. Database
# Run db/01_schema.sql then db/02_seed.sql in Snowflake (Snowsight or SnowSQL)
# Then hash passwords:
python scripts/hash_passwords.py   # see below

# 5. Run
streamlit run app.py
```

## Password Hashing

The seed file contains placeholder password hashes. After running the seed:

```python
# scripts/hash_passwords.py
import bcrypt, snowflake.connector, os

# Set your credentials as env vars for this one-time script
conn = snowflake.connector.connect(
    account=os.environ["SF_ACCOUNT"],
    user=os.environ["SF_USER"],
    password=os.environ["SF_PASSWORD"],
    database="FLEET_INSPECT", schema="CORE"
)
cur = conn.cursor()
default_pw = "Finspect2026!"
hashed = bcrypt.hashpw(default_pw.encode(), bcrypt.gensalt(12)).decode()
cur.execute("UPDATE USERS SET password_hash = %s WHERE password_hash LIKE '$2b$12$placeholder%'", (hashed,))
conn.commit()
print(f"Updated {cur.rowcount} users with hashed password.")
```

## Deployment (Streamlit Community Cloud or internal server)

1. Push this repo to GitHub under the Feeding Westchester org
2. Connect Streamlit Cloud to the repo
3. Add secrets via the Streamlit Cloud UI (Settings → Secrets)
4. Set `app.py` as the entry point

For on-prem: `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`
Reverse-proxy with nginx + TLS recommended.

## Roles & Permissions

| Role | Key Permissions |
|---|---|
| `operator_warehouse` | inspection.create, session.start/return, safety.create |
| `driver_delivery` | same as operator_warehouse |
| `supervisor` | + approval.temperature, approval.return_to_service, reports.read |
| `safety_manager` | safety.manage, reports.read, audit.read |
| `fleet_admin` | fleet.manage, operator.manage, templates.manage, workorder.verify |
| `maintenance_tech` | workorder.create/verify, defect.manage |
| `org_admin` | all 22 permissions |

## Business Logic: Inspection Cascade

```
Submit inspection
  └─ Any critical item = FAIL?
       ├── YES → asset.status = 'oos'
       │         create DEFECT (auto_generated=true, severity='critical')
       │         create WORK_ORDER (priority='critical')
       │         notify all supervisors + fleet admins
       └── NO  → result = pass/fail based on non-critical items
```

## Key Differences from Original (Supabase/Node.js)

| Concern | Before | Now |
|---|---|---|
| Database | Supabase (PostgreSQL) | Snowflake |
| Auth | Supabase Auth (JWT) | PyJWT + bcrypt + USERS table |
| Row-Level Security | Supabase RLS policies | Permission checks in Python layer |
| API | Node.js REST (19 endpoint groups) | Streamlit pages (no separate API needed) |
| App | Android (Kotlin, offline-first) | Streamlit web (browser, online) |
| Offline | Supported | Not required |
| Hosting | Render (Node) + Supabase cloud | Streamlit + Snowflake (both IT-managed) |
