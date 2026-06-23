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
