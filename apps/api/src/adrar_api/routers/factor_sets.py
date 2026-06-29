"""READ endpoints: factor sets and unit conversions."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..deps import DBDep, TenantDep
from ..models.responses import ConversionResponse, FactorSetSummary

router = APIRouter()


@router.get("/methodologies")
def list_methodologies(tenant: TenantDep, db: DBDep) -> list[dict]:
    """Return all available methodologies (id, name, code)."""
    with db.cursor() as cur:
        cur.execute("SELECT id, name, code FROM methodologies ORDER BY name")
        return [dict(r) for r in cur.fetchall()]


@router.get("/factor-sets", response_model=list[FactorSetSummary])
def search_factor_sets(
    tenant: TenantDep,
    db: DBDep,
    methodology_id: str | None = Query(default=None),
    region: str | None = Query(default=None),
    year: int | None = Query(default=None),
) -> list[FactorSetSummary]:
    """Return factor sets, optionally filtered by methodology, region, and reporting year."""
    with db.cursor() as cur:
        conditions: list[str] = []
        params: list = []

        if methodology_id:
            conditions.append("methodology_id = %s")
            params.append(methodology_id)
        if region:
            conditions.append("(region = %s OR region IS NULL)")
            params.append(region)
        if year:
            on_date = date(year, 12, 31)
            conditions.append("effective_from <= %s AND (effective_to IS NULL OR effective_to >= %s)")
            params.extend([on_date, on_date])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        cur.execute(
            f"""
            SELECT id, methodology_id, name, version, effective_from, effective_to,
                   gwp_basis, region
            FROM factor_sets {where}
            ORDER BY effective_from DESC
            """,
            params,
        )
        return [FactorSetSummary(**r) for r in cur.fetchall()]


@router.get("/conversions", response_model=ConversionResponse)
def get_conversion(
    tenant: TenantDep,
    db: DBDep,
    from_unit: str = Query(...),
    to_unit: str = Query(...),
    fuel_type: str | None = Query(default=None),
    year: int = Query(default=2024),
) -> ConversionResponse:
    """
    Resolve a unit conversion path using the stored conversion_factors graph.
    Returns the combined coefficient and every intermediate step.
    """
    from decimal import Decimal

    from adrar_kernel import ConversionEdge, ConversionError, resolve_conversion

    on_date = date(year, 12, 31)

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, from_unit, to_unit, coefficient, conversion_type, fuel_type,
                   source, effective_from, effective_to
            FROM conversion_factors
            WHERE effective_from <= %s AND (effective_to IS NULL OR effective_to >= %s)
            """,
            (on_date, on_date),
        )
        edges = [
            ConversionEdge(
                id=str(r["id"]),
                from_unit=r["from_unit"],
                to_unit=r["to_unit"],
                coefficient=Decimal(str(r["coefficient"])),
                conversion_type=r["conversion_type"],
                fuel_type=r["fuel_type"],
                source=r["source"],
                effective_from=r["effective_from"],
                effective_to=r["effective_to"],
            )
            for r in cur.fetchall()
        ]

    try:
        chain = resolve_conversion(edges, from_unit, to_unit, fuel_type, on_date)
    except ConversionError as exc:
        raise HTTPException(404, str(exc)) from exc

    return ConversionResponse(
        from_unit=from_unit,
        to_unit=to_unit,
        fuel_type=fuel_type,
        combined_coefficient=chain.combined_coefficient,
        steps=[
            {
                "edge_id": s.edge_id,
                "from_unit": s.from_unit,
                "to_unit": s.to_unit,
                "coefficient": str(s.coefficient),
                "conversion_type": s.conversion_type,
                "fuel_type": s.fuel_type,
            }
            for s in chain.steps
        ],
    )
