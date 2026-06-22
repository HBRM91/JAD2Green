"""
Phase 3 acceptance tests.

Critical invariants under test:
  1. All endpoints require auth (401 without token)
  2. Tenant isolation: bureau A cannot read/write bureau B data
  3. propose_activity cannot set state=validated
  4. compute_emissions blocks if un-validated facts exist
  5. No finalize/approve/submit route exists
  6. compute_emissions produces dual Scope 2 in the snapshot
"""

from __future__ import annotations

import uuid

import pytest
from adrar_api.main import app
from fastapi.testclient import TestClient

METHODOLOGY_ID = "00000000-0000-0000-0000-000000000001"


# ── helpers ────────────────────────────────────────────────────────────────

def _create_client_and_project(client: TestClient, bureau_id: str) -> tuple[str, str]:
    r = client.post("/clients", json={"name": f"Client {uuid.uuid4().hex[:6]}"})
    assert r.status_code == 201, r.text
    client_id = r.json()["id"]

    r = client.post("/projects", json={
        "client_id": client_id,
        "name": "Test Project",
        "reporting_year": 2024,
        "methodology_id": METHODOLOGY_ID,
    })
    assert r.status_code == 201, r.text
    return client_id, r.json()["id"]


def _propose_electricity_fact(client: TestClient, project_id: str) -> str:
    r = client.post(f"/projects/{project_id}/activity", json={
        "category": "scope2_electricity",
        "activity_value": "500",
        "activity_unit": "kWh",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "scope": 2,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── 1. Auth required on all endpoints ────────────────────────────────────

class TestAuthRequired:
    def test_no_token_returns_401(self):
        c = TestClient(app)  # no auth header
        assert c.get("/projects").status_code == 401

    def test_bad_token_returns_401(self):
        c = TestClient(app, headers={"Authorization": "Bearer garbage"})
        assert c.get("/projects").status_code == 401

    def test_health_no_auth(self):
        c = TestClient(app)
        assert c.get("/health").status_code == 200


# ── 2. Tenant isolation ───────────────────────────────────────────────────

class TestTenantIsolation:
    def test_bureau_a_cannot_see_bureau_b_clients(
        self, client_a, client_b, bureau_a_id, bureau_b_id
    ):
        # Create a client under bureau B
        r = client_b.post("/clients", json={"name": "Bureau B Client"})
        assert r.status_code == 201
        b_client_id = r.json()["id"]

        # Bureau A's list must not contain bureau B's client
        r = client_a.get("/clients")
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()]
        assert b_client_id not in ids, "RLS FAIL: bureau A can see bureau B client"

    def test_bureau_a_cannot_get_bureau_b_project(
        self, client_a, client_b, bureau_a_id, bureau_b_id
    ):
        _, proj_b_id = _create_client_and_project(client_b, bureau_b_id)
        r = client_a.get(f"/projects/{proj_b_id}")
        assert r.status_code == 404, "RLS FAIL: bureau A can access bureau B project"

    def test_bureau_a_cannot_get_bureau_b_activity(
        self, client_a, client_b, bureau_a_id, bureau_b_id
    ):
        _, proj_b_id = _create_client_and_project(client_b, bureau_b_id)
        _propose_electricity_fact(client_b, proj_b_id)

        r = client_a.get(f"/projects/{proj_b_id}/activity")
        # Either 404 (project not found) or empty list — never bureau B's data
        if r.status_code == 200:
            assert r.json() == [], "RLS FAIL: bureau A received bureau B activity facts"

    def test_bureau_a_cannot_propose_into_bureau_b_project(
        self, client_a, client_b, bureau_a_id, bureau_b_id
    ):
        _, proj_b_id = _create_client_and_project(client_b, bureau_b_id)
        r = client_a.post(f"/projects/{proj_b_id}/activity", json={
            "category": "scope1_stationary",
            "activity_value": "100",
            "activity_unit": "MJ",
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "scope": 1,
        })
        # Must fail — project belongs to bureau B
        assert r.status_code in (404, 403, 422), (
            f"RLS FAIL: bureau A managed to propose into bureau B project: {r.status_code}"
        )


# ── 3. propose_activity cannot set validated ──────────────────────────────

class TestProposeInvariant:
    def test_propose_with_state_proposed_succeeds(self, client_a, bureau_a_id):
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        r = client_a.post(f"/projects/{proj_id}/activity", json={
            "category": "scope1_stationary",
            "activity_value": "100",
            "activity_unit": "MJ",
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "scope": 1,
            "state": "proposed",
        })
        assert r.status_code == 201
        assert r.json()["state"] == "proposed"

    def test_propose_with_state_validated_rejected(self, client_a, bureau_a_id):
        """§0.3: API must reject attempts to write state=validated."""
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        r = client_a.post(f"/projects/{proj_id}/activity", json={
            "category": "scope1_stationary",
            "activity_value": "100",
            "activity_unit": "MJ",
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "scope": 1,
            "state": "validated",
        })
        assert r.status_code == 422, (
            f"§0.3 VIOLATED: propose_activity accepted state=validated (got {r.status_code})"
        )

    def test_propose_default_state_is_proposed(self, client_a, bureau_a_id):
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        fact_id = _propose_electricity_fact(client_a, proj_id)
        r = client_a.get(f"/projects/{proj_id}/activity")
        facts = {f["id"]: f for f in r.json()}
        assert facts[fact_id]["state"] == "proposed"


# ── 4. compute blocks on un-validated facts ───────────────────────────────

class TestComputeInvariant:
    def test_compute_blocks_with_proposed_facts(self, client_a, bureau_a_id):
        """§0.10: compute must refuse when proposed facts exist."""
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        _propose_electricity_fact(client_a, proj_id)  # remains proposed

        r = client_a.post(f"/projects/{proj_id}/compute", json={
            "reporting_year": 2024,
            "gwp_basis": "AR5",
            "methodology_id": METHODOLOGY_ID,
            "region": "MA",
        })
        assert r.status_code == 422, (
            f"§0.10 VIOLATED: compute accepted un-validated facts (got {r.status_code})"
        )
        assert "proposed" in r.json()["detail"].lower(), (
            f"Expected 'proposed' in error message: {r.json()['detail']}"
        )

    def test_compute_blocks_with_no_facts(self, client_a, bureau_a_id):
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        r = client_a.post(f"/projects/{proj_id}/compute", json={
            "reporting_year": 2024,
            "gwp_basis": "AR5",
            "methodology_id": METHODOLOGY_ID,
            "region": "MA",
        })
        assert r.status_code == 422

    def test_compute_succeeds_with_all_validated(self, client_a, bureau_a_id):
        """Full happy path: propose → validate → compute → snapshot with dual S2."""
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        fact_id = _propose_electricity_fact(client_a, proj_id)

        # Validate via the human-gate endpoint
        r = client_a.patch(f"/projects/{proj_id}/activity/{fact_id}/validate")
        assert r.status_code == 200
        assert r.json()["state"] == "validated"

        # Now compute should succeed
        r = client_a.post(f"/projects/{proj_id}/compute", json={
            "reporting_year": 2024,
            "gwp_basis": "AR5",
            "methodology_id": METHODOLOGY_ID,
            "region": "MA",
        })
        assert r.status_code == 201, r.text
        snap = r.json()

        # Snapshot has dual Scope 2 (§0 inv 8)
        totals = snap["totals_co2e"]
        assert "scope2_location" in totals
        assert "scope2_market" in totals
        assert float(snap["scope2_location_t"]) > 0
        assert float(snap["scope2_market_t"]) > 0

        # state_hash is a 64-char hex string
        assert len(snap["state_hash"]) == 64

    def test_compute_deterministic(self, client_a, bureau_a_id):
        """Same inputs → same state_hash on two separate compute calls."""
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        fact_id = _propose_electricity_fact(client_a, proj_id)
        client_a.patch(f"/projects/{proj_id}/activity/{fact_id}/validate")

        payload = {
            "reporting_year": 2024,
            "gwp_basis": "AR5",
            "methodology_id": METHODOLOGY_ID,
            "region": "MA",
        }
        r1 = client_a.post(f"/projects/{proj_id}/compute", json=payload)
        r2 = client_a.post(f"/projects/{proj_id}/compute", json=payload)
        assert r1.status_code == 201 and r2.status_code == 201
        assert r1.json()["state_hash"] == r2.json()["state_hash"]


# ── 5. No finalize/approve endpoint ──────────────────────────────────────

def _all_route_paths(app_) -> list[str]:
    """Recursively collect all route paths including from included routers."""
    paths = []
    for r in app_.routes:
        if hasattr(r, "path"):
            paths.append(r.path)
        if hasattr(r, "routes"):
            for sub in r.routes:
                if hasattr(sub, "path"):
                    paths.append(sub.path)
    return paths


class TestNoFinalizeEndpoint:
    def test_no_finalize_route(self):
        """§0.4: No finalize/approve/submit endpoint may exist."""
        routes = _all_route_paths(app)
        forbidden = {"finalize", "approve", "submit", "final"}
        for route in routes:
            parts = set(route.lower().split("/"))
            overlap = parts & forbidden
            assert not overlap, (
                f"§0.4 VIOLATED: found forbidden route segment {overlap} in {route}"
            )

    def test_validate_endpoint_is_human_gate_not_auto(self, client_a, bureau_a_id):
        """The /validate endpoint requires explicit human action; it is not auto-triggered."""
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        fact_id = _propose_electricity_fact(client_a, proj_id)

        # Manual call to validate (simulating consultant UI)
        r = client_a.patch(f"/projects/{proj_id}/activity/{fact_id}/validate")
        assert r.status_code == 200
        # Fact is now validated
        r = client_a.get(f"/projects/{proj_id}/activity")
        fact = next(f for f in r.json() if f["id"] == fact_id)
        assert fact["state"] == "validated"


# ── 6. Factor-set and conversion endpoints ───────────────────────────────

class TestReadEndpoints:
    def test_search_factor_sets(self, client_a):
        r = client_a.get("/factor-sets", params={"year": 2024})
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_search_factor_sets_methodology_filter(self, client_a):
        r = client_a.get("/factor-sets", params={
            "methodology_id": METHODOLOGY_ID,
            "year": 2024,
        })
        assert r.status_code == 200
        for fs in r.json():
            assert fs["methodology_id"] == METHODOLOGY_ID

    def test_get_conversion_direct(self, client_a):
        r = client_a.get("/conversions", params={
            "from_unit": "kWh",
            "to_unit": "MJ",
            "year": 2024,
        })
        assert r.status_code == 200
        assert float(r.json()["combined_coefficient"]) == pytest.approx(3.6, rel=1e-3)

    def test_get_conversion_fuel_specific(self, client_a):
        r = client_a.get("/conversions", params={
            "from_unit": "L",
            "to_unit": "MJ",
            "fuel_type": "diesel",
            "year": 2024,
        })
        assert r.status_code == 200
        assert float(r.json()["combined_coefficient"]) == pytest.approx(34.93, rel=1e-3)

    def test_get_conversion_not_found(self, client_a):
        r = client_a.get("/conversions", params={
            "from_unit": "L",
            "to_unit": "parsecs",
            "year": 2024,
        })
        assert r.status_code == 404

    def test_get_snapshot(self, client_a, bureau_a_id):
        _, proj_id = _create_client_and_project(client_a, bureau_a_id)
        fact_id = _propose_electricity_fact(client_a, proj_id)
        client_a.patch(f"/projects/{proj_id}/activity/{fact_id}/validate")
        r = client_a.post(f"/projects/{proj_id}/compute", json={
            "reporting_year": 2024, "gwp_basis": "AR5",
            "methodology_id": METHODOLOGY_ID, "region": "MA",
        })
        snap_id = r.json()["id"]

        r2 = client_a.get(f"/projects/{proj_id}/snapshots/{snap_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == snap_id

    def test_snapshot_not_visible_cross_tenant(self, client_a, client_b, bureau_a_id, bureau_b_id):
        # Create snapshot under bureau A
        _, proj_a_id = _create_client_and_project(client_a, bureau_a_id)
        fact_id = _propose_electricity_fact(client_a, proj_a_id)
        client_a.patch(f"/projects/{proj_a_id}/activity/{fact_id}/validate")
        r = client_a.post(f"/projects/{proj_a_id}/compute", json={
            "reporting_year": 2024, "gwp_basis": "AR5",
            "methodology_id": METHODOLOGY_ID, "region": "MA",
        })
        snap_id = r.json()["id"]

        # Bureau B tries to access it
        _, proj_b_id = _create_client_and_project(client_b, bureau_b_id)
        r2 = client_b.get(f"/projects/{proj_b_id}/snapshots/{snap_id}")
        assert r2.status_code == 404, "RLS FAIL: bureau B accessed bureau A snapshot"
