"""Minimal CRUD for clients and projects."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..deps import DBDep, TenantDep
from ..models.requests import ClientCreate, ProjectCreate
from ..models.responses import ClientResponse, ProjectResponse

router = APIRouter()


_CLIENT_COLS = "id, bureau_id, name, sector, naics_code, secteur_maroc, is_listed_bvc, rse_reporting_required, created_at"
_PROJECT_COLS = "id, bureau_id, client_id, name, reporting_year, methodology_id, status, reporting_frameworks, sector_code, language, ndc_target_year, ndc_baseline_year, created_at"


@router.post("/clients", response_model=ClientResponse, status_code=201)
def create_client(body: ClientCreate, tenant: TenantDep, db: DBDep) -> ClientResponse:
    with db.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO clients (bureau_id, name, sector, naics_code, secteur_maroc, is_listed_bvc, rse_reporting_required)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING {_CLIENT_COLS}
            """,
            (tenant.bureau_id, body.name, body.sector, body.naics_code, body.secteur_maroc, body.is_listed_bvc, body.rse_reporting_required),
        )
        row = cur.fetchone()
    return ClientResponse(**row)


@router.get("/clients", response_model=list[ClientResponse])
def list_clients(tenant: TenantDep, db: DBDep) -> list[ClientResponse]:
    with db.cursor() as cur:
        cur.execute(f"SELECT {_CLIENT_COLS} FROM clients ORDER BY created_at")
        return [ClientResponse(**r) for r in cur.fetchall()]


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, tenant: TenantDep, db: DBDep) -> ProjectResponse:
    with db.cursor() as cur:
        cur.execute("SELECT id FROM clients WHERE id = %s", (body.client_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Client not found")
        cur.execute(
            f"""
            INSERT INTO projects (bureau_id, client_id, name, reporting_year, methodology_id,
                                  reporting_frameworks, sector_code, language, ndc_target_year, ndc_baseline_year)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_PROJECT_COLS}
            """,
            (
                tenant.bureau_id, body.client_id, body.name, body.reporting_year, body.methodology_id,
                body.reporting_frameworks, body.sector_code, body.language, body.ndc_target_year, body.ndc_baseline_year,
            ),
        )
        row = cur.fetchone()
    return ProjectResponse(**row)


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(tenant: TenantDep, db: DBDep) -> list[ProjectResponse]:
    with db.cursor() as cur:
        cur.execute(f"SELECT {_PROJECT_COLS} FROM projects ORDER BY created_at")
        return [ProjectResponse(**r) for r in cur.fetchall()]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, tenant: TenantDep, db: DBDep) -> ProjectResponse:
    with db.cursor() as cur:
        cur.execute(f"SELECT {_PROJECT_COLS} FROM projects WHERE id = %s", (project_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    return ProjectResponse(**row)


@router.get("/projects/{project_id}/summary")
def get_project_summary(project_id: str, tenant: TenantDep, db: DBDep) -> dict:
    """Aggregated summary: last snapshot totals, anomaly count, RSE status, facts counts."""
    with db.cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Project not found")

        cur.execute(
            """
            SELECT totals_co2e, gri_305_data, ndc_alignment, created_at, reporting_year
            FROM report_snapshots
            WHERE project_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
        snap = cur.fetchone()

        cur.execute(
            "SELECT state, COUNT(*) as n FROM activity_facts WHERE project_id = %s GROUP BY state",
            (project_id,),
        )
        facts_by_state = {r["state"]: r["n"] for r in cur.fetchall()}

        cur.execute(
            "SELECT COUNT(*) as n FROM anomalies WHERE project_id = %s AND resolved = FALSE",
            (project_id,),
        )
        open_anomalies = cur.fetchone()["n"]

        cur.execute(
            "SELECT COUNT(*) as n FROM rse_scores WHERE project_id = %s",
            (project_id,),
        )
        rse_count = cur.fetchone()["n"]

    return {
        "last_snapshot": {
            "created_at": snap["created_at"].isoformat() if snap and snap["created_at"] else None,
            "reporting_year": snap["reporting_year"] if snap else None,
            "totals_co2e": snap["totals_co2e"] if snap else None,
            "gri_305_data": snap["gri_305_data"] if snap else None,
            "ndc_progress_pct": (
                snap["ndc_alignment"].get("progress_pct") if snap and snap["ndc_alignment"] else None
            ),
        } if snap else None,
        "facts": {
            "proposed": facts_by_state.get("proposed", 0),
            "validated": facts_by_state.get("validated", 0),
            "total": sum(facts_by_state.values()),
        },
        "open_anomalies": open_anomalies,
        "rse_scores_count": rse_count,
    }
