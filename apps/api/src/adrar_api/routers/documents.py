"""
Document upload endpoint → triggers ingestion Celery task.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException, UploadFile

from ..deps import DBDep, TenantDep

router = APIRouter()

_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/projects/{project_id}/documents", status_code=202)
async def upload_document(
    project_id: str,
    file: UploadFile,
    tenant: TenantDep,
    db: DBDep,
) -> dict:
    """
    Accept a document upload and enqueue an ingestion task.
    Returns 202 Accepted with doc metadata; extraction happens asynchronously.
    """
    # Verify project visibility (RLS enforces bureau isolation)
    with db.cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Project not found")

    content = await file.read()
    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(413, f"File too large (max {_MAX_SIZE_BYTES // 1024 // 1024} MB)")

    filename = file.filename or "upload"
    content_type = file.content_type or "application/octet-stream"

    # Enqueue Celery task (import here to avoid circular deps at module level)
    from adrar_worker.tasks.ingest import ingest_document

    task = ingest_document.delay(
        content_b64=base64.b64encode(content).decode(),
        bureau_id=tenant.bureau_id,
        project_id=project_id,
        filename=filename,
        content_type=content_type,
        user_id=tenant.user_id,
    )

    return {
        "task_id": task.id,
        "filename": filename,
        "size_bytes": len(content),
        "status": "queued",
    }
