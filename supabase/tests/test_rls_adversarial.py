"""
Phase 1 adversarial acceptance tests for RLS + schema invariants.

Tests:
1. bureau_A session cannot SELECT bureau_B rows (clients, projects, activity_facts, snapshots)
2. bureau_A session cannot UPDATE bureau_B rows
3. report_snapshots: UPDATE denied
4. report_snapshots: DELETE denied
5. activity_facts: state cannot regress validated → proposed (trigger)
6. activity_facts: DELETE denied (no DELETE policy)
7. Seed data: ONEE grid factor present and correct scope2_type
"""

import os
import pathlib
import uuid
import psycopg2
import pytest
import sqlparse
import testing.postgresql

PG_BIN = pathlib.Path(r"C:\Users\Hamza\AppData\Local\pg17_portable\bin")
MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent / "migrations"
SEED_DIR = pathlib.Path(__file__).parent.parent / "seed"


@pytest.fixture(scope="session")
def pg():
    """Spin up a temporary PostgreSQL instance for the test session."""
    instance = testing.postgresql.Postgresql(
        initdb=str(PG_BIN / "initdb"),
        postgres=str(PG_BIN / "postgres"),
        initdb_args="-U postgres -A trust --encoding=UTF8 --lc-collate=C --lc-ctype=C",
    )
    yield instance
    # testing.postgresql sends SIGINT on shutdown which Windows doesn't support.
    # Use pg_ctl stop -m fast as a Windows-compatible alternative, then clear
    # the child_process reference so the library's __del__ has nothing to signal.
    import subprocess
    data_dir = instance.get_data_directory()
    subprocess.run(
        [str(PG_BIN / "pg_ctl"), "stop", "-D", data_dir, "-m", "fast", "-w"],
        capture_output=True,
    )
    instance.child_process = None  # prevent __del__ from trying SIGINT


def _connect(pg, **kwargs):
    """Open a psycopg2 connection and force UTF-8 client encoding."""
    conn = psycopg2.connect(**pg.dsn(), **kwargs)
    conn.set_client_encoding("UTF8")
    return conn


def _has_sql(stmt: str) -> bool:
    """Return True if the sqlparse statement contains actual SQL (not just comments/whitespace)."""
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
    """Execute a .sql file statement by statement using sqlparse."""
    sql = path.read_text(encoding="utf-8")
    for stmt in sqlparse.split(sql):
        stmt = stmt.strip()
        if stmt and _has_sql(stmt):
            cur.execute(stmt)


@pytest.fixture(scope="session")
def conn_superuser(pg):
    """Superuser connection — used to run migrations and seed."""
    conn = _connect(pg)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def db_ready(conn_superuser, pg):
    """Run all migrations and seed data once."""
    cur = conn_superuser.cursor()

    # Run migrations in order
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        _run_sql_file(cur, migration)

    # Run seed
    for seed_file in sorted(SEED_DIR.glob("*.sql")):
        _run_sql_file(cur, seed_file)

    # Create a non-superuser app role that RLS will actually apply to.
    # In Supabase this is the 'authenticated' role; here we call it 'app_user'.
    cur.execute("DROP ROLE IF EXISTS app_user")
    cur.execute("CREATE ROLE app_user LOGIN PASSWORD 'test'")
    cur.execute(
        """GRANT SELECT, INSERT, UPDATE, DELETE
           ON bureaus, clients, users, projects, activity_facts,
              report_snapshots, anomalies, audit_log
           TO app_user"""
    )
    cur.execute(
        "GRANT SELECT ON methodologies, factor_sets, emission_factors, conversion_factors, gwp_values TO app_user"
    )

    # Create two bureaus for adversarial tests
    bureau_a_id = str(uuid.uuid4())
    bureau_b_id = str(uuid.uuid4())

    cur.execute(
        "INSERT INTO bureaus (id, name, region) VALUES (%s, 'Bureau A', 'MA'), (%s, 'Bureau B', 'MA')",
        (bureau_a_id, bureau_b_id),
    )

    # Insert a client and project under each bureau
    client_a_id = str(uuid.uuid4())
    client_b_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO clients (id, bureau_id, name) VALUES (%s, %s, 'Client A'), (%s, %s, 'Client B')",
        (client_a_id, bureau_a_id, client_b_id, bureau_b_id),
    )

    method_id = "00000000-0000-0000-0000-000000000001"
    project_a_id = str(uuid.uuid4())
    project_b_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO projects (id, bureau_id, client_id, name, reporting_year, methodology_id)
           VALUES (%s,%s,%s,'Project A',2024,%s), (%s,%s,%s,'Project B',2024,%s)""",
        (project_a_id, bureau_a_id, client_a_id, method_id,
         project_b_id, bureau_b_id, client_b_id, method_id),
    )

    # Insert an activity_fact under bureau B
    fact_b_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO activity_facts
               (id, bureau_id, project_id, category, activity_value, activity_unit,
                period_start, period_end, scope)
           VALUES (%s,%s,%s,'scope1_mobile',100,'L','2024-01-01','2024-12-31',1)""",
        (fact_b_id, bureau_b_id, project_b_id),
    )

    # Insert a validated activity_fact under bureau A (for regression test)
    fact_a_validated_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO activity_facts
               (id, bureau_id, project_id, category, activity_value, activity_unit,
                period_start, period_end, scope, state)
           VALUES (%s,%s,%s,'scope1_stationary',500,'MJ','2024-01-01','2024-12-31',1,'validated')""",
        (fact_a_validated_id, bureau_a_id, project_a_id),
    )

    # Insert a snapshot under bureau B
    snapshot_b_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO report_snapshots
               (id, bureau_id, project_id, reporting_year, state_hash,
                totals_co2e, computation_trace, factor_set_versions, gwp_basis, uncertainty)
           VALUES (%s,%s,%s,2024,'abc123',
                   '{"scope1":100}','[]','[]','AR5','{}')""",
        (snapshot_b_id, bureau_b_id, project_b_id),
    )

    cur.close()

    return {
        "bureau_a_id": bureau_a_id,
        "bureau_b_id": bureau_b_id,
        "client_a_id": client_a_id,
        "client_b_id": client_b_id,
        "project_a_id": project_a_id,
        "project_b_id": project_b_id,
        "fact_b_id": fact_b_id,
        "fact_a_validated_id": fact_a_validated_id,
        "snapshot_b_id": snapshot_b_id,
    }


