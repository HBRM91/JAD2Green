-- ============================================================
-- Migration 001: Full schema for Adrar AI
-- All tables created here; RLS in 002; seed in 003.
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- REFERENCE TABLES (global, not tenant-scoped)
-- ------------------------------------------------------------

CREATE TABLE methodologies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    version         TEXT NOT NULL,
    region          TEXT,                     -- NULL means globally applicable
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name, version)
);

CREATE TABLE factor_sets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    methodology_id  UUID NOT NULL REFERENCES methodologies(id),
    name            TEXT NOT NULL,
    version         TEXT NOT NULL,
    effective_from  DATE NOT NULL,
    effective_to    DATE,                     -- NULL means still valid
    gwp_basis       TEXT NOT NULL CHECK (gwp_basis IN ('AR4','AR5','AR6')),
    region          TEXT,
    source_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- A methodology+version+region is unique per effective period
    UNIQUE (methodology_id, version, region, effective_from)
);

CREATE TABLE emission_factors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factor_set_id   UUID NOT NULL REFERENCES factor_sets(id),
    category        TEXT NOT NULL,            -- e.g. scope1_stationary, scope2_electricity
    sub_category    TEXT,
    gas             TEXT NOT NULL,            -- CO2, CH4, N2O, CO2e
    value           NUMERIC(20,10) NOT NULL,
    unit            TEXT NOT NULL,            -- e.g. kgCO2e/kWh
    activity_unit   TEXT NOT NULL,            -- e.g. kWh
    scope           INTEGER NOT NULL CHECK (scope IN (1,2,3)),
    scope2_type     TEXT CHECK (scope2_type IN ('location','market')),
    region          TEXT,
    source          TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unit conversion graph (basis: NCV, density, oxidation, direct)
-- Each row is a directed edge: from_unit → to_unit with a coefficient.
-- The resolver does multi-hop traversal.
CREATE TABLE conversion_factors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_unit       TEXT NOT NULL,
    to_unit         TEXT NOT NULL,
    coefficient     NUMERIC(20,10) NOT NULL,
    conversion_type TEXT NOT NULL CHECK (conversion_type IN ('NCV','density','oxidation','direct')),
    fuel_type       TEXT,                     -- e.g. 'diesel', 'natural_gas'; NULL = applies to all
    source          TEXT,
    effective_from  DATE NOT NULL,
    effective_to    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (from_unit, to_unit, fuel_type, effective_from)
);

-- GWP values by gas and AR basis (100-year time horizon by default)
CREATE TABLE gwp_values (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gas                 TEXT NOT NULL,
    gwp_basis           TEXT NOT NULL CHECK (gwp_basis IN ('AR4','AR5','AR6')),
    value               NUMERIC(10,4) NOT NULL,
    time_horizon_years  INTEGER NOT NULL DEFAULT 100,
    source              TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (gas, gwp_basis, time_horizon_years)
);

-- ------------------------------------------------------------
-- TENANT ROOT
-- ------------------------------------------------------------

