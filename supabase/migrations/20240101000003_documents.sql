-- Migration 003: documents table for upload tracking + dedup
-- Dedup invariant: UNIQUE (bureau_id, content_hash) prevents double-counting on re-upload.

CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id           UUID NOT NULL REFERENCES bureaus(id),
    project_id          UUID NOT NULL REFERENCES projects(id),
    filename            TEXT NOT NULL,
    content_hash        TEXT NOT NULL,       -- SHA-256 hex; dedup key
    content_type        TEXT NOT NULL,
    file_size_bytes     BIGINT,
    extraction_method   TEXT,                -- xlsx | csv | pdf | scan_haiku
    processing_status   TEXT NOT NULL DEFAULT 'pending'
                        CHECK (processing_status IN ('pending','processing','done','error')),
    processing_error    TEXT,
    extraction_count    INTEGER NOT NULL DEFAULT 0,
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Idempotency: same file uploaded again to same bureau is a no-op (§0: no double-count)
    UNIQUE (bureau_id, content_hash)
);

CREATE INDEX idx_documents_bureau    ON documents(bureau_id);
CREATE INDEX idx_documents_project   ON documents(project_id);
CREATE INDEX idx_documents_status    ON documents(processing_status);

-- RLS: same bureau_id pattern as all tenant tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_select ON documents
    FOR SELECT USING (bureau_id = current_bureau_id());

CREATE POLICY documents_insert ON documents
    FOR INSERT WITH CHECK (bureau_id = current_bureau_id());

CREATE POLICY documents_update ON documents
    FOR UPDATE
    USING (bureau_id = current_bureau_id())
    WITH CHECK (bureau_id = current_bureau_id());