def rls_conn(pg, bureau_id: str):
    """Open a non-superuser connection scoped to bureau_id via GUC — simulates API middleware.

    RLS is bypassed for superusers, so we connect as 'app_user' (equivalent to
    Supabase's 'authenticated' role). This is exactly what the API middleware does.
    """
    dsn = dict(pg.dsn())
    dsn["user"] = "app_user"
    dsn["password"] = "test"
    conn = psycopg2.connect(**dsn)
    conn.set_client_encoding("UTF8")
    conn.autocommit = False
    cur = conn.cursor()
    # This is exactly what the API middleware does per request (§0 inv 6)
    cur.execute("SET app.bureau_id = %s", (bureau_id,))
    cur.close()
    return conn


# ────────────────────────────────────────────────────────────
# 1. Cross-tenant SELECT isolation
# ────────────────────────────────────────────────────────────

def test_bureau_a_cannot_select_bureau_b_clients(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_a_id"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM clients WHERE id = %s", (ids["client_b_id"],))
    rows = cur.fetchall()
    conn.close()
    assert rows == [], f"RLS FAIL: bureau A saw bureau B client: {rows}"


def test_bureau_a_cannot_select_bureau_b_projects(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_a_id"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM projects WHERE id = %s", (ids["project_b_id"],))
    rows = cur.fetchall()
    conn.close()
    assert rows == [], f"RLS FAIL: bureau A saw bureau B project: {rows}"


def test_bureau_a_cannot_select_bureau_b_activity_facts(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_a_id"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM activity_facts WHERE id = %s", (ids["fact_b_id"],))
    rows = cur.fetchall()
    conn.close()
    assert rows == [], f"RLS FAIL: bureau A saw bureau B activity_fact: {rows}"


def test_bureau_a_cannot_select_bureau_b_snapshots(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_a_id"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM report_snapshots WHERE id = %s", (ids["snapshot_b_id"],))
    rows = cur.fetchall()
    conn.close()
    assert rows == [], f"RLS FAIL: bureau A saw bureau B snapshot: {rows}"


# ────────────────────────────────────────────────────────────
# 2. Cross-tenant UPDATE isolation
# ────────────────────────────────────────────────────────────

