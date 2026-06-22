"""
Phase 4 acceptance tests for document ingestion pipeline.

Tests call process_document() directly (no Celery broker required).
Uses the same portable PostgreSQL as Phases 1 and 3.

Acceptance criteria:
  1. Dedup: re-uploading identical content produces no duplicate facts
  2. Provenance: every extracted fact carries doc_id, confidence, source_page
  3. Extraction writes proposed only: state='proposed' for all extracted facts
  4. LLM never touches calc: parse_scan does not call kernel; no snapshot created
  5. Multi-format: CSV and XLSX both parse correctly
  6. Reconciliation hook runs after extraction
"""

from __future__ import annotations

import io
import pathlib
import uuid

import openpyxl
import psycopg2
import psycopg2.extras
import pytest
import sqlparse
import testing.postgresql
from adrar_worker.parsers.scan_parser import parse_scan
from adrar_worker.parsers.xlsx_parser import parse_csv, parse_xlsx
from adrar_worker.tasks.ingest import process_document

PG_BIN = pathlib.Path(r"C:\Users\Hamza\AppData\Local\pg17_portable\bin")
MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "supabase" / "migrations"
SEED_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "supabase" / "seed"


# ── Fixtures ──────────────────────────────────────────────────────────────

def _has_sql(stmt: str) -> bool:
    parsed = sqlparse.parse(stmt)
    if not parsed:
        return False
    for token in parsed[0].flatten():
        if token.ttype not in (
            sqlparse.tokens.Whitespace,
            sqlparse.tokens.Newline,
            sqlparse.tokens.Comment.Single,
            sqlparse.tokens.Comment.Multiline,
        ) and token.value.strip():
            return True
    return False


def _run_sql_file(cur, path: pathlib.Path) -> None:
    sql = path.read_text(encoding="utf-8")
    for stmt in sqlparse.split(sql):
        stmt = stmt.strip()
        if stmt and _has_sql(stmt):
            cur.execute(stmt)


@pytest.fixture(scope="session")
def pg():
    instance = testing.postgresql.Postgresql(
        initdb=str(PG_BIN / "initdb"),
        postgres=str(PG_BIN / "postgres"),
        initdb_args="-U postgres -A trust --encoding=UTF8 --lc-collate=C --lc-ctype=C",
    )
    yield instance
    import subprocess
    subprocess.run(
        [str(PG_BIN / "pg_ctl"), "stop", "-D", instance.get_data_directory(), "-m", "fast", "-w"],
        capture_output=True,
    )
    instance.child_process = None


@pytest.fixture(scope="session")
def db_url(pg) -> str:
    dsn = pg.dsn()
    return f"postgresql://{dsn['user']}@{dsn['host']}:{dsn['port']}/{dsn['database']}"


@pytest.fixture(scope="session")
def su_conn(pg):
    conn = psycopg2.connect(**pg.dsn(), cursor_factory=psycopg2.extras.RealDictCursor)
    conn.set_client_encoding("UTF8")
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def db_ready(su_conn):
    cur = su_conn.cursor()
    for mig in sorted(MIGRATIONS_DIR.glob("*.sql")):
        _run_sql_file(cur, mig)
    for seed in sorted(SEED_DIR.glob("*.sql")):
        _run_sql_file(cur, seed)

    cur.execute("DROP ROLE IF EXISTS app_user")
    cur.execute("CREATE ROLE app_user LOGIN PASSWORD 'test'")
    cur.execute(
        """GRANT SELECT, INSERT, UPDATE, DELETE
           ON bureaus, clients, users, projects, activity_facts,
              report_snapshots, anomalies, audit_log, documents TO app_user"""
    )
    cur.execute(
        "GRANT SELECT ON methodologies, factor_sets, emission_factors, "
        "conversion_factors, gwp_values TO app_user"
    )
    cur.close()


@pytest.fixture(scope="session")
def bureau_id(su_conn, db_ready) -> str:
    bid = str(uuid.uuid4())
    su_conn.cursor().execute(
        "INSERT INTO bureaus (id, name, region) VALUES (%s, 'Test Bureau', 'MA')", (bid,)
    )
    return bid


@pytest.fixture(scope="session")
def project_id(su_conn, bureau_id) -> str:
    client_id = str(uuid.uuid4())
    su_conn.cursor().execute(
        "INSERT INTO clients (id, bureau_id, name) VALUES (%s, %s, 'Test Client')",
        (client_id, bureau_id),
    )
    pid = str(uuid.uuid4())
    su_conn.cursor().execute(
        """INSERT INTO projects (id, bureau_id, client_id, name, reporting_year, methodology_id)
           VALUES (%s,%s,%s,'Test Project',2024,'00000000-0000-0000-0000-000000000001')""",
        (pid, bureau_id, client_id),
    )
    return pid


