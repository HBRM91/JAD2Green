"""
Report generation and delivery endpoints.

GET  /projects/{project_id}/snapshots/{snap_id}/report  → DOCX download (default)
POST /projects/{project_id}/snapshots/{snap_id}/export  → Google Docs (opt-in, default OFF)

§0.11 — export endpoint gated by bureau.google_export_enabled.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..deps import DBDep, TenantDep

router = APIRouter()


def _fetch_report_context(db, project_id: str, snap_id: str) -> tuple[dict, str, str, str]:
    """Fetch snapshot + project/client/methodology names. Returns (snapshot, proj, client, method)."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT rs.id, rs.bureau_id, rs.project_id, rs.reporting_year, rs.state_hash,
                   rs.totals_co2e, rs.scope2_location_t, rs.scope2_market_t,
                   rs.computation_trace, rs.factor_set_versions, rs.gwp_basis,
                   rs.uncertainty, rs.reconciliation, rs.created_at
            FROM report_snapshots rs
            WHERE rs.id = %s AND rs.project_id = %s
            """,
            (snap_id, project_id),
        )
        snap_row = cur.fetchone()
        if not snap_row:
            raise HTTPException(404, "Snapshot not found")

        cur.execute(
            """
            SELECT p.name AS project_name, c.name AS client_name, m.name AS method_name
            FROM projects p
            JOIN clients c ON c.id = p.client_id
            JOIN methodologies m ON m.id = p.methodology_id
            WHERE p.id = %s
            """,
            (project_id,),
        )
        meta = cur.fetchone()
        if not meta:
            raise HTTPException(404, "Project metadata not found")

    snapshot = {
        "id": str(snap_row["id"]),
        "bureau_id": str(snap_row["bureau_id"]),
        "project_id": str(snap_row["project_id"]),
        "reporting_year": snap_row["reporting_year"],
        "state_hash": snap_row["state_hash"],
        "totals_co2e": snap_row["totals_co2e"],
        "scope2_location_t": str(snap_row["scope2_location_t"]) if snap_row["scope2_location_t"] else None,
        "scope2_market_t": str(snap_row["scope2_market_t"]) if snap_row["scope2_market_t"] else None,
        "computation_trace": snap_row["computation_trace"],
        "factor_set_versions": snap_row["factor_set_versions"],
        "gwp_basis": snap_row["gwp_basis"],
        "uncertainty": snap_row["uncertainty"],
        "reconciliation": snap_row["reconciliation"],
    }
    return snapshot, meta["project_name"], meta["client_name"], meta["method_name"]


@router.get("/projects/{project_id}/snapshots/{snap_id}/report")
def download_report(
    project_id: str,
    snap_id: str,
    tenant: TenantDep,
    db: DBDep,
) -> Response:
    """
    Build and return a Bilan Carbone DOCX report for download.
    Report is built from snapshot aggregates only (§0.11).
    """
    from adrar_worker.report.charts import (
        category_bar_chart,
        scope2_comparison_bar,
        scope_pie_chart,
    )
    from adrar_worker.report.narrative import generate_narrative
    from adrar_worker.report.renderer import render_bilan_carbone_docx

    snapshot, proj_name, client_name, method_name = _fetch_report_context(db, project_id, snap_id)
    totals = snapshot.get("totals_co2e", {})

    charts = {
        "scope_pie": scope_pie_chart(totals),
        "category_bar": category_bar_chart(snapshot.get("computation_trace", [])),
        "scope2_bar": scope2_comparison_bar(totals),
    }
    narrative = generate_narrative(
        totals=totals,
        uncertainty=snapshot.get("uncertainty", {}),
        project_name=proj_name,
        reporting_year=snapshot["reporting_year"],
        methodology_name=method_name,
        gwp_basis=snapshot.get("gwp_basis", "AR5"),
    )
    docx_bytes = render_bilan_carbone_docx(
        snapshot=snapshot,
        project_name=proj_name,
        client_name=client_name,
        methodology_name=method_name,
        narrative=narrative,
        charts=charts,
    )

    filename = f"bilan_carbone_{project_id}_{snapshot['reporting_year']}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/projects/{project_id}/snapshots/{snap_id}/export")
def export_to_google_docs(
    project_id: str,
    snap_id: str,
    tenant: TenantDep,
    db: DBDep,
    google_access_token: str = "",
) -> dict:
    """
    Export report to Google Docs (opt-in, default OFF — §0.11).

    Requires bureau.google_export_enabled = True.
    Only the aggregate DOCX is sent to Google — no raw facts or documents.
    One-way: Google edits never sync back.
    """
    from adrar_worker.report.charts import (
        category_bar_chart,
        scope2_comparison_bar,
        scope_pie_chart,
    )
    from adrar_worker.report.delivery import (
        GoogleExportDisabledError,
        GoogleExportNotConfiguredError,
        google_docs_export,
    )
    from adrar_worker.report.narrative import generate_narrative
    from adrar_worker.report.renderer import render_bilan_carbone_docx

    # Check bureau opt-in (§0.11: Google export default OFF)
    with db.cursor() as cur:
        cur.execute(
            "SELECT google_export_enabled FROM bureaus WHERE id = %s",
            (tenant.bureau_id,),
        )
        bureau = cur.fetchone()

    bureau_enabled = bureau["google_export_enabled"] if bureau else False

    snapshot, proj_name, client_name, method_name = _fetch_report_context(db, project_id, snap_id)
    totals = snapshot.get("totals_co2e", {})

    charts = {
        "scope_pie": scope_pie_chart(totals),
        "category_bar": category_bar_chart(snapshot.get("computation_trace", [])),
        "scope2_bar": scope2_comparison_bar(totals),
    }
    narrative = generate_narrative(
        totals=totals,
        uncertainty=snapshot.get("uncertainty", {}),
        project_name=proj_name,
        reporting_year=snapshot["reporting_year"],
        methodology_name=method_name,
        gwp_basis=snapshot.get("gwp_basis", "AR5"),
    )
    docx_bytes = render_bilan_carbone_docx(
        snapshot=snapshot,
        project_name=proj_name,
        client_name=client_name,
        methodology_name=method_name,
        narrative=narrative,
        charts=charts,
    )

    try:
        return google_docs_export(
            docx_bytes=docx_bytes,
            bureau_google_export_enabled=bureau_enabled,
            google_access_token=google_access_token or None,
            filename=f"Bilan Carbone {proj_name} {snapshot['reporting_year']}",
        )
    except GoogleExportDisabledError as exc:
        raise HTTPException(403, str(exc)) from exc
    except GoogleExportNotConfiguredError as exc:
        raise HTTPException(422, str(exc)) from exc
