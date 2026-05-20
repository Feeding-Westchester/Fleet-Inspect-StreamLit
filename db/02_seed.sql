-- ============================================================
-- Fleet Inspect — Seed Data
-- Run after 01_schema.sql
-- All UUID_STRING() calls use SELECT form (Snowflake VALUES clause restriction)
-- ============================================================

-- ── COMPLIANCE STANDARDS ─────────────────────────────────────
INSERT INTO COMPLIANCE_STANDARDS (id, code, label)
SELECT UUID_STRING(), 'OSHA_1910_178', 'OSHA 1910.178 – Powered Industrial Trucks' UNION ALL
SELECT UUID_STRING(), 'DOT_49_CFR_396', 'DOT 49 CFR Part 396 – Vehicle Inspection & Maintenance' UNION ALL
SELECT UUID_STRING(), 'FDA_FSMA',       'FDA FSMA – Food Safety Modernization Act' UNION ALL
SELECT UUID_STRING(), 'AIB_INTL',       'AIB International – Food Safety Standards';

-- ── SITE ─────────────────────────────────────────────────────
INSERT INTO SITES (id, name, address, city, state, zip, timezone) VALUES
  ('site-elmsford-01', 'Feeding Westchester – Elmsford Warehouse',
   '200 Clearbrook Rd', 'Elmsford', 'NY', '10523', 'America/New_York');

INSERT INTO SITE_POLICIES (site_id, inspection_interval_hours, pre_trip_required,
    post_trip_required, temp_hold_auto_approve_min, max_oos_assets_pct)
VALUES ('site-elmsford-01', 8, TRUE, TRUE, 30, 20.0);

-- ── ROLES ────────────────────────────────────────────────────
INSERT INTO ROLES (id, name, label) VALUES
  ('role-op-wh',     'operator_warehouse',  'Warehouse Operator'),
  ('role-driver',    'driver_delivery',     'Delivery Driver'),
  ('role-super',     'supervisor',          'Supervisor'),
  ('role-safety',    'safety_manager',      'Safety Manager'),
  ('role-fleet',     'fleet_admin',         'Fleet Administrator'),
  ('role-maint',     'maintenance_tech',    'Maintenance Technician'),
  ('role-orgadmin',  'org_admin',           'Organization Administrator');

-- ── PERMISSIONS ──────────────────────────────────────────────
INSERT INTO PERMISSIONS (id, code, description) VALUES
  ('perm-01', 'inspection.create',          'Submit a new inspection'),
  ('perm-02', 'session.start',              'Start an equipment session'),
  ('perm-03', 'session.return',             'Return equipment at end of session'),
  ('perm-04', 'safety.create',              'File a safety observation'),
  ('perm-05', 'safety.manage',              'Manage safety observations'),
  ('perm-06', 'coaching.read_self',         'View own coaching notes'),
  ('perm-07', 'approval.temperature',       'Approve/reject temperature holds'),
  ('perm-08', 'approval.return_to_service', 'Approve return-to-service after OOS'),
  ('perm-09', 'reports.read',               'View compliance and analytics reports'),
  ('perm-10', 'fleet.manage',               'Add/edit fleet assets'),
  ('perm-11', 'operator.manage',            'Add/edit operators'),
  ('perm-12', 'templates.manage',           'Create/edit checklist templates'),
  ('perm-13', 'audit.read',                 'Read audit log'),
  ('perm-14', 'notifications.manage',       'Manage system notifications'),
  ('perm-15', 'workorder.create',           'Create work orders'),
  ('perm-16', 'workorder.verify',           'Verify completed work orders'),
  ('perm-17', 'defect.manage',              'Manage defects'),
  ('perm-18', 'amendment.create',           'Amend submitted inspections'),
  ('perm-19', 'history.read',               'View event history'),
  ('perm-20', 'help.read',                  'Access help articles'),
  ('perm-21', 'sync.push',                  'Push sync events'),
  ('perm-22', 'sync.pull',                  'Pull sync events');

-- ── ROLE → PERMISSION MAPPINGS ───────────────────────────────
-- operator_warehouse
INSERT INTO ROLE_PERMISSIONS VALUES
  ('role-op-wh', 'perm-01'), ('role-op-wh', 'perm-02'), ('role-op-wh', 'perm-03'),
  ('role-op-wh', 'perm-04'), ('role-op-wh', 'perm-06'), ('role-op-wh', 'perm-20'),
  ('role-op-wh', 'perm-21'), ('role-op-wh', 'perm-22');

-- driver_delivery
INSERT INTO ROLE_PERMISSIONS VALUES
  ('role-driver', 'perm-01'), ('role-driver', 'perm-02'), ('role-driver', 'perm-03'),
  ('role-driver', 'perm-04'), ('role-driver', 'perm-06'), ('role-driver', 'perm-20'),
  ('role-driver', 'perm-21'), ('role-driver', 'perm-22');

-- supervisor
INSERT INTO ROLE_PERMISSIONS VALUES
  ('role-super', 'perm-01'), ('role-super', 'perm-02'), ('role-super', 'perm-03'),
  ('role-super', 'perm-04'), ('role-super', 'perm-05'), ('role-super', 'perm-06'),
  ('role-super', 'perm-07'), ('role-super', 'perm-08'), ('role-super', 'perm-09'),
  ('role-super', 'perm-15'), ('role-super', 'perm-18'), ('role-super', 'perm-19'),
  ('role-super', 'perm-20'), ('role-super', 'perm-21'), ('role-super', 'perm-22');