def test_bureau_a_cannot_update_bureau_b_client(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_a_id"])
    cur = conn.cursor()
    cur.execute(
        "UPDATE clients SET name = 'HACKED' WHERE id = %s",
        (ids["client_b_id"],),
    )
    assert cur.rowcount == 0, "RLS FAIL: bureau A managed to UPDATE bureau B client"
    conn.rollback()
    conn.close()


def test_bureau_a_cannot_update_bureau_b_activity_fact(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_a_id"])
    cur = conn.cursor()
    cur.execute(
        "UPDATE activity_facts SET activity_value = 999 WHERE id = %s",
        (ids["fact_b_id"],),
    )
    assert cur.rowcount == 0, "RLS FAIL: bureau A managed to UPDATE bureau B activity_fact"
    conn.rollback()
    conn.close()


# ────────────────────────────────────────────────────────────
# 3. Snapshot immutability — UPDATE denied
# ────────────────────────────────────────────────────────────

def test_snapshot_update_denied_for_owning_bureau(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_b_id"])
    cur = conn.cursor()
    cur.execute(
        "UPDATE report_snapshots SET state_hash = 'tampered' WHERE id = %s",
        (ids["snapshot_b_id"],),
    )
    assert cur.rowcount == 0, "Invariant FAIL: snapshot UPDATE was allowed — must be insert-only"
    conn.rollback()
    conn.close()


# ────────────────────────────────────────────────────────────
# 4. Snapshot immutability — DELETE denied
# ────────────────────────────────────────────────────────────

def test_snapshot_delete_denied(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_b_id"])
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM report_snapshots WHERE id = %s",
        (ids["snapshot_b_id"],),
    )
    assert cur.rowcount == 0, "Invariant FAIL: snapshot DELETE was allowed — must be insert-only"
    conn.rollback()
    conn.close()


# ────────────────────────────────────────────────────────────
# 5. Activity facts: state regression blocked by trigger
# ────────────────────────────────────────────────────────────

def test_activity_fact_state_cannot_regress_from_validated(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_a_id"])
    cur = conn.cursor()
    with pytest.raises(psycopg2.errors.RaiseException):
        cur.execute(
            "UPDATE activity_facts SET state = 'proposed' WHERE id = %s",
            (ids["fact_a_validated_id"],),
        )
    conn.rollback()
    conn.close()


# ────────────────────────────────────────────────────────────
# 6. Activity facts: DELETE denied (no DELETE RLS policy)
# ────────────────────────────────────────────────────────────

def test_activity_fact_delete_denied(pg, db_ready):
    ids = db_ready
    conn = rls_conn(pg, ids["bureau_b_id"])
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM activity_facts WHERE id = %s",
        (ids["fact_b_id"],),
    )
    assert cur.rowcount == 0, "Invariant FAIL: activity_fact DELETE was allowed — must be append-only"
    conn.rollback()
    conn.close()


# ────────────────────────────────────────────────────────────
# 7. Seed data: ONEE grid factor present with correct values
# ────────────────────────────────────────────────────────────

def test_onee_grid_factor_exists(conn_superuser, db_ready):
    cur = conn_superuser.cursor()
    cur.execute(
        """SELECT value, scope, scope2_type, region
           FROM emission_factors
           WHERE sub_category = 'grid_location' AND region = 'MA'
           LIMIT 1"""
    )
    row = cur.fetchone()
    cur.close()
    assert row is not None, "Seed FAIL: ONEE grid location factor not found"
    value, scope, scope2_type, region = row
    assert float(value) == pytest.approx(0.679, rel=1e-3)
    assert scope == 2
    assert scope2_type == "location"
    assert region == "MA"


def test_ar6_gwp_co2_equals_1(conn_superuser, db_ready):
    cur = conn_superuser.cursor()
    cur.execute(
        "SELECT value FROM gwp_values WHERE gas='CO2' AND gwp_basis='AR6' AND time_horizon_years=100"
    )
    row = cur.fetchone()
    cur.close()
    assert row is not None
    assert float(row[0]) == 1.0


def test_ar5_gwp_ch4(conn_superuser, db_ready):
    cur = conn_superuser.cursor()
    cur.execute(
        "SELECT value FROM gwp_values WHERE gas='CH4' AND gwp_basis='AR5' AND time_horizon_years=100"
    )
    row = cur.fetchone()
    cur.close()
    assert row is not None
    assert float(row[0]) == 28.0


def test_effective_dating_two_factor_sets_exist(conn_superuser, db_ready):
    """FY2023 and FY2024 factor sets exist with non-overlapping effective dates."""
    cur = conn_superuser.cursor()
    cur.execute(
        """SELECT version, effective_from, effective_to
           FROM factor_sets
           WHERE methodology_id = '00000000-0000-0000-0000-000000000001'
           ORDER BY effective_from"""
    )
    rows = cur.fetchall()
    cur.close()
    assert len(rows) >= 2, "Need at least two factor sets for effective-dating test"
    # FY2023 ends before FY2024 starts
    fy2023 = next((r for r in rows if r[0] == '21.0'), None)
    fy2024 = next((r for r in rows if r[0] == '22.0'), None)
    assert fy2023 is not None
    assert fy2024 is not None
    assert fy2023[2] is not None  # FY2023 has an end date
    assert fy2023[2] < fy2024[1]  # FY2023 ends before FY2024 starts
