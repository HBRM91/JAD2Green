"""Minimal CRUD for clients and projects."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..deps import DBDep, TenantDep
from ..models.requests import ClientCreate, ProjectCreate
from ..models.responses import ClientResponse, ProjectResponse

router = APIRouter()


@router.post("/clients", response_model=ClientResponse, status_code=201)
def create_client(body: ClientCreate, tenant: TenantDep, db: DBDep) -> ClientResponse:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO clients (bureau_id, name, sector)
            VALUES (%s, %s, %s)
            RETURNING id, bureau_id, name, sector, created_at
            """,
            (tenant.bureau_id, body.name, body.sector),
        )
        row = cur.fetchone()
    return ClientResponse(**row)


@router.get("/clients", response_model=list[ClientResponse])
def list_clients(tenant: TenantDep, db: DBDep) -> list[ClientResponse]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, bureau_id, name, sector, created_at FROM clients ORDER BY created_at"
        )
        return [ClientResponse(**r) for r in cur.fetchall()]


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, tenant: TenantDep, db: DBDep) -> ProjectResponse:
    with db.cursor() as cur:
        # Verify client belongs to this bureau (RLS enforces it, but explicit check gives 404)
        cur.execute("SELECT id FROM clients WHERE id = %s", (body.client_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Client not found")
        cur.execute(
            """
            INSERT INTO projects (bureau_id, client_id, name, reporting_year, methodology_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, bureau_id, client_id, name, reporting_year, methodology_id, status, created_at
            """,
            (tenant.bureau_id, body.client_id, body.name, body.reporting_year, body.methodology_id),
        )
        row = cur.fetchone()
    return ProjectResponse(**row)


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(tenant: TenantDep, db: DBDep) -> list[ProjectResponse]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, bureau_id, client_id, name, reporting_year, methodology_id, status, created_at
            FROM projects ORDER BY created_at
            """
        )
        return [ProjectResponse(**r) for r in cur.fetchall()]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, tenant: TenantDep, db: DBDep) -> ProjectResponse:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, bureau_id, client_id, name, reporting_year, methodology_id, status, created_at
            FROM projects WHERE id = %s
            """,
            (project_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    return ProjectResponse(**row)
