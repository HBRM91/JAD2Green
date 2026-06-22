"""
Celery task: generate Bilan Carbone DOCX report from a report_snapshot.

§0.11 — Only snapshot aggregate data is used. Raw facts never touch this pipeline.
"""

from __future__ import annotations

import logging

from ..celery_app import app
from ..report.charts import category_bar_chart, scope2_comparison_bar, scope_pie_chart
from ..report.delivery import download_docx
from ..report.narrative import generate_narrative
from ..report.renderer import render_bilan_carbone_docx

log = logging.getLogger(__name__)


def build_report(
    snapshot: dict,
    project_name: str,
    client_name: str,
    methodology_name: str,
) -> bytes:
    """
    Pure report-building pipeline — callable directly in tests.

    Args:
        snapshot: report_snapshot row (aggregate fields only — §0.11)
        project_name, client_name, methodology_name: metadata from DB

    Returns:
        DOCX bytes
    """
    totals = snapshot.get("totals_co2e", {})
    trace = snapshot.get("computation_trace", [])

    # Generate charts from snapshot aggregates
    charts = {
        "scope_pie": scope_pie_chart(totals),
        "category_bar": category_bar_chart(trace),
        "scope2_bar": scope2_comparison_bar(totals),
    }

    # Generate LLM narrative (outside kernel, from aggregates only)
    narrative = generate_narrative(
        totals=totals,
        uncertainty=snapshot.get("uncertainty", {}),
        project_name=project_name,
        reporting_year=snapshot.get("reporting_year", "—"),
        methodology_name=methodology_name,
        gwp_basis=snapshot.get("gwp_basis", "AR5"),
    )

    return render_bilan_carbone_docx(
        snapshot=snapshot,
        project_name=project_name,
        client_name=client_name,
        methodology_name=methodology_name,
        narrative=narrative,
        charts=charts,
    )


@app.task(bind=True, name="adrar_worker.generate_report", max_retries=2)
def generate_report_task(
    self,
    snapshot: dict,
    project_name: str,
    client_name: str,
    methodology_name: str,
) -> dict:
    """
    Celery task wrapping build_report.
    Returns {'docx_b64': <base64>, 'size_bytes': <int>}.
    """
    import base64
    try:
        docx_bytes = build_report(snapshot, project_name, client_name, methodology_name)
        result = download_docx(docx_bytes)
        return {
            "docx_b64": base64.b64encode(docx_bytes).decode(),
            "size_bytes": result["size_bytes"],
            "filename": result["filename"],
        }
    except Exception as exc:
        log.exception("Report generation failed for snapshot %s", snapshot.get("id"))
        raise self.retry(exc=exc) from exc
