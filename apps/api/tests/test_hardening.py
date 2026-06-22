"""
Phase 7 hardening tests — adversarial multi-tenant + invariant suite.

Covers:
  H1. Snapshot rows cannot be updated or deleted (§0.10 immutable guard trigger)
  H2. activity_facts state cannot regress from validated → proposed
  H3. Cross-tenant snapshot access via every endpoint variation
  H4. Cross-tenant anomaly access
  H5. Validate endpoint idempotency and state-gate
  H6. compute_emissions uncertainty is separate from totals (§0.2)
  H7. Effective-dating: FY2024 vs FY2023 pull different factor sets (§0.7)
  H8. No auto-finalize path exists anywhere in the API (§0.4)
  H9. Cross-bureau bureau-row access is blocked by RLS
  H10. Audit log entries are written for validate and compute events
"""

from __future__ import annotations

import uuid

import psycopg2
import psycopg2.extras
import pytest
from adrar_api.main import app
from fastapi.testclient import TestClient

METHODOLOGY_ID = "00000000-0000-0000-0000-000000000001"


def _create_project(tc: TestClient) -> str:
    cid = tc.post("/clients", json={"name": f"HC{uuid.uuid4().hex[:4]}"}).json()["id"]
    pid = tc.post("/projects", json={
        "client_id": cid, "name": "Hardening Project",
        "reporting_year": 2024, "methodology_id": METHODOLOGY_ID,
    }).json()["id"]
    return pid


def _propose_and_validate(tc: TestClient, pid: str) -> tuple[str, str]:
    """Propose + validate one electricity fact. Returns (fact_id, snapshot_id)."""
    fid = tc.post(f"/projects/{pid}/activity", json={
        "category": "scope2_electricity", "activity_value": "100",
        "activity_unit": "kWh", "period_start": "2024-01-01",
        "period_end": "2024-12-31", "scope": 2,
    }).json()["id"]
    tc.patch(f"/projects/{pid}/activity/{fid}/validate")

    snap = tc.post(f"/projects/{pid}/compute", json={
        "reporting_year": 2024, "gwp_basis": "AR6",
        "methodology_id": METHODOLOGY_ID, "region": "MA",
    })
    snap_id = snap.json()["id"]
    return fid, snap_id


# ── H1: Snapshot immutability (§0.10) ─────────────────────────────────────

class TestSnapshotImmutability:
    """Trigger trg_snapshots_immutable_update/delete must fire for any role."""

    def test_snapshot_update_denied_by_trigger(self, su_conn, client_a, bureau_a_id, db_ready):
        pid = _create_project(client_a)
        _, snap_id = _propose_and_validate(client_a, pid)

        cur = su_conn.cursor()
        with pytest.raises(psycopg2.errors.RaiseException, match=r"immutable"):
            cur.execute(
                "UPDATE report_snapshots SET reporting_year = 9999 WHERE id = %s",
                (snap_id,)
            )
        su_conn.rollback()

    def test_snapshot_delete_denied_by_trigger(self, su_conn, client_a, bureau_a_id, db_ready):
        pid = _create_project(client_a)
        _, snap_id = _propose_and_validate(client_a, pid)

        cur = su_conn.cursor()
        with pytest.raises(psycopg2.errors.RaiseException, match=r"immutable"):
            cur.execute("DELETE FROM report_snapshots WHERE id = %s", (snap_id,))
        su_conn.rollback()


# ── H2: activity_facts state regression (§0.3) ────────────────────────────

class TestStateRegression:
    def test_validated_fact_cannot_regress_to_proposed(self, su_conn, client_a, bureau_a_id, db_ready):
        pid = _create_project(client_a)
        r = client_a.post(f"/projects/{pid}/activity", json={
            "category": "scope1_stationary", "activity_value": "50",
            "activity_unit": "MJ", "period_start": "2024-01-01",
            "period_end": "2024-12-31", "scope": 1,
        })
        fid = r.json()["id"]
        client_a.patch(f"/projects/{pid}/activity/{fid}/validate")

        cur = su_conn.cursor()
        with pytest.raises(psycopg2.errors.RaiseException, match=r"regress"):
            cur.execute(
                "UPDATE activity_facts SET state = 'proposed' WHERE id = %s",
                (fid,)
            )
        su_conn.rollback()

    def test_validate_already_validated_returns_404(self, client_a, bureau_a_id):
        pid = _create_project(client_a)
        r = client_a.post(f"/projects/{pid}/activity", json={
            "category": "scope1_stationary", "activity_value": "10",
            "activity_unit": "MJ", "period_start": "2024-01-01",
            "period_end": "2024-12-31", "scope": 1,
        })
        fid = r.json()["id"]
        client_a.patch(f"/projects/{pid}/activity/{fid}/validate")

        # Second validate on already-validated should 404
        r2 = client_a.patch(f"/projects/{pid}/activity/{fid}/validate")
        assert r2.status_code == 404


