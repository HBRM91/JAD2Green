"""
Document upload endpoint → triggers ingestion Celery task.
"""

from __future__ import annotations

import base64
import os
import re

from fastapi import APIRouter, HTTPException, Request, UploadFile

from ..deps import DBDep, TenantDep
from ..limiter import limiter

router = APIRouter()

_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Allowlist of permitted MIME types — server-side enforcement
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "application/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Magic bytes for server-side file type detection (defence-in-depth)
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"PK\x03\x04", "application/zip-based"),   # XLSX and DOCX are ZIP-based
    # CSV has no magic bytes — allowed through if MIME type matches
]

# Filename sanitisation: allow only safe characters, strip path components
_UNSAFE_FILENAME = re.compile(r"[^\w\-. ]")


def _sanitize_filename(name: str) -> str:
    """Strip path traversal and dangerous characters from an upload filename."""
    # Take only the basename (no directory components)
    name = os.path.basename(name.replace("\\", "/"))
    # Replace any character outside word chars, dash, dot, space
    name = _UNSAFE_FILENAME.sub("_", name)
    # Truncate to 255 chars (filesystem limit)
    return name[:255] or "upload"


def _check_magic_bytes(content: bytes, claimed_type: str) -> None:
    """Reject files whose magic bytes contradict their claimed MIME type."""
    if not content:
        raise HTTPException(400, "Empty file")

    # PDFs must start with %PDF
    if claimed_type == "application/pdf":
        if not content.startswith(b"%PDF"):
            raise HTTPException(415, "File content does not match claimed type (PDF expected)")
        return

    # Office formats (XLSX, DOCX) must be ZIP-based
    if claimed_type in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(415, "File content does not match claimed type (Office format expected)")
        return

    # CSV: no magic bytes, accept as-is if MIME type is on allowlist


@router.post("/projects/{project_id}/documents", status_code=202)
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
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

    # Server-side MIME type allowlist check
    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, f"File type not supported: {content_type}")

    content = await file.read()

    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(413, f"File too large (max {_MAX_SIZE_BYTES // 1024 // 1024} MB)")

    # Magic-byte validation (server-side, cannot be spoofed by client)
    _check_magic_bytes(content, content_type)

    # Sanitize filename — prevents path traversal and XSS via stored filename
    safe_filename = _sanitize_filename(file.filename or "upload")

    from adrar_worker.tasks.ingest import ingest_document

    task = ingest_document.delay(
        content_b64=base64.b64encode(content).decode(),
        bureau_id=tenant.bureau_id,
        project_id=project_id,
        filename=safe_filename,
        content_type=content_type,
        user_id=tenant.user_id,
    )

    return {
        "task_id": task.id,
        "filename": safe_filename,
        "size_bytes": len(content),
        "status": "queued",
    }
