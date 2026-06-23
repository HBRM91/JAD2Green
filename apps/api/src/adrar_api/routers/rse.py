"""RSE (Rapport RSE BVC) and AMEE energy audit endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..deps import DBDep, TenantDep

router = APIRouter()


class RseScoreCreate(BaseModel):
    reporting_year: int
    # Pilier Environnemental
    e_ghg_scope1: float | None = None
    e_ghg_scope2: float | None = None
    e_ghg_scope3: float | None = None
    e_energy_total: float | None = None
    e_energy_renew: float | None = None
    e_water_total: float | None = None
    e_water_recycle: float | None = None
    e_waste_total: float | None = None
    e_waste_recycle: float | None = None
    # Pilier Social
    s_employees_total: int | None = None
    s_women_pct: float | None = None
    s_training_hours: float | None = None
    s_accidents_rate: float | None = None
    # Pilier Gouvernance
    g_board_women_pct: float | None = None
    g_independent_pct: float | None = None
    notes: str | None = None


_RSE_COLS = """id, bureau_id, project_id, reporting_year,
    e_ghg_scope1, e_ghg_scope2, e_ghg_scope3,
    e_energy_total, e_energy_renew,
    e_water_total, e_water_recycle,
    e_waste_total, e_waste_recycle,
    s_employees_total, s_women_pct, s_training_hours, s_accidents_rate,
    g_board_women_pct, g_independent_pct,
    methodology_ref, notes, created_at"""


@router.get("/projects/{project_id}/rse", response_model=list[dict])
def list_rse_scores(project_id: str, tenant: TenantDep, db: DBDep) -> list[dict]:
    with db.cursor() as cur:
        cur.execute(
            f"SELECT {_RSE_COLS} FROM rse_scores WHERE project_id = %s ORDER BY reporting_year DESC",
            (project_id,),
        )
        return [dict(r) for r in cur.fetchall()]


@router.post("/projects/{project_id}/rse", status_code=201)
def upsert_rse_score(project_id: str, body: RseScoreCreate, tenant: TenantDep, db: DBDep) -> dict:
    """Upsert RSE score for a project/year. Used by BVC-listed company RSE reporting."""
    with db.cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Project not found")

        cur.execute(
            f"""
            INSERT INTO rse_scores
                (bureau_id, project_id, reporting_year,
                 e_ghg_scope1, e_ghg_scope2, e_ghg_scope3,
                 e_energy_total, e_energy_renew,
                 e_water_total, e_water_recycle,
                 e_waste_total, e_waste_recycle,
                 s_employees_total, s_women_pct, s_training_hours, s_accidents_rate,
                 g_board_women_pct, g_independent_pct, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (project_id, reporting_year) DO UPDATE SET
                e_ghg_scope1 = EXCLUDED.e_ghg_scope1,
                e_ghg_scope2 = EXCLUDED.e_ghg_scope2,
                e_ghg_scope3 = EXCLUDED.e_ghg_scope3,
                e_energy_total = EXCLUDED.e_energy_total,
                e_energy_renew = EXCLUDED.e_energy_renew,
                e_water_total = EXCLUDED.e_water_total,
                e_water_recycle = EXCLUDED.e_water_recycle,
                e_waste_total = EXCLUDED.e_waste_total,
                e_waste_recycle = EXCLUDED.e_waste_recycle,
                s_employees_total = EXCLUDED.s_employees_total,
                s_women_pct = EXCLUDED.s_women_pct,
                s_training_hours = EXCLUDED.s_training_hours,
                s_accidents_rate = EXCLUDED.s_accidents_rate,
                g_board_women_pct = EXCLUDED.g_board_women_pct,
                g_independent_pct = EXCLUDED.g_independent_pct,
                notes = EXCLUDED.notes
            RETURNING {_RSE_COLS}
            """,
            (
                tenant.bureau_id, project_id, body.reporting_year,
                body.e_ghg_scope1, body.e_ghg_scope2, body.e_ghg_scope3,
                body.e_energy_total, body.e_energy_renew,
                body.e_water_total, body.e_water_recycle,
                body.e_waste_total, body.e_waste_recycle,
                body.s_employees_total, body.s_women_pct,
                body.s_training_hours, body.s_accidents_rate,
                body.g_board_women_pct, body.g_independent_pct,
                body.notes,
            ),
        )
        return dict(cur.fetchone())