-- safety_manager
INSERT INTO ROLE_PERMISSIONS VALUES
  ('role-safety', 'perm-04'), ('role-safety', 'perm-05'), ('role-safety', 'perm-09'),
  ('role-safety', 'perm-13'), ('role-safety', 'perm-19'), ('role-safety', 'perm-20');

-- fleet_admin
INSERT INTO ROLE_PERMISSIONS VALUES
  ('role-fleet', 'perm-08'), ('role-fleet', 'perm-09'), ('role-fleet', 'perm-10'),
  ('role-fleet', 'perm-11'), ('role-fleet', 'perm-12'), ('role-fleet', 'perm-15'),
  ('role-fleet', 'perm-16'), ('role-fleet', 'perm-17'), ('role-fleet', 'perm-18'),
  ('role-fleet', 'perm-19'), ('role-fleet', 'perm-20');

-- maintenance_tech
INSERT INTO ROLE_PERMISSIONS VALUES
  ('role-maint', 'perm-15'), ('role-maint', 'perm-16'), ('role-maint', 'perm-17'),
  ('role-maint', 'perm-19'), ('role-maint', 'perm-20');

-- org_admin — all permissions
INSERT INTO ROLE_PERMISSIONS
SELECT 'role-orgadmin', id FROM PERMISSIONS;

-- ── ASSET TYPES ──────────────────────────────────────────────
INSERT INTO ASSET_TYPES (id, code, label_en, label_es) VALUES
  ('at-01', 'forklift',           'Forklift',           'Montacargas'),
  ('at-02', 'pallet_jack',        'Pallet Jack',        'Transpaleta'),
  ('at-03', 'reach_truck',        'Reach Truck',        'Apilador de alcance'),
  ('at-04', 'order_picker',       'Order Picker',       'Recogepedidos'),
  ('at-05', 'box_truck',          'Box Truck',          'Camión de caja'),
  ('at-06', 'cargo_van',          'Cargo Van',          'Camioneta de carga'),
  ('at-07', 'refrigerated_truck', 'Refrigerated Truck', 'Camión refrigerado'),
  ('at-08', 'trailer',            'Trailer',            'Remolque');

-- ── TEST USERS (passwords are bcrypt placeholders — hash after seeding) ──
INSERT INTO USERS (id, email, password_hash, first_name, last_name,
    employee_id, preferred_lang, site_id) VALUES
  ('usr-01', 'ykesse@feedingwestchester.org',        '$2b$12$placeholder_hash_ykesse', 'Yaw',    'Kesse',    'EMP001', 'en', 'site-elmsford-01'),
  ('usr-02', 'supervisor1@feedingwestchester.org',   '$2b$12$placeholder_hash_super1', 'Maria',  'Lopez',    'EMP002', 'es', 'site-elmsford-01'),
  ('usr-03', 'operator1@feedingwestchester.org',     '$2b$12$placeholder_hash_op1',   'James',  'Rivera',   'EMP003', 'en', 'site-elmsford-01'),
  ('usr-04', 'operator2@feedingwestchester.org',     '$2b$12$placeholder_hash_op2',   'Ana',    'Gutierrez','EMP004', 'es', 'site-elmsford-01'),
  ('usr-05', 'operator3@feedingwestchester.org',     '$2b$12$placeholder_hash_op3',   'Kevin',  'Chen',     'EMP005', 'en', 'site-elmsford-01'),
  ('usr-06', 'operator4@feedingwestchester.org',     '$2b$12$placeholder_hash_op4',   'Rosa',   'Martinez', 'EMP006', 'es', 'site-elmsford-01'),
  ('usr-07', 'driver1@feedingwestchester.org',       '$2b$12$placeholder_hash_drv1',  'Marcus', 'Brown',    'EMP007', 'en', 'site-elmsford-01'),
  ('usr-08', 'driver2@feedingwestchester.org',       '$2b$12$placeholder_hash_drv2',  'Sofia',  'Reyes',    'EMP008', 'es', 'site-elmsford-01'),
  ('usr-09', 'safety@feedingwestchester.org',        '$2b$12$placeholder_hash_sfty',  'David',  'Kim',      'EMP009', 'en', 'site-elmsford-01'),
  ('usr-10', 'fleetadmin@feedingwestchester.org',    '$2b$12$placeholder_hash_fadm',  'Linda',  'Torres',   'EMP010', 'en', 'site-elmsford-01');

-- ── ROLE GRANTS ───────────────────────────────────────────────
INSERT INTO USER_ROLE_GRANTS (user_id, role_id, site_id, granted_by) VALUES
  ('usr-01', 'role-orgadmin', 'site-elmsford-01', 'usr-01'),
  ('usr-02', 'role-super',    'site-elmsford-01', 'usr-01'),
  ('usr-03', 'role-op-wh',    'site-elmsford-01', 'usr-01'),
  ('usr-04', 'role-op-wh',    'site-elmsford-01', 'usr-01'),
  ('usr-05', 'role-op-wh',    'site-elmsford-01', 'usr-01'),
  ('usr-06', 'role-op-wh',    'site-elmsford-01', 'usr-01'),
  ('usr-07', 'role-driver',   'site-elmsford-01', 'usr-01'),
  ('usr-08', 'role-driver',   'site-elmsford-01', 'usr-01'),
  ('usr-09', 'role-safety',   'site-elmsford-01', 'usr-01'),
  ('usr-10', 'role-fleet',    'site-elmsford-01', 'usr-01');
