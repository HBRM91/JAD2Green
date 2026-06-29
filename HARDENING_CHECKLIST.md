# Hardening checklist — verify before going live

Cross-references each `SECURITY.md` and `CLAUDE.md §0` invariant with the
code/config location that enforces it. Run through this **once** after
the first deploy and again after any major version bump.

## Authentication & JWT
- [ ] `SUPABASE_JWT_SECRET` is ≥32 chars, not a known-weak default
  → enforced at api startup by `config.py:model_post_init` (refuses to boot otherwise)
- [ ] JWT audience is `authenticated` (matches Supabase)
  → `apps/api/src/adrar_api/deps.py:get_tenant`
- [ ] `SECRET_KEY` ≥32 chars
  → same `config.py` check
- [ ] `TOKEN_ENCRYPT_KEY` ≥32 chars (for pgp_sym_encrypt of Google tokens at rest)
  → `apps/api/src/adrar_api/services/google_tokens.py`

## Multi-tenancy (RLS)
- [ ] `app.bureau_id` GUC injected per request from JWT
  → `apps/api/src/adrar_api/deps.py`
- [ ] RLS enabled on every tenant table
  → `supabase/migrations/20240101000002_rls.sql` and
    `20240101000004_hardening.sql`
- [ ] Cross-tenant read attempt returns empty
  → `apps/api/tests/test_hardening.py::TestCrossTenantSnapshots`
- [ ] Cross-tenant write attempt returns 404/403
  → `apps/api/tests/test_api.py::TestReadEndpoints::test_*_cross_tenant`

## No-finalize invariant (§0.4)
- [ ] No `POST /projects/{id}/finalize` (or `approve`, `submit`, `final`)
  → `apps/api/tests/test_hardening.py::TestNoFinalizeHardening`
- [ ] API startup scans routes for forbidden segments
  → same test class

## Effective-dating (§0.7)
- [ ] FY2024 uses factor set valid for FY2024, not "latest"
  → `apps/api/src/adrar_api/services/compute_svc.py:select_factor_set`
  → `apps/api/tests/test_hardening.py::TestEffectiveDating`
- [ ] FY2023 and FY2024 select different factor sets when both seeded

## Dual Scope 2 (§0.8)
- [ ] Snapshot persists both `scope2_location` and `scope2_market` totals
  → `packages/kernel/src/adrar_kernel/calc.py:compute_emissions`

## Uncertainty separation (§0.2)
- [ ] `totals_co2e` does NOT include `(1 + uncertainty)` factor
  → `apps/api/tests/test_hardening.py::TestUncertaintySeparation`

## Conversion-as-data (§0.9)
- [ ] Editing a `conversion_factors` coefficient changes the result
  → `packages/kernel/tests/test_kernel.py::test_conversion_as_data`

## Snapshot immutability (§0.10)
- [ ] `report_snapshots` rejects UPDATE and DELETE
  → DB trigger in `20240101000004_hardening.sql`
  → `apps/api/tests/test_hardening.py::TestSnapshotImmutability`

## Reproducibility (§0.1)
- [ ] Same inputs → identical totals + identical `state_hash`
  → `packages/kernel/tests/test_kernel.py`
  → `apps/api/tests/test_api.py::TestComputeInvariant::test_compute_deterministic`

## Residency (§0.11)
- [ ] All raw documents stay in Supabase Storage (region = tenant region)
  → `apps/api/src/adrar_api/routers/documents.py` upload handler
- [ ] API to LLM/OCR provider is logged in `audit_log` with provider + cost
  → TODO Phase 2 (currently NOT writing — must be done before go-live)
- [ ] No raw document or fact data sent to Google on export
  → `apps/api/src/adrar_api/routers/reports.py:export_to_google_docs`
    sends the DOCX bytes + AI disclosure only
- [ ] Google Drive export is **off by default** in the UI
  → `apps/web/src/app/projects/[id]/page.tsx` export toggle

## AI transparency (§0.12)
- [ ] Every generated DOCX report contains the AI disclosure block
  → `apps/worker/src/adrar_worker/report/narrative.py:DISCLOSURE_BLOCK`
  → `apps/worker/src/adrar_worker/report/renderer.py` injects it

## Rate limiting + body limits
- [ ] slowapi is active on every router
  → `apps/api/src/adrar_api/main.py` (`app.state.limiter`)
- [ ] Body size limit ≤ 25 MB on `/documents` upload
  → `apps/api/src/adrar_api/main.py` (request size middleware)
  → Caddyfile: `request_body { max_size 25MB }`
- [ ] CORS allowlist matches the production frontend origin
  → `apps/api/src/adrar_api/main.py` (`_raw_origins`)

## Headers
- [ ] HSTS, X-Content-Type-Options, X-Frame-Options set on api + web
  → Caddyfile header blocks
- [ ] CSP on web (Next.js) restricts scripts to self + Supabase origin
  → Caddyfile web header block
- [ ] `Server` header stripped
  → Caddyfile `-Server`

## TLS
- [ ] Let's Encrypt cert obtained and auto-renewing
  → Caddy ACME HTTP-01 challenge (needs port 80 reachable)
- [ ] HSTS preload eligible (max-age 2 years, includeSubDomains, preload)
  → Caddyfile header

## Network
- [ ] UFW allows 22, 80, 443 only
  → `scripts/setup-hetzner.sh` step 5
- [ ] Postgres not exposed on public internet (use Supabase direct connection)
  → DATABASE_URL uses Supabase host
- [ ] Redis not exposed on public internet
  → `docker-compose.prod.yml` removes the redis port binding

## Observability (TODO Phase 7)
- [ ] Sentry SDK wired into api + worker + web
- [ ] structlog JSON logging
- [ ] `/health` returns DB + Redis + Celery worker count
- [ ] Frontend `app/error.tsx` → Sentry

## Backups
- [ ] First backup verified (size > 0, decryptable)
  → `scripts/backup.sh` run manually
- [ ] Restored backup row counts match live DB (±transaction drift)
  → `scripts/restore.sh` against a throwaway project
- [ ] Quarterly DR drill scheduled (calendar reminder)

## Provider DPAs (legal)
- [ ] Aliyun DashScope — DPA in place before any production OCR call carrying personal data
- [ ] OpenRouter — DPA in place before any production extraction/narrative call
- [ ] Google (Gemini) — DPA in place if `GEMINI_API_KEY` set
- [ ] Google Drive export — opt-in only, default OFF
