"""
Fleet Inspect — Business Logic
Mirrors the Express middleware chain from the original Node.js API:
  critical fail → auto-defect → OOS lock → work order → notifications
"""

import uuid
from datetime import datetime, timezone
from db.connection import execute, query_one, query_many
import streamlit as st


# ── Audit helper ──────────────────────────────────────────────

def _audit(user_id: str, action: str, entity_type: str,
           entity_id: str, old_vals=None, new_vals=None):
    execute(
        """
        INSERT INTO AUDIT_LOG (id, user_id, action, entity_type, entity_id,
            old_values, new_values)
        VALUES (%s, %s, %s, %s, %s, PARSE_JSON(%s), PARSE_JSON(%s))
        """,
        (str(uuid.uuid4()), user_id, action, entity_type, entity_id,
         str(old_vals) if old_vals else None,
         str(new_vals) if new_vals else None)
    )


def _history(site_id: str, user_id: str, entity_type: str,
             entity_id: str, event_type: str, payload: dict = None):
    execute(
        """
        INSERT INTO HISTORY_EVENTS (id, site_id, user_id, entity_type,
            entity_id, event_type, payload)
        VALUES (%s, %s, %s, %s, %s, %s, PARSE_JSON(%s))
        """,
        (str(uuid.uuid4()), site_id, user_id, entity_type, entity_id,
         event_type, str(payload) if payload else None)
    )


