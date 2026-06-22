"""
Shared fixtures for Phase 3 API tests.

Uses the same portable PostgreSQL pattern as Phase 1 RLS tests.
Overrides the get_db dependency to inject test connections with GUC already set.
"""

from __future__ import annotations

import os
import pathlib
import uuid
from collections.abc import Generator
from typing import Annotated

# Prevent startup secret-strength check from failing in test environment
os.environ.setdefault("ADRAR_TESTING", "1")

import psycopg2
import psycopg2.extras
import pytest
import sqlparse
import testing.postgresql
from adrar_api.config import settings
from adrar_api.deps import TenantContext, get_db, get_tenant
from adrar_api.main import app
from fastapi import Depends
from fastapi.testclient import TestClient
from jose import jwt

PG_BIN = pathlib.Path(r"C:\Users\Hamza\AppData\Local\pg17_portable\bin")
MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "supabase" / "migrations"
SEED_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "supabase" / "seed"

_TEST_JWT_SECRET = "test-secret-for-api-tests"


def _make_jwt(bureau_id: str, role: str = "consultant", user_id: str | None = None) -> str:
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "bureau_id": bureau_id,
        "adrar_role": role,
        "aud": "authenticated",
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


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
def db_ready(su_conn, pg):
    """Run migrations + seed + create app_user role once per session."""
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
              report_snapshots, anomalies, audit_log TO app_user"""
    )
    cur.execute(
        "GRANT SELECT ON methodologies, factor_sets, emission_factors, "
        "conversion_factors, gwp_values TO app_user"
    )
    cur.close()
    return pg


@pytest.fixture(scope="session")
def bureau_a_id(su_conn, db_ready) -> str:
    bid = str(uuid.uuid4())
    su_conn.cursor().execute(
        "INSERT INTO bureaus (id, name, region) VALUES (%s, 'Bureau A', 'MA')", (bid,)
    )
    return bid


@pytest.fixture(scope="session")
def bureau_b_id(su_conn, db_ready) -> str:
    bid = str(uuid.uuid4())
    su_conn.cursor().execute(
        "INSERT INTO bureaus (id, name, region) VALUES (%s, 'Bureau B', 'MA')", (bid,)
    )
    return bid


def make_client(pg, bureau_id: str, db_url: str) -> TestClient:
    """
    Return a TestClient for bureau_id.
    Overrides: settings.database_url → test DB, settings.supabase_jwt_secret → test secret.
    """
    # Patch settings used by deps.py
    settings.database_url = db_url
    settings.supabase_jwt_secret = _TEST_JWT_SECRET

    token = _make_jwt(bureau_id)

    # Override get_db to connect as app_user (non-superuser) for RLS to apply.
    # Must use Depends(get_tenant) so FastAPI injects TenantContext from JWT,
    # not from the request body.
    def _get_test_db(
        tenant: Annotated[TenantContext, Depends(get_tenant)],
    ) -> Generator:
        dsn = pg.dsn()
        conn = psycopg2.connect(
            host=dsn["host"],
            port=dsn["port"],
            dbname=dsn["database"],
            user="app_user",
            password="test",
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        conn.set_client_encoding("UTF8")
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.bureau_id = %s", (tenant.bureau_id,))
                cur.execute("SET LOCAL app.role = %s", (tenant.role,))
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    app.dependency_overrides[get_db] = _get_test_db

    client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture(scope="session")
def client_a(pg, bureau_a_id, db_url, db_ready) -> TestClient:
    return make_client(pg, bureau_a_id, db_url)


@pytest.fixture(scope="session")
def client_b(pg, bureau_b_id, db_url, db_ready) -> TestClient:
    return make_client(pg, bureau_b_id, db_url)