CREATE TABLE bureaus (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    TEXT NOT NULL,
    region                  TEXT NOT NULL CHECK (region IN ('MA','EU')),
    google_export_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- TENANT TABLES (all carry bureau_id)
-- ------------------------------------------------------------

CREATE TABLE clients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id   UUID NOT NULL REFERENCES bureaus(id),
    name        TEXT NOT NULL,
    sector      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User profiles (Supabase Auth manages auth.users; this extends it with tenant/role)
CREATE TABLE users (
    id          UUID PRIMARY KEY,            -- mirrors auth.users.id
    bureau_id   UUID NOT NULL REFERENCES bureaus(id),
    role        TEXT NOT NULL CHECK (role IN ('admin','consultant','reviewer')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id       UUID NOT NULL REFERENCES bureaus(id),
    client_id       UUID NOT NULL REFERENCES clients(id),
    name            TEXT NOT NULL,
    reporting_year  INTEGER NOT NULL,
    methodology_id  UUID NOT NULL REFERENCES methodologies(id),
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','completed','archived')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- ACTIVITY FACTS (append-only; state: proposed → validated)
-- ------------------------------------------------------------

CREATE TABLE activity_facts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id       UUID NOT NULL REFERENCES bureaus(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    -- supersedes_id enables corrections: the new row supersedes the old one
    supersedes_id   UUID REFERENCES activity_facts(id),
    category        TEXT NOT NULL,
    sub_category    TEXT,
    description     TEXT,
    activity_value  NUMERIC(20,6) NOT NULL,
    activity_unit   TEXT NOT NULL,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    scope           INTEGER NOT NULL CHECK (scope IN (1,2,3)),
    scope2_type     TEXT CHECK (scope2_type IN ('location','market')),
    -- state: proposed = written by extraction/API; validated = human-only (UI trust boundary)
    state           TEXT NOT NULL DEFAULT 'proposed'
                    CHECK (state IN ('proposed','validated')),
    provenance      JSONB NOT NULL DEFAULT '{}',
    validated_by    UUID,                     -- auth.users.id; set only by UI flow
    validated_at    TIMESTAMPTZ,
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT period_order CHECK (period_end >= period_start)
);

-- Prevent state from ever going backwards (validated → proposed)
CREATE OR REPLACE FUNCTION activity_facts_state_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.state = 'validated' AND NEW.state != 'validated' THEN
        RAISE EXCEPTION 'activity_facts: state cannot regress from validated (id=%)', OLD.id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_activity_facts_state_guard
    BEFORE UPDATE ON activity_facts
    FOR EACH ROW EXECUTE FUNCTION activity_facts_state_guard();

-- ------------------------------------------------------------
-- REPORT SNAPSHOTS (immutable — INSERT only; no UPDATE/DELETE)
-- ------------------------------------------------------------

CREATE TABLE report_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id           UUID NOT NULL REFERENCES bureaus(id),
    project_id          UUID NOT NULL REFERENCES projects(id),
    reporting_year      INTEGER NOT NULL,
    state_hash          TEXT NOT NULL,
    -- totals carry NO uncertainty — uncertainty is separate (§0 inv 2)
    totals_co2e         JSONB NOT NULL,
    scope2_location_t   NUMERIC(20,6),
    scope2_market_t     NUMERIC(20,6),
    computation_trace   JSONB NOT NULL,       -- every multiplication, factor id, source, version
    factor_set_versions JSONB NOT NULL,
    gwp_basis           TEXT NOT NULL,
    uncertainty         JSONB NOT NULL,       -- separate from totals
    reconciliation      JSONB NOT NULL DEFAULT '{}',
    generated_by        UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- ANOMALIES
-- ------------------------------------------------------------

CREATE TABLE anomalies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id           UUID NOT NULL REFERENCES bureaus(id),
    project_id          UUID NOT NULL REFERENCES projects(id),
    activity_fact_id    UUID REFERENCES activity_facts(id),
    anomaly_type        TEXT NOT NULL,
    severity            TEXT NOT NULL CHECK (severity IN ('info','warning','error')),
    description         TEXT NOT NULL,
    resolved            BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_by         UUID,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- AUDIT LOG
-- ------------------------------------------------------------

CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id       UUID NOT NULL REFERENCES bureaus(id),
    user_id         UUID,
    action          TEXT NOT NULL,            -- e.g. EXTRACT, VALIDATE, COMPUTE, EXPORT
    entity_type     TEXT NOT NULL,
    entity_id       UUID,
    before_state    JSONB,
    after_state     JSONB,
    confidence      NUMERIC(5,4),             -- populated for extraction events
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------

CREATE INDEX idx_clients_bureau         ON clients(bureau_id);
CREATE INDEX idx_users_bureau           ON users(bureau_id);
CREATE INDEX idx_projects_bureau        ON projects(bureau_id);
CREATE INDEX idx_projects_client        ON projects(client_id);
CREATE INDEX idx_activity_facts_bureau  ON activity_facts(bureau_id);
CREATE INDEX idx_activity_facts_project ON activity_facts(project_id);
CREATE INDEX idx_activity_facts_state   ON activity_facts(state);
CREATE INDEX idx_snapshots_bureau       ON report_snapshots(bureau_id);
CREATE INDEX idx_snapshots_project      ON report_snapshots(project_id);
CREATE INDEX idx_anomalies_bureau       ON anomalies(bureau_id);
CREATE INDEX idx_audit_bureau           ON audit_log(bureau_id);
CREATE INDEX idx_factor_sets_eff        ON factor_sets(effective_from, effective_to);
CREATE INDEX idx_conv_factors_edge      ON conversion_factors(from_unit, to_unit);