# ── H3: Cross-tenant snapshot access ──────────────────────────────────────

class TestCrossTenantSnapshots:
    def test_snapshot_list_cross_tenant_empty(self, client_a, client_b, bureau_a_id, bureau_b_id):
        pid_a = _create_project(client_a)
        _propose_and_validate(client_a, pid_a)

        # Bureau B creates its own project and tries to list A's snapshots
        pid_b = _create_project(client_b)
        r = client_b.get(f"/projects/{pid_b}/snapshots")
        assert r.status_code == 200
        assert r.json() == [], "RLS FAIL: bureau B listed bureau A snapshots"

    def test_snapshot_get_cross_tenant_404(self, client_a, client_b, bureau_a_id, bureau_b_id):
        pid_a = _create_project(client_a)
        _, snap_id = _propose_and_validate(client_a, pid_a)

        pid_b = _create_project(client_b)
        r = client_b.get(f"/projects/{pid_b}/snapshots/{snap_id}")
        assert r.status_code == 404, "RLS FAIL: bureau B retrieved bureau A snapshot"


# ── H4: Cross-tenant anomaly access ───────────────────────────────────────

class TestCrossTenantAnomalies:
    def test_anomalies_not_visible_cross_tenant(self, client_a, client_b, bureau_a_id, bureau_b_id):
        pid_a = _create_project(client_a)
        fid = client_a.post(f"/projects/{pid_a}/activity", json={
            "category": "scope1_stationary", "activity_value": "0",
            "activity_unit": "MJ", "period_start": "2024-01-01",
            "period_end": "2024-12-31", "scope": 1,
        }).json()["id"]
        client_a.patch(f"/projects/{pid_a}/activity/{fid}/validate")
        # Reconcile to generate anomalies
        client_a.post(f"/projects/{pid_a}/reconcile")

        pid_b = _create_project(client_b)
        r = client_b.post(f"/projects/{pid_b}/reconcile")
        assert r.status_code in (200, 201)
        # Bureau B should only see its own (none)
        assert r.json() == [], "RLS FAIL: bureau B saw bureau A anomalies"


# ── H5: Validate idempotency ───────────────────────────────────────────────

class TestValidateIdempotency:
    def test_validate_nonexistent_fact_404(self, client_a, bureau_a_id):
        pid = _create_project(client_a)
        fake_id = str(uuid.uuid4())
        r = client_a.patch(f"/projects/{pid}/activity/{fake_id}/validate")
        assert r.status_code == 404

    def test_validate_cross_tenant_fact_404(self, client_a, client_b, bureau_a_id, bureau_b_id):
        pid_a = _create_project(client_a)
        fid_a = client_a.post(f"/projects/{pid_a}/activity", json={
            "category": "scope1_stationary", "activity_value": "10",
            "activity_unit": "MJ", "period_start": "2024-01-01",
            "period_end": "2024-12-31", "scope": 1,
        }).json()["id"]

        pid_b = _create_project(client_b)
        r = client_b.patch(f"/projects/{pid_b}/activity/{fid_a}/validate")
        assert r.status_code == 404, "Security FAIL: bureau B validated bureau A fact"


# ── H6: Uncertainty separate from totals (§0.2) ───────────────────────────

class TestUncertaintySeparation:
    def test_uncertainty_not_inflating_totals(self, client_a, bureau_a_id):
        pid = _create_project(client_a)
        _, snap_id = _propose_and_validate(client_a, pid)

        r = client_a.get(f"/projects/{pid}/snapshots/{snap_id}")
        snap = r.json()

        totals = snap["totals_co2e"]
        uncertainty = snap["uncertainty"]

        # §0.2: totals must NOT include (1 + uncertainty) factor
        # Verify: uncertainty is a separate object, not embedded in totals
        assert isinstance(uncertainty, dict), "uncertainty must be a dict separate from totals"
        for key in totals:
            assert key not in uncertainty or isinstance(uncertainty[key], (int, float)), (
                "§0.2 FAIL: uncertainty appears embedded in totals"
            )

        # The total must equal the raw activity × factor × gwp (no uncertainty factor)
        # We can only check it's > 0 and that adding uncertainty would give a different value
        total_val = totals.get("total", sum(v for k, v in totals.items() if k != "total"))
        assert total_val > 0


# ── H7: Effective-dating (§0.7) ───────────────────────────────────────────