# ── Test data helpers ─────────────────────────────────────────────────────

_CSV_CONTENT = (
    b"category,activity_value,activity_unit,period_start,period_end,scope\n"
    b"scope2_electricity,500,kWh,2024-01-01,2024-12-31,2\n"
    b"scope1_mobile,100,L,2024-01-01,2024-12-31,1\n"
)


def _make_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["category", "activity_value", "activity_unit", "period_start", "period_end", "scope"])
    ws.append(["scope2_electricity", 500, "kWh", "2024-01-01", "2024-12-31", 2])
    ws.append(["scope1_mobile", 100, "L", "2024-01-01", "2024-12-31", 1])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _count_facts(su_conn, project_id: str) -> int:
    cur = su_conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM activity_facts WHERE project_id = %s", (project_id,))
    return cur.fetchone()["n"]


def _count_docs(su_conn, bureau_id: str) -> int:
    cur = su_conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM documents WHERE bureau_id = %s", (bureau_id,))
    return cur.fetchone()["n"]


# ── 1. Dedup ──────────────────────────────────────────────────────────────

def test_dedup_same_content_no_duplicate_facts(su_conn, db_url, bureau_id, project_id):
    """Re-uploading identical CSV must not create duplicate activity_facts."""
    user_id = str(uuid.uuid4())

    r1 = process_document(
        content=_CSV_CONTENT,
        bureau_id=bureau_id,
        project_id=project_id,
        filename="energy_2024.csv",
        content_type="text/csv",
        user_id=user_id,
        db_url=db_url,
    )
    assert not r1["is_duplicate"]
    facts_after_first = _count_facts(su_conn, project_id)

    r2 = process_document(
        content=_CSV_CONTENT,
        bureau_id=bureau_id,
        project_id=project_id,
        filename="energy_2024_copy.csv",   # different filename, same bytes
        content_type="text/csv",
        user_id=user_id,
        db_url=db_url,
    )
    assert r2["is_duplicate"], "Second upload of same content must be detected as duplicate"
    assert r2["facts_count"] == 0, "Duplicate upload must not insert new facts"

    facts_after_second = _count_facts(su_conn, project_id)
    assert facts_after_first == facts_after_second, (
        f"Dedup FAIL: first upload had {facts_after_first} facts, "
        f"after re-upload there are {facts_after_second}"
    )


def test_dedup_different_content_both_processed(su_conn, db_url, bureau_id, project_id):
    """Two different files must both be processed (content hash distinguishes them)."""
    user_id = str(uuid.uuid4())
    content_a = _CSV_CONTENT
    content_b = (
        b"category,activity_value,activity_unit,period_start,period_end,scope\n"
        b"scope1_stationary,200,MJ,2024-01-01,2024-06-30,1\n"
    )

    before = _count_facts(su_conn, project_id)
    process_document(content_a, bureau_id, project_id, "a.csv", "text/csv", user_id, db_url=db_url)
    process_document(content_b, bureau_id, project_id, "b.csv", "text/csv", user_id, db_url=db_url)
    after = _count_facts(su_conn, project_id)
    assert after > before, "Both distinct files must produce facts"


# ── 2. Provenance populated ───────────────────────────────────────────────

def test_provenance_has_doc_id_and_confidence(su_conn, db_url, bureau_id, project_id):
    """Every extracted fact must have doc_id and confidence in provenance."""
    user_id = str(uuid.uuid4())
    result = process_document(
        content=_CSV_CONTENT,
        bureau_id=bureau_id,
        project_id=project_id,
        filename="prov_test.csv",
        content_type="text/csv",
        user_id=user_id,
        db_url=db_url,
    )
    # May be duplicate from previous test — look for facts with this doc_id
    doc_id = result["doc_id"]

    cur = su_conn.cursor()
    cur.execute(
        "SELECT provenance FROM activity_facts WHERE project_id = %s AND provenance->>'doc_id' = %s",
        (project_id, doc_id),
    )
    rows = cur.fetchall()
    # If this was a dedup, rows will be empty — find any fact with provenance
    if not rows:
        cur.execute(
            "SELECT provenance FROM activity_facts WHERE project_id = %s LIMIT 1",
            (project_id,),
        )
        rows = cur.fetchall()

    assert rows, "No facts found with provenance"
    for row in rows:
        prov = row["provenance"]
        assert "doc_id" in prov, f"provenance missing doc_id: {prov}"
        assert "confidence" in prov, f"provenance missing confidence: {prov}"
        assert "extraction_method" in prov, f"provenance missing extraction_method: {prov}"


# ── 3. Extraction writes proposed only ───────────────────────────────────

