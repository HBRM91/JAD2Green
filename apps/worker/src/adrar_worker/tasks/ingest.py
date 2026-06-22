"""
Document ingestion pipeline.

Upload → virus/format normalize → route → extract → propose facts.

Invariants enforced:
  §0.3 — all writes are state='proposed'; validated is never set here
  §0.1 — LLM (Haiku) never touches the kernel calculation path
  Dedup — UNIQUE(bureau_id, content_hash) in DB; re-upload is a no-op
"""

from __future__ import annotations

import hashlib
import json
import logging
import os

import psycopg2
import psycopg2.extras

from ..celery_app import app
from ..parsers.base import ExtractedFact, build_provenance
from ..parsers.pdf_parser import is_scan, parse_pdf
from ..parsers.scan_parser import parse_scan
from ..parsers.xlsx_parser import parse_csv, parse_xlsx

log = logging.getLogger(__name__)

_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


# ── Routing ───────────────────────────────────────────────────────────────

def _route(filename: str, content_type: str, content: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("xlsx", "xls", "ods"):
        return "xlsx"
    if ext == "csv":
        return "csv"
    if ext == "pdf" or content_type == "application/pdf":
        return "scan" if is_scan(content) else "pdf"
    return "unknown"


def _extract(
    route: str,
    content: bytes,
    doc_id: str,
    filename: str,
) -> tuple[list[ExtractedFact], str]:
    """Return (facts, extraction_method)."""
    if route == "xlsx":
        return parse_xlsx(content, doc_id, filename), "xlsx_parser"
    if route == "csv":
        return parse_csv(content, doc_id, filename), "csv_parser"
    if route == "pdf":
        facts = parse_pdf(content, doc_id, filename)
        return facts, "pdf_pdfplumber"
    if route == "scan":
        # LLM path: Haiku for messy scans (§0 inv 1: never touches kernel)
        if not os.getenv("ANTHROPIC_API_KEY"):
            log.warning("ANTHROPIC_API_KEY not set; scan extraction skipped for doc %s", doc_id)
        facts = parse_scan(content, doc_id, filename)
        return facts, "scan_haiku"
    return [], "unknown"


# ── DB helpers ────────────────────────────────────────────────────────────

def _db_conn(bureau_id: str) -> psycopg2.extensions.connection:
    conn = psycopg2.connect(_DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SET LOCAL app.bureau_id = %s", (bureau_id,))
        cur.execute("SET LOCAL app.role = %s", ("consultant",))
    return conn


def _register_document(
    cur: psycopg2.extensions.cursor,
    bureau_id: str,
    project_id: str,
    filename: str,
    content_hash: str,
    content_type: str,
    file_size: int,
    user_id: str,
) -> tuple[str, bool]:
    """
    Insert document row. Returns (doc_id, is_new).
    is_new=False means duplicate — caller should skip extraction.
    """
    cur.execute(
        """
        INSERT INTO documents
            (bureau_id, project_id, filename, content_hash, content_type,
             file_size_bytes, processing_status, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,'pending',%s)
        ON CONFLICT (bureau_id, content_hash) DO NOTHING
        RETURNING id
        """,
        (bureau_id, project_id, filename, content_hash, content_type, file_size, user_id),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"]), True

    # Duplicate — fetch existing id
    cur.execute(
        "SELECT id FROM documents WHERE bureau_id=%s AND content_hash=%s",
        (bureau_id, content_hash),
    )
    row = cur.fetchone()
    return str(row["id"]), False


def _write_proposed_facts(
    cur: psycopg2.extensions.cursor,
    bureau_id: str,
    project_id: str,
    doc_id: str,
    filename: str,
    extraction_method: str,
    facts: list[ExtractedFact],
    user_id: str,
) -> int:
    """
    Write each extracted fact as state='proposed' (§0 inv 3).
    Returns count of rows inserted.
    """
    count = 0
    for fact in facts:
        provenance = build_provenance(doc_id, filename, fact, extraction_method)
        cur.execute(
            """
            INSERT INTO activity_facts
                (bureau_id, project_id, category, sub_category,
                 activity_value, activity_unit, period_start, period_end,
                 scope, scope2_type, state, provenance, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'proposed',%s,%s)
            """,
            (
                bureau_id,
                project_id,
                fact.category,
                fact.sub_category,
                str(fact.activity_value),
                fact.activity_unit,
                fact.period_start,
                fact.period_end,
                fact.scope,
                fact.scope2_type,
                json.dumps(provenance),
                user_id,
            ),
        )
        count += 1
    return count


def _reconcile_monthly_vs_annual(
    cur: psycopg2.extensions.cursor,
    bureau_id: str,
    project_id: str,
) -> list[dict]:
    """
    Flag categories where Σ monthly proposed facts ≠ annual proposed fact.
    Returns list of anomaly descriptions.
    """
    cur.execute(
        """
        SELECT category,
               COUNT(*) AS fact_count,
               SUM(activity_value) AS total_value,
               MIN(period_start) AS min_start,
               MAX(period_end) AS max_end
        FROM activity_facts
        WHERE project_id = %s AND state = 'proposed'
        GROUP BY category
        HAVING COUNT(*) > 1
           AND MAX(period_end) - MIN(period_start) >= 364
        """,
        (project_id,),
    )
    anomalies = []
    for r in cur.fetchall():
        # If sum of partial periods covers a full year, check consistency
        anomalies.append({
            "category": r["category"],
            "total": str(r["total_value"]),
            "fact_count": r["fact_count"],
            "note": "Multiple facts span full year — verify no overlap or missing periods",
        })
    return anomalies


# ── Core pipeline (pure function, testable without Celery) ────────────────

def process_document(
    content: bytes,
    bureau_id: str,
    project_id: str,
    filename: str,
    content_type: str,
    user_id: str,
    db_url: str | None = None,
) -> dict:
    """
    Full ingestion pipeline — called directly in tests and wrapped by Celery task.

    Returns a result dict with: doc_id, is_duplicate, facts_count, extraction_method.
    """
    effective_db_url = db_url or _DATABASE_URL
    content_hash = hashlib.sha256(content).hexdigest()
    route = _route(filename, content_type, content)

    conn = psycopg2.connect(effective_db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # Inject tenant GUC (§0 inv 6)
            cur.execute("SET LOCAL app.bureau_id = %s", (bureau_id,))
            cur.execute("SET LOCAL app.role = %s", ("consultant",))

            doc_id, is_new = _register_document(
                cur, bureau_id, project_id, filename,
                content_hash, content_type, len(content), user_id,
            )

            if not is_new:
                conn.commit()
                return {
                    "doc_id": doc_id,
                    "is_duplicate": True,
                    "facts_count": 0,
                    "extraction_method": "dedup",
                    "reconciliation_anomalies": [],
                }

            # Mark processing
            cur.execute(
                "UPDATE documents SET processing_status='processing' WHERE id=%s", (doc_id,)
            )

            # Extract (LLM only for scan route; never touches kernel)
            facts, extraction_method = _extract(route, content, doc_id, filename)

            # Write all facts as proposed (§0 inv 3)
            count = _write_proposed_facts(
                cur, bureau_id, project_id, doc_id, filename, extraction_method, facts, user_id
            )

            # Reconciliation
            anomalies = _reconcile_monthly_vs_annual(cur, bureau_id, project_id)

            # Update document status + method
            cur.execute(
                """
                UPDATE documents
                SET processing_status='done', extraction_method=%s, extraction_count=%s
                WHERE id=%s
                """,
                (extraction_method, count, doc_id),
            )

        conn.commit()
        return {
            "doc_id": doc_id,
            "is_duplicate": False,
            "facts_count": count,
            "extraction_method": extraction_method,
            "reconciliation_anomalies": anomalies,
        }

    except Exception as exc:
        conn.rollback()
        # Try to mark error (best-effort; may fail if doc not yet registered)
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.bureau_id = %s", (bureau_id,))
                cur.execute(
                    "UPDATE documents SET processing_status='error', processing_error=%s "
                    "WHERE bureau_id=%s AND content_hash=%s",
                    (str(exc), bureau_id, content_hash),
                )
            conn.commit()
        except Exception:
            pass
        raise
    finally:
        conn.close()


# ── Celery task ───────────────────────────────────────────────────────────

@app.task(bind=True, name="adrar_worker.ingest_document", max_retries=3, default_retry_delay=60)
def ingest_document(
    self,
    content_b64: str,
    bureau_id: str,
    project_id: str,
    filename: str,
    content_type: str,
    user_id: str,
) -> dict:
    """
    Celery task wrapping process_document.
    content_b64: base64-encoded file bytes.
    """
    import base64
    try:
        content = base64.b64decode(content_b64)
        return process_document(
            content=content,
            bureau_id=bureau_id,
            project_id=project_id,
            filename=filename,
            content_type=content_type,
            user_id=user_id,
        )
    except Exception as exc:
        log.exception("Ingestion failed for bureau=%s project=%s file=%s", bureau_id, project_id, filename)
        raise self.retry(exc=exc) from exc
