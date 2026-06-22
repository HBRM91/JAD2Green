"""
Activity facts: propose (write proposed only) and read.

Invariant §0.3: propose_activity may only write state='proposed'.
Validated state is set exclusively through the UI validation gate (Phase 6).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ..deps import DBDep, TenantDep
from ..models.requests import ProposeActivityRequest
from ..models.responses import ActivityFactResponse

router = APIRouter()


@router.post(
    "/projects/{project_id}/activity",
    response_model=ActivityFactResponse,
    status_code=201,
)
def propose_activity(
    project_id: str,
    body: ProposeActivityRequest,
    tenant: TenantDep,
    db: DBDep,
) -> ActivityFactResponse:
    """
    Write a proposed activity fact. State is always 'proposed' — never 'validated'.
    §0.3: the Pydantic validator rejects state != 'proposed' before this runs.
    """
    # Belt-and-suspenders: force state regardless of what the validated model says
    assert body.state == "proposed", "Invariant §0.3 violated: state must be proposed"

    with db.cursor() as cur:
        # Verify project belongs to this bureau (RLS enforces, but explicit = 404 not 500)
        cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Project not found")

        cur.execute(
            """
            INSERT INTO activity_facts
                (bureau_id, project_id, category, sub_category, description,
                 activity_value, activity_unit, period_start, period_end,
                 scope, scope2_type, state, provenance, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'proposed',%s,%s)
            RETURNING
                id, bureau_id, project_id, category, sub_category, description,
                activity_value, activity_unit, period_start, period_end,
                scope, scope2_type, state, provenance, created_at
            """,
            (
                tenant.bureau_id,
                project_id,
                body.category,
                body.sub_category,
                body.description,
                str(body.activity_value),
                body.activity_unit,
                body.period_start,
                body.period_end,
                body.scope,
                body.scope2_type,
                json.dumps(body.provenance),
                tenant.user_id,
            ),
        )
        row = cur.fetchone()
    return ActivityFactResponse(**row)


@router.get(
    "/projects/{project_id}/activity",
    response_model=list[ActivityFactResponse],
)
def get_activity_data(
    project_id: str,
    tenant: TenantDep,
    db: DBDep,
    state: str | None = None,
) -> list[ActivityFactResponse]:
    """Return activity facts for a project, optionally filtered by state."""
    with db.cursor() as cur:
        if state:
            cur.execute(
                """
                SELECT id, bureau_id, project_id, category, sub_category, description,
                       activity_value, activity_unit, period_start, period_end,
                       scope, scope2_type, state, provenance, created_at
                FROM activity_facts
                WHERE project_id = %s AND state = %s
                ORDER BY created_at
                """,
                (project_id, state),
            )
        else:
            cur.execute(
                """
                SELECT id, bureau_id, project_id, category, sub_category, description,
                       activity_value, activity_unit, period_start, period_end,
                       scope, scope2_type, state, provenance, created_at
                FROM activity_facts
                WHERE project_id = %s
                ORDER BY created_at
                """,
                (project_id,),
            )
        return [ActivityFactResponse(**r) for r in cur.fetchall()]


@router.patch(
    "/projects/{project_id}/activity/{fact_id}/validate",
    response_model=ActivityFactResponse,
)
def validate_activity_fact(
    project_id: str,
    fact_id: str,
    tenant: TenantDep,
    db: DBDep,
) -> ActivityFactResponse:
    """
    Human-only validation gate: promote a proposed fact to validated.
    This is the ONLY code path that may write 'validated' state (§0 inv 3 + 4).
    Called by the consultant UI validation gate (Phase 6).
    """
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE activity_facts
            SET state = 'validated', validated_by = %s, validated_at = NOW()
            WHERE id = %s AND project_id = %s AND state = 'proposed'
            RETURNING
                id, bureau_id, project_id, category, sub_category, description,
                activity_value, activity_unit, period_start, period_end,
                scope, scope2_type, state, provenance, created_at
            """,
            (tenant.user_id, fact_id, project_id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Fact not found or already validated")
    return ActivityFactResponse(**row)
