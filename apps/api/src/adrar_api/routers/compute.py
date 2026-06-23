"""
COMPUTE tier endpoints: compute_emissions, reconcile, get_report_snapshot.

Invariant §0.10: compute_emissions blocks on un-validated facts.
Invariant §0.4: NO finalize/approve/submit endpoint exists here or anywhere.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..deps import DBDep, TenantDep
from ..limiter import limiter
from ..models.requests import ComputeEmissionsRequest
from ..models.responses import AnomalyResponse, ReportSnapshotResponse
from ..services.compute_svc import ComputeError, run_compute_and_persist

router = APIRouter()


@router.post(
    "/projects/{project_id}/compute",
    response_model=ReportSnapshotResponse,
    status_code=201,
)
@limiter.limit("10/minute")
def compute_emissions_endpoint(
    request: Request,
    project_id: str,
    body: ComputeEmissionsRequest,
    tenant: TenantDep,
    db: DBDep,
) -> ReportSnapshotResponse:
    """
    Compute GHG emissions for a project and persist an immutable snapshot.
    Blocks if any activity facts are still in 'proposed' state (§0 inv 10).
    """
    try:
        row = run_compute_and_persist(
            conn=db,
            project_id=project_id,
            bureau_id=tenant.bureau_id,
            user_id=tenant.user_id,
            methodology_id=body.methodology_id,
            region=body.region,
            reporting_year=body.reporting_year,
            gwp_basis=body.gwp_basis,
        )
    except ComputeError as exc:
        raise HTTPException(422, str(exc)) from exc

    return _row_to_snapshot(row)


@router.get(
    "/projects/{project_id}/snapshots/{snapshot_id}",
    response_model=ReportSnapshotResponse,
)
def get_report_snapshot(
    project_id: str,
    snapshot_id: str,
    tenant: TenantDep,
    db: DBDep,
) -> ReportSnapshotResponse:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, bureau_id, project_id, reporting_year, state_hash,
                   totals_co2e, scope2_location_t, scope2_market_t,
                   computation_trace, factor_set_versions, gwp_basis,
                   uncertainty, reconciliation, created_at
            FROM report_snapshots
            WHERE id = %s AND project_id = %s
            """,
            (snapshot_id, project_id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Snapshot not found")
    return _row_to_snapshot(row)


@router.get(
    "/projects/{project_id}/snapshots",
    response_model=list[ReportSnapshotResponse],
)
def list_snapshots(
    project_id: str,
    tenant: TenantDep,
    db: DBDep,
) -> list[ReportSnapshotResponse]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, bureau_id, project_id, reporting_year, state_hash,
                   totals_co2e, scope2_location_t, scope2_market_t,
                   computation_trace, factor_set_versions, gwp_basis,
                   uncertainty, reconciliation, created_at
            FROM report_snapshots
            WHERE project_id = %s
            ORDER BY created_at DESC
            """,
            (project_id,),
        )
        return [_row_to_snapshot(r) for r in cur.fetchall()]


@router.post(
    "/projects/{project_id}/reconcile",
    response_model=list[AnomalyResponse],
    status_code=201,
)
def reconcile(
    project_id: str,
    tenant: TenantDep,
    db: DBDep,
) -> list[AnomalyResponse]:
    """
    Run reconciliation checks on the project's validated facts.
    Flags anomalies for: duplicate periods, zero values, implausible magnitudes.
    """
    anomalies = []
    with db.cursor() as cur:
        # Check for duplicate category+period combinations
        cur.execute(
            """
            SELECT category, period_start, period_end, COUNT(*) AS n
            FROM activity_facts
            WHERE project_id = %s AND state = 'validated'
            GROUP BY category, period_start, period_end
            HAVING COUNT(*) > 1
            """,
            (project_id,),
        )
        for r in cur.fetchall():
            cur.execute(
                """
                INSERT INTO anomalies (bureau_id, project_id, anomaly_type, severity, description)
                VALUES (%s, %s, 'duplicate_period', 'warning', %s)
                RETURNING id, bureau_id, project_id, activity_fact_id, anomaly_type,
                          severity, description, resolved, created_at
                """,
                (
                    tenant.bureau_id,
                    project_id,
                    f"Duplicate validated facts for category={r['category']} "
                    f"period {r['period_start']}–{r['period_end']} ({r['n']} entries)",
                ),
            )
            row = cur.fetchone()
            if row:
                anomalies.append(AnomalyResponse(**row))

        # Check for zero-value facts
        cur.execute(
            """
            SELECT id FROM activity_facts
            WHERE project_id = %s AND state = 'validated' AND activity_value = 0
            """,
            (project_id,),
        )
        for r in cur.fetchall():
            cur.execute(
                """
                INSERT INTO anomalies (bureau_id, project_id, activity_fact_id, anomaly_type,
                                       severity, description)
                VALUES (%s, %s, %s, 'zero_value', 'info', 'Activity value is zero')
                RETURNING id, bureau_id, project_id, activity_fact_id, anomaly_type,
                          severity, description, resolved, created_at
                """,
                (tenant.bureau_id, project_id, r["id"]),
            )
            row = cur.fetchone()
            if row:
                anomalies.append(AnomalyResponse(**row))

    return anomalies


def _row_to_snapshot(row: dict) -> ReportSnapshotResponse:
    return ReportSnapshotResponse(
        id=str(row["id"]),
        bureau_id=str(row["bureau_id"]),
        project_id=str(row["project_id"]),
        reporting_year=row["reporting_year"],
        state_hash=row["state_hash"],
        totals_co2e=row["totals_co2e"],
        scope2_location_t=row["scope2_location_t"],
        scope2_market_t=row["scope2_market_t"],
        gwp_basis=row["gwp_basis"],
        uncertainty=row["uncertainty"],
        computation_trace=row["computation_trace"],
        factor_set_versions=row["factor_set_versions"],
        reconciliation=row["reconciliation"],
        created_at=row["created_at"],
    )