def _notify(user_id: str, notif_type: str, title: str, body: str,
            entity_type: str = None, entity_id: str = None):
    execute(
        """
        INSERT INTO NOTIFICATIONS (id, user_id, type, title, body,
            entity_type, entity_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), user_id, notif_type, title, body,
         entity_type, entity_id)
    )


def _notify_supervisors(site_id: str, notif_type: str, title: str, body: str,
                         entity_type: str = None, entity_id: str = None):
    """Notify all supervisors and fleet admins at the site."""
    supers = query_many(
        """
        SELECT DISTINCT u.id
        FROM USERS u
        JOIN USER_ROLE_GRANTS rg ON rg.user_id = u.id
        JOIN ROLES r ON r.id = rg.role_id
        WHERE rg.site_id = %s AND rg.revoked_at IS NULL
          AND r.name IN ('supervisor', 'fleet_admin', 'safety_manager', 'org_admin')
          AND u.active = TRUE
        """,
        (site_id,)
    )
    for s in supers:
        _notify(s["ID"], notif_type, title, body, entity_type, entity_id)


# ── Sessions ──────────────────────────────────────────────────

def start_session(site_id: str, asset_id: str, operator_id: str,
                  started_by: str, client_event_id: str = None) -> dict:
    session_id = str(uuid.uuid4())
    client_event_id = client_event_id or str(uuid.uuid4())

    # Idempotency check
    existing = query_one(
        "SELECT id FROM SESSIONS WHERE client_event_id = %s",
        (client_event_id,)
    )
    if existing:
        return {"id": existing["ID"], "idempotent": True}

    execute(
        """
        INSERT INTO SESSIONS (id, site_id, asset_id, operator_id,
            started_by, status, client_event_id)
        VALUES (%s, %s, %s, %s, %s, 'active', %s)
        """,
        (session_id, site_id, asset_id, operator_id, started_by, client_event_id)
    )
    execute(
        "UPDATE ASSETS SET status = 'in_use', updated_at = CURRENT_TIMESTAMP() WHERE id = %s",
        (asset_id,)
    )
    _audit(started_by, "session.start", "SESSIONS", session_id)
    return {"id": session_id, "idempotent": False}


def handoff_session(session_id: str, handed_off_to: str, user_id: str):
    execute(
        """
        UPDATE SESSIONS SET status = 'handed_off', handed_off_to = %s,
            handed_off_at = CURRENT_TIMESTAMP(), updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s AND status = 'active'
        """,
        (handed_off_to, session_id)
    )
    _audit(user_id, "session.handoff", "SESSIONS", session_id)


# ── Inspection submission ─────────────────────────────────────

def submit_inspection(
    session_id: str | None,
    asset_id: str,
    operator_id: str,
    submitted_by: str,
    template_id: str,
    inspection_type: str,
    responses: list[dict],   # [{item_id, result, numeric_value, text_value, notes}]
    site_id: str,
    client_event_id: str = None,
) -> dict:
    """
    Core inspection submission with full business logic:
    critical fail → auto-defect → OOS → work order → notifications
    """
    client_event_id = client_event_id or str(uuid.uuid4())

    # Idempotency
    existing = query_one(
        "SELECT id, overall_result FROM INSPECTIONS WHERE client_event_id = %s",
        (client_event_id,)
    )
    if existing:
        return {"id": existing["ID"], "result": existing["OVERALL_RESULT"],
                "idempotent": True}

    inspection_id = str(uuid.uuid4())

    # Classify responses
    critical_fails = []
    has_any_fail = False
    for r in responses:
        if r.get("result") == "fail":
            has_any_fail = True
            item = query_one(
                "SELECT critical FROM CHECKLIST_ITEMS WHERE id = %s",
                (r["item_id"],)
            )
            if item and item["CRITICAL"]:
                critical_fails.append(r)

    overall = "fail" if has_any_fail else "pass"
    if critical_fails:
        overall = "fail"  # always fail with critical

    # Insert inspection
    execute(
        """
        INSERT INTO INSPECTIONS (id, session_id, asset_id, operator_id,
            submitted_by, template_id, inspection_type, status,
            overall_result, critical_fail_count, submitted_at, client_event_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'submitted', %s, %s,
                CURRENT_TIMESTAMP(), %s)
        """,
        (inspection_id, session_id, asset_id, operator_id, submitted_by,
         template_id, inspection_type, overall, len(critical_fails),
         client_event_id)
    )

    # Insert responses
    for r in responses:
        execute(
            """
            INSERT INTO INSPECTION_RESPONSES (id, inspection_id, item_id,
                result, numeric_value, text_value, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (str(uuid.uuid4()), inspection_id, r["item_id"],
             r.get("result"), r.get("numeric_value"),
             r.get("text_value"), r.get("notes"))
        )

    # Update asset last_inspected
    execute(
        "UPDATE ASSETS SET last_inspected = CURRENT_TIMESTAMP(), updated_at = CURRENT_TIMESTAMP() WHERE id = %s",
        (asset_id,)
    )

    defect_ids = []
    work_order_id = None

    # ── Critical fail cascade ─────────────────────────────────
    if critical_fails:
        # 1. Place asset Out of Service
        execute(
            """
            UPDATE ASSETS SET status = 'oos',
                oos_reason = 'Critical inspection failure',
                oos_since = CURRENT_TIMESTAMP(),
                updated_at = CURRENT_TIMESTAMP()
            WHERE id = %s
            """,
            (asset_id,)
        )

        # 2. Auto-create defects for each critical fail
        for cf in critical_fails:
            item = query_one(
                "SELECT label_en FROM CHECKLIST_ITEMS WHERE id = %s",
                (cf["item_id"],)
            )
            defect_id = str(uuid.uuid4())
            execute(
                """
                INSERT INTO DEFECTS (id, asset_id, inspection_id,
                    inspection_item_id, reported_by, severity, description,
                    status, auto_generated, oos_triggered)
                VALUES (%s, %s, %s, %s, %s, 'critical', %s, 'open', TRUE, TRUE)
                """,
                (defect_id, asset_id, inspection_id, cf["item_id"],
                 submitted_by,
                 f"[AUTO] Critical fail: {item['LABEL_EN'] if item else cf['item_id']}")
            )
            defect_ids.append(defect_id)

        # 3. Auto-create work order
        if defect_ids:
            wo_id = str(uuid.uuid4())
            execute(
                """
                INSERT INTO WORK_ORDERS (id, asset_id, defect_id, created_by,
                    priority, status, description)
                VALUES (%s, %s, %s, %s, 'critical', 'open',
                        'Auto-generated from critical inspection failure')
                """,
                (wo_id, asset_id, defect_ids[0], submitted_by)
            )
            work_order_id = wo_id

        # 4. Notify supervisors
        asset = query_one("SELECT name, tag FROM ASSETS WHERE id = %s", (asset_id,))
        asset_name = asset["NAME"] if asset else asset_id
        _notify_supervisors(
            site_id, "oos_triggered",
            f"⛔ Asset Out of Service: {asset_name}",
            f"Critical inspection failure placed {asset_name} out of service.",
            "ASSETS", asset_id
        )
        if work_order_id:
            _notify_supervisors(
                site_id, "work_order_assigned",
                f"🔧 Work Order Created: {asset_name}",
                "A critical-priority work order was auto-generated.",
                "WORK_ORDERS", work_order_id
            )

    _audit(submitted_by, "inspection.submit", "INSPECTIONS", inspection_id,
           new_vals={"result": overall, "critical_fails": len(critical_fails)})
    _history(site_id, submitted_by, "INSPECTIONS", inspection_id,
             "inspection.submitted", {"result": overall})

    return {
        "id": inspection_id,
        "result": overall,
        "critical_fail_count": len(critical_fails),
        "defect_ids": defect_ids,
        "work_order_id": work_order_id,
        "oos_triggered": bool(critical_fails),
        "idempotent": False,
    }


# ── Returns ───────────────────────────────────────────────────

def submit_return(session_id: str, asset_id: str, operator_id: str,
                  submitted_by: str, fuel_level: str = None,
                  damage_noted: bool = False, damage_notes: str = None,
                  client_event_id: str = None) -> dict:
    client_event_id = client_event_id or str(uuid.uuid4())
    existing = query_one(
        "SELECT id FROM RETURNS WHERE client_event_id = %s", (client_event_id,)
    )
    if existing:
        return {"id": existing["ID"], "idempotent": True}

    return_id = str(uuid.uuid4())
    execute(
        """
        INSERT INTO RETURNS (id, session_id, asset_id, operator_id,
            submitted_by, fuel_level, damage_noted, damage_notes, client_event_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (return_id, session_id, asset_id, operator_id, submitted_by,
         fuel_level, damage_noted, damage_notes, client_event_id)
    )
    execute(
        """
        UPDATE SESSIONS SET status = 'returned', returned_at = CURRENT_TIMESTAMP(),
            updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s
        """,
        (session_id,)
    )
    # Only return asset to available if not OOS
    execute(
        """
        UPDATE ASSETS SET status = 'available', updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s AND status = 'in_use'
        """,
        (asset_id,)
    )
    _audit(submitted_by, "return.submit", "RETURNS", return_id)
    return {"id": return_id, "idempotent": False}


# ── Work order verification ───────────────────────────────────

def verify_work_order(work_order_id: str, verified_by: str,
                      site_id: str, notes: str = None) -> dict:
    wo = query_one("SELECT * FROM WORK_ORDERS WHERE id = %s", (work_order_id,))
    if not wo:
        return {"error": "Work order not found"}

    execute(
        """
        UPDATE WORK_ORDERS SET status = 'verified', verified_by = %s,
            verified_at = CURRENT_TIMESTAMP(), notes = %s,
            updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s
        """,
        (verified_by, notes, work_order_id)
    )
    # Return asset to service
    execute(
        """
        UPDATE ASSETS SET status = 'available', oos_reason = NULL,
            oos_since = NULL, updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s AND status IN ('oos', 'maintenance')
        """,
        (wo["ASSET_ID"],)
    )
    _audit(verified_by, "workorder.verify", "WORK_ORDERS", work_order_id)
    _notify_supervisors(
        site_id, "work_order_assigned",
        "✅ Work Order Verified",
        f"Work order {work_order_id[:8]} has been verified and asset returned to service.",
        "WORK_ORDERS", work_order_id
    )
    return {"id": work_order_id, "status": "verified"}


# ── Temperature holds ─────────────────────────────────────────

def review_temp_hold(hold_id: str, action: str, reviewed_by: str,
                     site_id: str, notes: str = None) -> dict:
    """action: 'approve' | 'reject'"""
    status = "approved" if action == "approve" else "rejected"
    execute(
        """
        UPDATE TEMPERATURE_HOLDS SET status = %s, reviewed_by = %s,
            reviewed_at = CURRENT_TIMESTAMP(), review_notes = %s,
            updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s AND status = 'pending'
        """,
        (status, reviewed_by, notes, hold_id)
    )
    _audit(reviewed_by, f"temp_hold.{action}", "TEMPERATURE_HOLDS", hold_id)
    return {"id": hold_id, "status": status}


# ── Safety observation actions ────────────────────────────────

def add_safety_action(observation_id: str, taken_by: str,
                      action_type: str, description: str) -> dict:
    action_id = str(uuid.uuid4())
    execute(
        """
        INSERT INTO SAFETY_OBSERVATION_ACTIONS (id, observation_id, taken_by,
            action_type, description)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (action_id, observation_id, taken_by, action_type, description)
    )
    execute(
        """
        UPDATE SAFETY_OBSERVATIONS SET status = 'action_taken',
            updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s AND status != 'closed'
        """,
        (observation_id,)
    )
    _audit(taken_by, "safety.action", "SAFETY_OBSERVATIONS", observation_id)
    return {"id": action_id}


# ── Inspection amendment ──────────────────────────────────────

def amend_inspection(inspection_id: str, amended_by: str,
                     reason: str, changes: dict) -> dict:
    amendment_id = str(uuid.uuid4())
    import json
    execute(
        """
        INSERT INTO INSPECTION_AMENDMENTS (id, inspection_id, amended_by,
            reason, changes)
        VALUES (%s, %s, %s, %s, PARSE_JSON(%s))
        """,
        (amendment_id, inspection_id, amended_by, reason, json.dumps(changes))
    )
    execute(
        """
        UPDATE INSPECTIONS SET status = 'amended',
            updated_at = CURRENT_TIMESTAMP()
        WHERE id = %s
        """,
        (inspection_id,)
    )
    _audit(amended_by, "inspection.amend", "INSPECTIONS", inspection_id,
           new_vals={"reason": reason})
    return {"id": amendment_id}
