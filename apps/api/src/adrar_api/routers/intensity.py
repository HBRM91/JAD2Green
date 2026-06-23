"""GRI 305-4 intensity denominator configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..deps import DBDep, TenantDep

router = APIRouter()


class IntensityConfigCreate(BaseModel):
    denominator_type: str
    denominator_value: float
    reporting_year: int


@router.get("/intensity-denominators")
def list_denominators(tenant: TenantDep, db: DBDep) -> list[dict]:
    """Return all available intensity denominator types."""
    with db.cursor() as cur:
        cur.execute("SELECT code, description, unit, sector FROM intensity_denominators ORDER BY sector, code")
        return [dict(r) for r in cur.fetchall()]


@router.get("/projects/{project_id}/intensity-config")
def list_intensity_config(project_id: str, tenant: TenantDep, db: DBDep) -> list[dict]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT pic.id, pic.denominator_type, pic.denominator_value, pic.reporting_year,
                   id.description, id.unit
            FROM project_intensity_config pic
            JOIN intensity_denominators id ON id.code = pic.denominator_type
            WHERE pic.project_id = %s
            ORDER BY pic.reporting_year DESC, pic.denominator_type
            """,
            (project_id,),
        )
        return [dict(r) for r in cur.fetchall()]


@router.post("/projects/{project_id}/intensity-config", status_code=201)
def upsert_intensity_config(project_id: str, body: IntensityConfigCreate, tenant: TenantDep, db: DBDep) -> dict:
    """Upsert denominator value for GRI 305-4 intensity ratio computation."""
    with db.cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Project not found")

        cur.execute(
            """
            INSERT INTO project_intensity_config (project_id, denominator_type, denominator_value, reporting_year)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (project_id, denominator_type, reporting_year) DO UPDATE
                SET denominator_value = EXCLUDED.denominator_value
            RETURNING id, project_id, denominator_type, denominator_value, reporting_year
            """,
            (project_id, body.denominator_type, body.denominator_value, body.reporting_year),
        )
        return dict(cur.fetchone())
