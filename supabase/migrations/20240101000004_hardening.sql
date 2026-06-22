-- ============================================================
-- Migration 004: Hardening (Phase 7)
-- - Encrypted Google refresh token storage at rest
-- - Immutable guard triggers on report_snapshots (belt-and-suspenders)
-- - Audit log triggers: extraction events + validated→snapshot transitions
-- - Region pinning: bureau region check function
-- ============================================================

-- ------------------------------------------------------------
-- 1. Encrypted Google refresh token storage (§0.11)
-- Token never leaves region; stored encrypted via pgcrypto.
-- Encryption key from GUC app.token_encrypt_key (injected by API layer).
-- ------------------------------------------------------------
ALTER TABLE bureaus
    ADD COLUMN IF NOT EXISTS google_refresh_token_enc BYTEA,
    ADD COLUMN IF NOT EXISTS region_locked_at TIMESTAMPTZ;

CREATE OR REPLACE FUNCTION store_google_refresh_token(
    p_bureau_id UUID,
    p_token TEXT,
    p_key TEXT
) RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE bureaus
    SET google_refresh_token_enc = pgp_sym_encrypt(p_token, p_key)
    WHERE id = p_bureau_id AND id = current_bureau_id();

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Bureau not found or cross-tenant access denied';
    END IF;
END;
$$;

-- Retrieve (decrypt) — only within same bureau session
CREATE OR REPLACE FUNCTION get_google_refresh_token(
    p_bureau_id UUID,
    p_key TEXT
) RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_enc BYTEA;
BEGIN
    SELECT google_refresh_token_enc INTO v_enc
    FROM bureaus
    WHERE id = p_bureau_id AND id = current_bureau_id();

    IF NOT FOUND OR v_enc IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN pgp_sym_decrypt(v_enc, p_key);
END;
$$;

-- ------------------------------------------------------------
-- 2. Belt-and-suspenders: DENY UPDATE/DELETE on report_snapshots
-- (RLS already denies; this trigger fires even for service role)
-- §0.10: immutable once written.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION report_snapshots_immutable_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'report_snapshots: rows are immutable (§0 inv 10). Operation: UPDATE on id=%', OLD.id;
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'report_snapshots: rows are immutable (§0 inv 10). Operation: DELETE on id=%', OLD.id;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_snapshots_immutable_update ON report_snapshots;
CREATE TRIGGER trg_snapshots_immutable_update
    BEFORE UPDATE ON report_snapshots
    FOR EACH ROW EXECUTE FUNCTION report_snapshots_immutable_guard();

DROP TRIGGER IF EXISTS trg_snapshots_immutable_delete ON report_snapshots;
CREATE TRIGGER trg_snapshots_immutable_delete
    BEFORE DELETE ON report_snapshots
    FOR EACH ROW EXECUTE FUNCTION report_snapshots_immutable_guard();

-- ------------------------------------------------------------
-- 3. Audit trigger: log every activity_facts state transition
-- Fires on UPDATE; records who validated and when.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit_activity_fact_transition()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Only log state transitions
    IF OLD.state IS DISTINCT FROM NEW.state THEN
        INSERT INTO audit_log (
            bureau_id, user_id, action, entity_type, entity_id,
            before_state, after_state, metadata
        ) VALUES (
            NEW.bureau_id,
            NEW.validated_by,
            'VALIDATE',
            'activity_fact',
            NEW.id,
            jsonb_build_object('state', OLD.state),
            jsonb_build_object('state', NEW.state, 'validated_by', NEW.validated_by, 'validated_at', NEW.validated_at),
            jsonb_build_object('project_id', NEW.project_id, 'category', NEW.category)
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_activity_fact ON activity_facts;
CREATE TRIGGER trg_audit_activity_fact
    AFTER UPDATE ON activity_facts
    FOR EACH ROW EXECUTE FUNCTION audit_activity_fact_transition();

-- ------------------------------------------------------------
-- 4. Audit trigger: log every report_snapshots insert (compute event)
-- Captures factor_set_versions and gwp_basis for traceability.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit_snapshot_insert()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit_log (
        bureau_id, user_id, action, entity_type, entity_id,
        after_state, metadata
    ) VALUES (
        NEW.bureau_id,
        NEW.generated_by,
        'COMPUTE',
        'report_snapshot',
        NEW.id,
        jsonb_build_object(
            'state_hash', NEW.state_hash,
            'reporting_year', NEW.reporting_year,
            'gwp_basis', NEW.gwp_basis,
            'factor_set_versions', NEW.factor_set_versions
        ),
        jsonb_build_object('project_id', NEW.project_id)
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_snapshot ON report_snapshots;
CREATE TRIGGER trg_audit_snapshot
    AFTER INSERT ON report_snapshots
    FOR EACH ROW EXECUTE FUNCTION audit_snapshot_insert();

-- ------------------------------------------------------------
-- 5. Add missing columns to documents for audit + provenance
-- ------------------------------------------------------------
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS original_filename TEXT,
    ADD COLUMN IF NOT EXISTS uploaded_by UUID,
    ADD COLUMN IF NOT EXISTS extraction_confidence NUMERIC(5,4);

-- Audit trigger: log document extraction events when processing completes.
-- Confidence stored per §0 (every extraction event must include confidence).
CREATE OR REPLACE FUNCTION audit_document_extraction()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit_log (
        bureau_id, user_id, action, entity_type, entity_id,
        after_state, confidence, metadata
    ) VALUES (
        NEW.bureau_id,
        NEW.uploaded_by,
        'EXTRACT',
        'document',
        NEW.id,
        jsonb_build_object(
            'processing_status', NEW.processing_status,
            'extraction_method', NEW.extraction_method
        ),
        NEW.extraction_confidence,
        jsonb_build_object(
            'project_id', NEW.project_id,
            'filename', COALESCE(NEW.original_filename, NEW.filename)
        )
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_document ON documents;
CREATE TRIGGER trg_audit_document
    AFTER UPDATE OF processing_status ON documents
    FOR EACH ROW
    WHEN (NEW.processing_status IN ('done', 'error'))
    EXECUTE FUNCTION audit_document_extraction();

-- ------------------------------------------------------------
-- 6. Region lock function: called at onboarding to pin bureau region.
-- Once set, region cannot be changed.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION lock_bureau_region(p_bureau_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE bureaus
    SET region_locked_at = NOW()
    WHERE id = p_bureau_id
      AND id = current_bureau_id()
      AND region_locked_at IS NULL;
END;
$$;

-- Prevent region from changing once locked
CREATE OR REPLACE FUNCTION bureaus_region_immutable_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.region_locked_at IS NOT NULL AND OLD.region != NEW.region THEN
        RAISE EXCEPTION 'bureaus: region is locked for bureau_id=%. Cannot change from % to %.',
            OLD.id, OLD.region, NEW.region;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bureaus_region_guard ON bureaus;
CREATE TRIGGER trg_bureaus_region_guard
    BEFORE UPDATE ON bureaus
    FOR EACH ROW EXECUTE FUNCTION bureaus_region_immutable_guard();
