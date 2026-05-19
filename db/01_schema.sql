-- ============================================================
-- Fleet Inspect — Snowflake Schema
-- Ported from Supabase/PostgreSQL (39 tables)
-- Covers: OSHA 1910.178 | DOT 49 CFR 396 | FDA FSMA | AIB
-- ============================================================

-- ── DATABASE / WAREHOUSE ────────────────────────────────────
-- Run once by IT admin:
-- CREATE DATABASE FLEET_INSPECT;
-- CREATE SCHEMA FLEET_INSPECT.CORE;
-- USE SCHEMA FLEET_INSPECT.CORE;

-- ── REFERENCE / LOOKUP TABLES ───────────────────────────────

CREATE TABLE IF NOT EXISTS COMPLIANCE_STANDARDS (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    code        VARCHAR(64)   NOT NULL UNIQUE,   -- e.g. OSHA_1910_178
    label       VARCHAR(256)  NOT NULL,
    description VARCHAR(1024),
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS SITES (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    name            VARCHAR(256)  NOT NULL,
    address         VARCHAR(512),
    city            VARCHAR(128),
    state           VARCHAR(64),
    zip             VARCHAR(16),
    timezone        VARCHAR(64)   DEFAULT 'America/New_York',
    active          BOOLEAN       DEFAULT TRUE,
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS SITE_POLICIES (
    id                          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    site_id                     VARCHAR(36)   NOT NULL REFERENCES SITES(id),
    inspection_interval_hours   INT           DEFAULT 8,
    pre_trip_required           BOOLEAN       DEFAULT TRUE,
    post_trip_required          BOOLEAN       DEFAULT TRUE,
    temp_hold_auto_approve_min  INT           DEFAULT 30,
    max_oos_assets_pct          NUMERIC(5,2)  DEFAULT 20.0,
    created_at                  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at                  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── USERS / AUTH ─────────────────────────────────────────────
-- Snowflake does not have built-in row-level auth like Supabase.
-- Authentication is handled by Streamlit + JWT (see auth/jwt_auth.py).
-- Users are stored here; passwords are hashed (bcrypt) in app layer.

CREATE TABLE IF NOT EXISTS USERS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    email           VARCHAR(256)  NOT NULL UNIQUE,
    password_hash   VARCHAR(256)  NOT NULL,
    first_name      VARCHAR(128),
    last_name       VARCHAR(128),
    employee_id     VARCHAR(64),
    phone           VARCHAR(32),
    preferred_lang  VARCHAR(8)    DEFAULT 'en',   -- en | es
    site_id         VARCHAR(36)   REFERENCES SITES(id),
    active          BOOLEAN       DEFAULT TRUE,
    last_login_at   TIMESTAMP_NTZ,
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ROLES (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    name        VARCHAR(64)   NOT NULL UNIQUE,
    -- operator_warehouse | driver_delivery | supervisor |
    -- safety_manager | fleet_admin | maintenance_tech | org_admin
    label       VARCHAR(128),
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS PERMISSIONS (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    code        VARCHAR(128)  NOT NULL UNIQUE,
    -- inspection.create | session.start | session.return |
    -- safety.create | safety.manage | coaching.read_self |
    -- approval.temperature | approval.return_to_service |
    -- reports.read | fleet.manage | operator.manage |
    -- templates.manage | audit.read | notifications.manage |
    -- workorder.create | workorder.verify | defect.manage |
    -- amendment.create | history.read | help.read |
    -- sync.push | sync.pull
    description VARCHAR(256),
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ROLE_PERMISSIONS (
    role_id         VARCHAR(36) NOT NULL REFERENCES ROLES(id),
    permission_id   VARCHAR(36) NOT NULL REFERENCES PERMISSIONS(id),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS USER_ROLE_GRANTS (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    user_id     VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    role_id     VARCHAR(36)   NOT NULL REFERENCES ROLES(id),
    site_id     VARCHAR(36)   REFERENCES SITES(id),   -- NULL = org-wide
    granted_by  VARCHAR(36)   REFERENCES USERS(id),
    granted_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    revoked_at  TIMESTAMP_NTZ,
    UNIQUE (user_id, role_id, site_id)
);

CREATE TABLE IF NOT EXISTS REFRESH_TOKENS (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    user_id     VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    token_hash  VARCHAR(256)  NOT NULL UNIQUE,
    expires_at  TIMESTAMP_NTZ NOT NULL,
    revoked_at  TIMESTAMP_NTZ,
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── ASSETS ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ASSET_TYPES (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    code        VARCHAR(64)   NOT NULL UNIQUE,
    -- forklift | pallet_jack | reach_truck | order_picker |
    -- box_truck | cargo_van | refrigerated_truck | trailer
    label_en    VARCHAR(128),
    label_es    VARCHAR(128),
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ASSETS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    site_id         VARCHAR(36)   NOT NULL REFERENCES SITES(id),
    asset_type_id   VARCHAR(36)   NOT NULL REFERENCES ASSET_TYPES(id),
    tag             VARCHAR(64)   NOT NULL UNIQUE,   -- QR / barcode value
    name            VARCHAR(256)  NOT NULL,
    make            VARCHAR(128),
    model           VARCHAR(128),
    year            INT,
    serial_number   VARCHAR(128),
    license_plate   VARCHAR(32),
    vin             VARCHAR(32),
    capacity_lbs    NUMERIC(10,2),
    fuel_type       VARCHAR(32),   -- electric | propane | gas | diesel
    status          VARCHAR(32)    DEFAULT 'available',
    -- available | in_use | oos | maintenance | retired
    oos_reason      VARCHAR(512),
    oos_since       TIMESTAMP_NTZ,
    last_inspected  TIMESTAMP_NTZ,
    notes           VARCHAR(2048),
    active          BOOLEAN        DEFAULT TRUE,
    created_at      TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),
    updated_at      TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);

-- ── OPERATORS ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS OPERATORS (
    id                  VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    user_id             VARCHAR(36)   REFERENCES USERS(id),
    site_id             VARCHAR(36)   NOT NULL REFERENCES SITES(id),
    employee_id         VARCHAR(64)   UNIQUE,
    first_name          VARCHAR(128)  NOT NULL,
    last_name           VARCHAR(128)  NOT NULL,
    license_number      VARCHAR(64),
    license_expires_at  DATE,
    certified_assets    VARIANT,      -- JSON array of asset_type codes
    active              BOOLEAN       DEFAULT TRUE,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── CHECKLIST TEMPLATES ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS CHECKLIST_TEMPLATES (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    site_id         VARCHAR(36)   REFERENCES SITES(id),   -- NULL = global
    asset_type_id   VARCHAR(36)   NOT NULL REFERENCES ASSET_TYPES(id),
    name_en         VARCHAR(256)  NOT NULL,
    name_es         VARCHAR(256),
    version         INT           DEFAULT 1,
    active          BOOLEAN       DEFAULT TRUE,
    created_by      VARCHAR(36)   REFERENCES USERS(id),
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS CHECKLIST_ITEMS (
    id                  VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    template_id         VARCHAR(36)   NOT NULL REFERENCES CHECKLIST_TEMPLATES(id),
    sort_order          INT           NOT NULL,
    category_en         VARCHAR(128),
    category_es         VARCHAR(128),
    label_en            VARCHAR(512)  NOT NULL,
    label_es            VARCHAR(512),
    response_type       VARCHAR(32)   DEFAULT 'pass_fail',
    -- pass_fail | numeric | text | photo_required
    critical            BOOLEAN       DEFAULT FALSE,
    -- TRUE → critical fail triggers auto-defect + OOS lock
    compliance_codes    VARIANT,      -- JSON array of standard codes
    help_text_en        VARCHAR(1024),
    help_text_es        VARCHAR(1024),
    active              BOOLEAN       DEFAULT TRUE,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── INSPECTION SESSIONS ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS SESSIONS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    site_id         VARCHAR(36)   NOT NULL REFERENCES SITES(id),
    asset_id        VARCHAR(36)   NOT NULL REFERENCES ASSETS(id),
    operator_id     VARCHAR(36)   NOT NULL REFERENCES OPERATORS(id),
    started_by      VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    status          VARCHAR(32)   DEFAULT 'active',
    -- active | handed_off | returned | closed
    started_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    handed_off_at   TIMESTAMP_NTZ,
    handed_off_to   VARCHAR(36)   REFERENCES OPERATORS(id),
    returned_at     TIMESTAMP_NTZ,
    closed_at       TIMESTAMP_NTZ,
    notes           VARCHAR(2048),
    client_event_id VARCHAR(128)  UNIQUE,   -- idempotency key
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── INSPECTIONS ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS INSPECTIONS (
    id                  VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    session_id          VARCHAR(36)   REFERENCES SESSIONS(id),
    asset_id            VARCHAR(36)   NOT NULL REFERENCES ASSETS(id),
    operator_id         VARCHAR(36)   NOT NULL REFERENCES OPERATORS(id),
    submitted_by        VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    template_id         VARCHAR(36)   NOT NULL REFERENCES CHECKLIST_TEMPLATES(id),
    inspection_type     VARCHAR(32)   DEFAULT 'pre_trip',
    -- pre_trip | post_trip | periodic | return_to_service
    status              VARCHAR(32)   DEFAULT 'submitted',
    -- submitted | passed | failed | amended
    overall_result      VARCHAR(32),
    -- pass | fail | conditional
    critical_fail_count INT           DEFAULT 0,
    submitted_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    completed_at        TIMESTAMP_NTZ,
    client_event_id     VARCHAR(128)  UNIQUE,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS INSPECTION_RESPONSES (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    inspection_id   VARCHAR(36)   NOT NULL REFERENCES INSPECTIONS(id),
    item_id         VARCHAR(36)   NOT NULL REFERENCES CHECKLIST_ITEMS(id),
    result          VARCHAR(32),  -- pass | fail | na
    numeric_value   NUMERIC(10,2),
    text_value      VARCHAR(2048),
    photo_urls      VARIANT,      -- JSON array
    notes           VARCHAR(1024),
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS INSPECTION_AMENDMENTS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    inspection_id   VARCHAR(36)   NOT NULL REFERENCES INSPECTIONS(id),
    amended_by      VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    reason          VARCHAR(1024) NOT NULL,
    changes         VARIANT       NOT NULL,   -- JSON diff
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── DEFECTS ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS DEFECTS (
    id                  VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    asset_id            VARCHAR(36)   NOT NULL REFERENCES ASSETS(id),
    inspection_id       VARCHAR(36)   REFERENCES INSPECTIONS(id),
    inspection_item_id  VARCHAR(36)   REFERENCES CHECKLIST_ITEMS(id),
    reported_by         VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    severity            VARCHAR(32)   DEFAULT 'major',
    -- minor | major | critical
    description         VARCHAR(2048) NOT NULL,
    status              VARCHAR(32)   DEFAULT 'open',
    -- open | in_progress | resolved | closed
    auto_generated      BOOLEAN       DEFAULT FALSE,
    oos_triggered       BOOLEAN       DEFAULT FALSE,
    resolved_at         TIMESTAMP_NTZ,
    resolved_by         VARCHAR(36)   REFERENCES USERS(id),
    resolution_notes    VARCHAR(2048),
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── WORK ORDERS ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS WORK_ORDERS (
    id                  VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    asset_id            VARCHAR(36)   NOT NULL REFERENCES ASSETS(id),
    defect_id           VARCHAR(36)   REFERENCES DEFECTS(id),
    created_by          VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    assigned_to         VARCHAR(36)   REFERENCES USERS(id),
    priority            VARCHAR(32)   DEFAULT 'normal',
    -- low | normal | high | critical
    status              VARCHAR(32)   DEFAULT 'open',
    -- open | in_progress | pending_verification | verified | closed
    description         VARCHAR(2048) NOT NULL,
    estimated_hours     NUMERIC(6,2),
    actual_hours        NUMERIC(6,2),
    parts_used          VARIANT,      -- JSON array
    verified_by         VARCHAR(36)   REFERENCES USERS(id),
    verified_at         TIMESTAMP_NTZ,
    completed_at        TIMESTAMP_NTZ,
    closed_at           TIMESTAMP_NTZ,
    notes               VARCHAR(2048),
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── RETURNS ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS RETURNS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    session_id      VARCHAR(36)   NOT NULL REFERENCES SESSIONS(id),
    asset_id        VARCHAR(36)   NOT NULL REFERENCES ASSETS(id),
    operator_id     VARCHAR(36)   NOT NULL REFERENCES OPERATORS(id),
    submitted_by    VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    fuel_level      VARCHAR(32),
    damage_noted    BOOLEAN       DEFAULT FALSE,
    damage_notes    VARCHAR(1024),
    photo_urls      VARIANT,
    client_event_id VARCHAR(128)  UNIQUE,
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── SAFETY OBSERVATIONS ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS SAFETY_OBSERVATIONS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    site_id         VARCHAR(36)   NOT NULL REFERENCES SITES(id),
    asset_id        VARCHAR(36)   REFERENCES ASSETS(id),
    reported_by     VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    category        VARCHAR(64),
    -- near_miss | unsafe_condition | unsafe_act | positive
    severity        VARCHAR(32)   DEFAULT 'medium',
    description     VARCHAR(2048) NOT NULL,
    location        VARCHAR(256),
    photo_urls      VARIANT,
    status          VARCHAR(32)   DEFAULT 'open',
    -- open | under_review | action_taken | closed
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS SAFETY_OBSERVATION_ACTIONS (
    id                  VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    observation_id      VARCHAR(36)   NOT NULL REFERENCES SAFETY_OBSERVATIONS(id),
    taken_by            VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    action_type         VARCHAR(64),
    description         VARCHAR(2048) NOT NULL,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── TEMPERATURE HOLDS ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS TEMPERATURE_HOLDS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    asset_id        VARCHAR(36)   NOT NULL REFERENCES ASSETS(id),
    session_id      VARCHAR(36)   REFERENCES SESSIONS(id),
    reported_by     VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    temp_reading    NUMERIC(6,2)  NOT NULL,
    temp_unit       VARCHAR(4)    DEFAULT 'F',
    threshold_min   NUMERIC(6,2),
    threshold_max   NUMERIC(6,2),
    product_desc    VARCHAR(512),
    status          VARCHAR(32)   DEFAULT 'pending',
    -- pending | approved | rejected | escalated
    reviewed_by     VARCHAR(36)   REFERENCES USERS(id),
    reviewed_at     TIMESTAMP_NTZ,
    review_notes    VARCHAR(1024),
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── COACHING ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS COACHING_NOTES (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    operator_id     VARCHAR(36)   NOT NULL REFERENCES OPERATORS(id),
    authored_by     VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    note_type       VARCHAR(32)   DEFAULT 'general',
    -- general | corrective | commendation | training
    body            VARCHAR(4096) NOT NULL,
    private         BOOLEAN       DEFAULT FALSE,
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── NOTIFICATIONS ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS NOTIFICATIONS (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    user_id     VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    type        VARCHAR(64)   NOT NULL,
    -- defect_created | oos_triggered | work_order_assigned |
    -- temp_hold_pending | inspection_overdue | safety_obs_created
    title       VARCHAR(256)  NOT NULL,
    body        VARCHAR(1024),
    entity_type VARCHAR(64),
    entity_id   VARCHAR(36),
    read_at     TIMESTAMP_NTZ,
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── AUDIT LOG ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS AUDIT_LOG (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    user_id     VARCHAR(36)   REFERENCES USERS(id),
    action      VARCHAR(128)  NOT NULL,
    entity_type VARCHAR(64),
    entity_id   VARCHAR(36),
    old_values  VARIANT,      -- JSON snapshot before
    new_values  VARIANT,      -- JSON snapshot after
    ip_address  VARCHAR(64),
    user_agent  VARCHAR(512),
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── HELP ARTICLES ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS HELP_ARTICLES (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    slug        VARCHAR(128)  NOT NULL UNIQUE,
    title_en    VARCHAR(256)  NOT NULL,
    title_es    VARCHAR(256),
    body_en     VARCHAR(16384) NOT NULL,
    body_es     VARCHAR(16384),
    category    VARCHAR(64),
    sort_order  INT           DEFAULT 0,
    published   BOOLEAN       DEFAULT TRUE,
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── HISTORY / EVENT LOG ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS HISTORY_EVENTS (
    id          VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    site_id     VARCHAR(36)   REFERENCES SITES(id),
    user_id     VARCHAR(36)   REFERENCES USERS(id),
    entity_type VARCHAR(64),
    entity_id   VARCHAR(36),
    event_type  VARCHAR(128)  NOT NULL,
    payload     VARIANT,
    created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── SYNC QUEUE (replaces Supabase realtime for offline buffer) ─
-- Not needed now that offline is not a requirement.
-- Retained as a lightweight change-feed for future integrations.

CREATE TABLE IF NOT EXISTS SYNC_EVENTS (
    id              VARCHAR(36)   DEFAULT UUID_STRING() PRIMARY KEY,
    user_id         VARCHAR(36)   NOT NULL REFERENCES USERS(id),
    direction       VARCHAR(8)    DEFAULT 'push',   -- push | pull
    entity_type     VARCHAR(64),
    entity_id       VARCHAR(36),
    payload         VARIANT,
    client_event_id VARCHAR(128),
    processed_at    TIMESTAMP_NTZ,
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