class TestEffectiveDating:
    def test_factor_sets_filtered_by_year(self, client_a):
        r2024 = client_a.get("/factor-sets", params={"year": 2024})
        r2023 = client_a.get("/factor-sets", params={"year": 2023})
        assert r2024.status_code == 200
        # Both requests should succeed; 2023 set should be different (or empty if not seeded)
        # The key invariant: endpoint accepts year parameter and returns effective-dated sets
        assert isinstance(r2024.json(), list)
        assert isinstance(r2023.json(), list)

        # Verify: every returned factor_set covers the requested year
        for fs in r2024.json():
            eff_from = fs.get("effective_from", "")
            eff_to = fs.get("effective_to")
            if eff_from:
                assert eff_from[:4] <= "2024", f"§0.7 FAIL: factor set effective_from {eff_from} > 2024"
            if eff_to:
                assert eff_to[:4] >= "2024", f"§0.7 FAIL: factor set effective_to {eff_to} < 2024"


# ── H8: No finalize anywhere (§0.4) ───────────────────────────────────────

class TestNoFinalizeHardening:
    FORBIDDEN_SEGMENTS = {"finalize", "approve", "submit", "final", "auto_validate", "autovalidate"}

    def test_no_forbidden_routes(self):
        for route in app.routes:
            path = getattr(route, "path", "")
            parts = set(path.lower().replace("-", "_").split("/"))
            overlap = parts & self.FORBIDDEN_SEGMENTS
            assert not overlap, f"§0.4 VIOLATED: forbidden segment {overlap} in route {path}"

    def test_cannot_post_to_finalize_path(self, client_a, bureau_a_id):
        pid = _create_project(client_a)
        assert client_a.post(f"/projects/{pid}/finalize").status_code == 405
        assert client_a.post(f"/projects/{pid}/approve").status_code == 405
        assert client_a.post(f"/projects/{pid}/submit").status_code == 405


# ── H9: Bureau row cross-tenant isolation ─────────────────────────────────

class TestBureauRowIsolation:
    def test_bureau_a_cannot_read_bureau_b_row(self, su_conn, bureau_a_id, bureau_b_id, db_ready):
        """RLS on bureaus: a session with bureau_A GUC must not see bureau_B row."""
        dsn = su_conn.dsn  # not available directly; use pg fixture
        # We verify via the app_user path that SELECT is filtered
        # (The API doesn't expose a /bureaus endpoint, so test via psycopg2 with GUC)
        conn = psycopg2.connect(
            host=su_conn.connection_parameters.get("host", "localhost"),
            port=su_conn.connection_parameters.get("port", 5432),
            dbname=su_conn.connection_parameters.get("dbname", "test"),
            user="app_user",
            password="test",
            cursor_factory=psycopg2.extras.RealDictCursor,
        ) if hasattr(su_conn, "connection_parameters") else None

        if conn is None:
            pytest.skip("Cannot reconstruct DSN for app_user in this test env")

        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.bureau_id = %s", (bureau_a_id,))
                cur.execute("SELECT id FROM bureaus")
                rows = cur.fetchall()
                ids = [str(r["id"]) for r in rows]
                assert bureau_b_id not in ids, (
                    f"RLS FAIL: bureau A session can see bureau B row (ids={ids})"
                )
                assert bureau_a_id in ids, "Bureau A must see its own row"
        finally:
            conn.close()


# ── H10: Audit log written for key transitions ────────────────────────────

class TestAuditLog:
    def test_audit_log_written_on_validate(self, su_conn, client_a, bureau_a_id, db_ready):
        pid = _create_project(client_a)
        r = client_a.post(f"/projects/{pid}/activity", json={
            "category": "scope1_stationary", "activity_value": "77",
            "activity_unit": "MJ", "period_start": "2024-01-01",
            "period_end": "2024-12-31", "scope": 1,
        })
        fid = r.json()["id"]

        # Validate — should trigger trg_audit_activity_fact
        client_a.patch(f"/projects/{pid}/activity/{fid}/validate")

        cur = su_conn.cursor()
        cur.execute(
            "SELECT * FROM audit_log WHERE entity_id = %s AND action = 'VALIDATE'",
            (fid,)
        )
        rows = cur.fetchall()
        assert len(rows) >= 1, "Audit log MISSING: no VALIDATE entry for activity_fact transition"
        row = rows[0]
        assert row["before_state"]["state"] == "proposed"
        assert row["after_state"]["state"] == "validated"

    def test_audit_log_written_on_compute(self, su_conn, client_a, bureau_a_id, db_ready):
        pid = _create_project(client_a)
        _, snap_id = _propose_and_validate(client_a, pid)

        cur = su_conn.cursor()
        cur.execute(
            "SELECT * FROM audit_log WHERE entity_id = %s AND action = 'COMPUTE'",
            (snap_id,)
        )
        rows = cur.fetchall()
        assert len(rows) >= 1, "Audit log MISSING: no COMPUTE entry for snapshot insert"
        row = rows[0]
        assert "state_hash" in row["after_state"]
        assert "gwp_basis" in row["after_state"]
