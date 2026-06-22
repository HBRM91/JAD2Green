-- ============================================================
-- Migration 002: Row-Level Security
-- Invariant §0.5: multi-tenancy enforced at DB via RLS.
-- Invariant §0.6: every request injects bureau_id GUC.
-- ============================================================

-- ------------------------------------------------------------
-- Helper: safe GUC accessor (returns NULL if not set, not error)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION current_bureau_id() RETURNS UUID
LANGUAGE sql STABLE SECURITY DEFINER AS $$
    SELECT NULLIF(current_setting('app.bureau_id', TRUE), '')::UUID
$$;

CREATE OR REPLACE FUNCTION current_bureau_role() RETURNS TEXT
LANGUAGE sql STABLE SECURITY DEFINER AS $$
    SELECT NULLIF(current_setting('app.role', TRUE), '')
$$;

-- ------------------------------------------------------------
-- REFERENCE TABLES: no RLS, readable by all authenticated roles
-- (methodologies, factor_sets, emission_factors, conversion_factors, gwp_values)
-- Writes only via service role (migrations/seed).
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- BUREAUS: each bureau row is its own tenant root.
-- A session may only see/touch its own bureau row.
-- ------------------------------------------------------------
ALTER TABLE bureaus ENABLE ROW LEVEL SECURITY;

CREATE POLICY bureaus_select ON bureaus
    FOR SELECT USING (id = current_bureau_id());

CREATE POLICY bureaus_update ON bureaus
    FOR UPDATE USING (id = current_bureau_id())
    WITH CHECK (id = current_bureau_id());

-- INSERT and DELETE via service role only (onboarding flow, admin).
-- No policy = denied for normal roles.

-- ------------------------------------------------------------
-- CLIENTS
-- ------------------------------------------------------------
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY clients_all ON clients
    USING (bureau_id = current_bureau_id())
    WITH CHECK (bureau_id = current_bureau_id());

-- ------------------------------------------------------------
-- USERS (consultant profile table)
-- ------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_all ON users
    USING (bureau_id = current_bureau_id())
    WITH CHECK (bureau_id = current_bureau_id());

-- ------------------------------------------------------------
-- PROJECTS
-- ------------------------------------------------------------
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY projects_all ON projects
    USING (bureau_id = current_bureau_id())
    WITH CHECK (bureau_id = current_bureau_id());

-- ------------------------------------------------------------
-- ACTIVITY FACTS (append-only; no DELETE policy)
-- UPDATE is allowed (state transition proposed→validated),
-- but the trigger prevents regression and the API enforces the
-- human-only constraint for validated writes.
-- ------------------------------------------------------------
ALTER TABLE activity_facts ENABLE ROW LEVEL SECURITY;

CREATE POLICY activity_facts_select ON activity_facts
    FOR SELECT USING (bureau_id = current_bureau_id());

CREATE POLICY activity_facts_insert ON activity_facts
    FOR INSERT WITH CHECK (bureau_id = current_bureau_id());

CREATE POLICY activity_facts_update ON activity_facts
    FOR UPDATE
    USING (bureau_id = current_bureau_id())
    WITH CHECK (bureau_id = current_bureau_id());

-- No DELETE policy → DELETE always denied at RLS level.

-- ------------------------------------------------------------
-- REPORT SNAPSHOTS (insert-only — no UPDATE, no DELETE)
-- Invariant §0.10: immutable once written.
-- ------------------------------------------------------------
ALTER TABLE report_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY snapshots_select ON report_snapshots
    FOR SELECT USING (bureau_id = current_bureau_id());

CREATE POLICY snapshots_insert ON report_snapshots
    FOR INSERT WITH CHECK (bureau_id = current_bureau_id());

-- No UPDATE or DELETE policies → both always denied.

-- ------------------------------------------------------------
-- ANOMALIES
-- ------------------------------------------------------------
ALTER TABLE anomalies ENABLE ROW LEVEL SECURITY;

CREATE POLICY anomalies_select ON anomalies
    FOR SELECT USING (bureau_id = current_bureau_id());

CREATE POLICY anomalies_insert ON anomalies
    FOR INSERT WITH CHECK (bureau_id = current_bureau_id());

CREATE POLICY anomalies_update ON anomalies
    FOR UPDATE
    USING (bureau_id = current_bureau_id())
    WITH CHECK (bureau_id = current_bureau_id());

-- ------------------------------------------------------------
-- AUDIT LOG (append-only, no UPDATE/DELETE)
-- ------------------------------------------------------------
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_log_select ON audit_log
    FOR SELECT USING (bureau_id = current_bureau_id());

CREATE POLICY audit_log_insert ON audit_log
    FOR INSERT WITH CHECK (bureau_id = current_bureau_id());

-- No UPDATE or DELETE policies.
