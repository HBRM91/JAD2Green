"""Flag anomaly endpoint (PROPOSE tier)."""

from __future__ import annotations

from fastapi import APIRouter

from ..deps import DBDep, TenantDep
from ..models.requests import FlagAnomalyRequest
from ..models.responses import AnomalyResponse

router = APIRouter()


@router.post(
    "/projects/{project_id}/anomalies",
    response_model=AnomalyResponse,
    status_code=201,
)
def flag_anomaly(
    project_id: str,
    body: FlagAnomalyRequest,
    tenant: TenantDep,
    db: DBDep,
) -> AnomalyResponse:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO anomalies
                (bureau_id, project_id, activity_fact_id, anomaly_type, severity, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, bureau_id, project_id, activity_fact_id, anomaly_type,
                      severity, description, resolved, created_at
            """,
            (
                tenant.bureau_id,
                project_id,
                body.activity_fact_id,
                body.anomaly_type,
                body.severity,
                body.description,
            ),
        )
        row = cur.fetchone()
    return AnomalyResponse(**row)