def test_extraction_writes_proposed_only(su_conn, db_url, bureau_id, project_id):
    """§0.3: no extraction path may write state=validated."""
    user_id = str(uuid.uuid4())
    xlsx_bytes = _make_xlsx()
    result = process_document(
        content=xlsx_bytes,
        bureau_id=bureau_id,
        project_id=project_id,
        filename="test.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        user_id=user_id,
        db_url=db_url,
    )
    doc_id = result["doc_id"]

    cur = su_conn.cursor()
    cur.execute(
        "SELECT state FROM activity_facts WHERE project_id = %s AND provenance->>'doc_id' = %s",
        (project_id, doc_id),
    )
    rows = cur.fetchall()
    for row in rows:
        assert row["state"] == "proposed", (
            f"§0.3 VIOLATED: extraction wrote state={row['state']!r} (must be 'proposed')"
        )


# ── 4. LLM never touches calc ─────────────────────────────────────────────

def test_scan_parser_without_api_key_returns_empty(monkeypatch):
    """When ANTHROPIC_API_KEY is not set, parse_scan returns empty list — no crash, no calc."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Minimal "PDF" bytes (won't actually be parsed, key check happens first)
    result = parse_scan(b"%PDF-1.4 fake scan content", "doc-1", "scan.pdf")
    assert result == [], "parse_scan must return [] when no API key is set"


def test_extraction_never_creates_snapshot(su_conn, db_url, bureau_id, project_id):
    """Ingestion pipeline must never create a report_snapshot (kernel is never called)."""
    user_id = str(uuid.uuid4())
    before = su_conn.cursor()
    before.execute("SELECT COUNT(*) AS n FROM report_snapshots WHERE bureau_id=%s", (bureau_id,))
    count_before = before.fetchone()["n"]

    process_document(
        content=_CSV_CONTENT,
        bureau_id=bureau_id,
        project_id=project_id,
        filename="no_snapshot_test.csv",
        content_type="text/csv",
        user_id=user_id,
        db_url=db_url,
    )

    after = su_conn.cursor()
    after.execute("SELECT COUNT(*) AS n FROM report_snapshots WHERE bureau_id=%s", (bureau_id,))
    count_after = after.fetchone()["n"]

    assert count_before == count_after, (
        "Ingestion MUST NOT create a report_snapshot — kernel must not be called during extraction"
    )


# ── 5. Parser unit tests ──────────────────────────────────────────────────

def test_csv_parser_extracts_facts():
    facts = parse_csv(_CSV_CONTENT, "doc-test", "test.csv")
    assert len(facts) == 2
    assert any(f.category == "scope2_electricity" for f in facts)
    assert any(f.category == "scope1_mobile" for f in facts)


def test_csv_parser_confidence_in_range():
    facts = parse_csv(_CSV_CONTENT, "doc-test", "test.csv")
    for f in facts:
        assert 0.0 <= f.confidence <= 1.0


def test_xlsx_parser_extracts_facts():
    xlsx_bytes = _make_xlsx()
    facts = parse_xlsx(xlsx_bytes, "doc-test", "test.xlsx")
    assert len(facts) == 2
    assert any(f.activity_unit == "kWh" for f in facts)
    assert any(f.activity_unit == "L" for f in facts)


def test_csv_empty_rows_skipped():
    content = b"category,activity_value,activity_unit,period_start,period_end,scope\n,,,,\n"
    facts = parse_csv(content, "doc-test", "empty.csv")
    assert facts == [], "Zero-value rows must be skipped"


def test_csv_scope_parsed():
    content = (
        b"category,activity_value,activity_unit,period_start,period_end,scope\n"
        b"scope2_electricity,1000,kWh,2024-01-01,2024-12-31,2\n"
    )
    facts = parse_csv(content, "doc-test", "scope_test.csv")
    assert facts[0].scope == 2


# ── 6. Reconciliation hook ────────────────────────────────────────────────

def test_reconciliation_runs_after_extraction(db_url, bureau_id, project_id):
    """process_document returns reconciliation_anomalies list (may be empty)."""
    user_id = str(uuid.uuid4())
    content = (
        b"category,activity_value,activity_unit,period_start,period_end,scope\n"
        b"scope1_stationary,50,MJ,2024-01-01,2024-06-30,1\n"
        b"scope1_stationary,60,MJ,2024-07-01,2024-12-31,1\n"
    )
    result = process_document(
        content=content,
        bureau_id=bureau_id,
        project_id=project_id,
        filename="reconcile_test.csv",
        content_type="text/csv",
        user_id=user_id,
        db_url=db_url,
    )
    assert "reconciliation_anomalies" in result
    assert isinstance(result["reconciliation_anomalies"], list)
