# AUDIT.md — JAD2Green-1 / Adrar AI A–Z MVP-Readiness Audit

**Audit date:** 2026-06-29
**Audited tree:** `C:\GITHUB\JAD2Green-1`
**Local branch:** `master` (clean checkout is at 1accdf3; current working tree has uncommitted Phase 6 WIP)
**Note on remote:** `origin/master` (and feature branches like `claude/friendly-gates-m8zhxm`) contain a substantially more advanced state — Phases 6 and 7 are essentially done there, with `SECURITY.md`, Docker Compose, rate limiting (slowapi), multi-provider LLM cascade, JAD2 brand UI, Morocco GRI 305 / NDC / AMEE features, AR language, etc. This audit is for the local working tree as instructed.

---

## A) Foreign AI / OCR providers inventory

The local working tree has **two runtime call sites** for foreign AI providers and **two aspirational/legacy references** in config and docs.

### A.1 — Anthropic Claude Haiku 4.5: scan extraction
- **File:** `apps/worker/src/adrar_worker/parsers/scan_parser.py:23,80-117`
- **Code:** `import anthropic; client = anthropic.Anthropic(...); client.messages.create(model=_HAIKU_MODEL, ...)`
- **What it does:** Sends the raw PDF (base64) to Anthropic's API for OCR+structured extraction on messy multilingual scans. Returns proposed facts.
- **Cost:** Claude Haiku 4.5 is ~$1 / 1M input tokens, $5 / 1M output. A 10-page scanned PDF ≈ 50K input tokens → ~$0.05 per scan + output (~$0.10–$0.30 typical). At 1000 docs/month that is ≈ $100–$300/month.
- **Latency:** 5–20 s per document.
- **Data residency:** Outbound to Anthropic (US-hosted; cross-border transfer from MA/EU regions — §0.11 violation risk).
- **Replacement (per locked decision in TODOLIST.md):** PaddleOCR-VL-1.5 via Aliyun DashScope (multilingual FR/AR), then Qwen3-Plus for structured extraction.

### A.2 — Anthropic Claude Haiku 4.5: report narrative
- **File:** `apps/worker/src/adrar_worker/report/narrative.py:18,77-120`
- **Code:** `import anthropic; client = anthropic.Anthropic(api_key=api_key); response = client.messages.create(model=_MODEL, ...)`
- **What it does:** Generates the French-language executive summary, key findings, and recommendations paragraphs for the Bilan Carbone report from snapshot aggregate totals (no raw facts). Runs once per report.
- **Cost:** ~$0.001–$0.005 per report at max_tokens=1024. At 100 reports/month = $0.10–$0.50/month. **Not a material cost.**
- **Latency:** 3–8 s per report.
- **Data residency:** Only aggregate totals are sent, so §0.11 risk is low. Still, cross-border to Anthropic.
- **Replacement:** DeepSeek V3 via OpenRouter (primary) → Qwen3-Plus → GLM-4-Plus cascade.

### A.3 — Azure Document Intelligence (declared, never called)
- **File:** `.env.example:13-14`
- **Code:** `AZURE_FORM_RECOGNIZER_ENDPOINT=` / `AZURE_FORM_RECOGNIZER_KEY=`
- **What it does:** **Nothing in the current code.** The variables are declared in `.env.example` (and only there) — they are referenced once in `CLAUDE.md:53` as a routing option for messy scans, but `pdf_parser.py` (the clean-PDF path) and `scan_parser.py` (the messy-scan path) never call Azure. The current code only uses `pdfplumber` for text-extractable PDFs and falls back to Haiku for scans.
- **Cost:** If added: $1.50/1000 pages prebuilt-layout, $3.00/1000 custom.
- **Recommendation:** **Remove entirely.** The variable is dead. The current scan routing already goes to Haiku; the clean-PDF path uses `pdfplumber` (open-source, free, in-process). Replace this with the Chinese OCR replacement proposed in A.1.

### A.4 — Tesseract OCR (declared, never called)
- **File:** `CLAUDE.md:52` (text only: "Tesseract; Azure Doc Intelligence or Claude Haiku ONLY for messy multilingual scans")
- **What it does:** **Nothing.** Tesseract is mentioned in the stack list but no Python code imports it.
- **Cost:** Free if used.
- **Recommendation:** **Remove from CLAUDE.md** or replace with the chosen Chinese OCR. Tesseract has poor accuracy on French/Arabic mixed text — it would be wrong to introduce it now.

### A.5 — Google Document AI / AWS Textract (not present, not used)
- Searched: no matches anywhere in the codebase. Nothing to migrate.

### A.6 — Foreign LLM in CI/automation (not a runtime concern)
- **File:** `.github/workflows/adrar-build.yml:43,65,68` and `HANDOVER.md:107,110`
- **What it does:** The GitHub Action uses `@anthropic-ai/claude-code` to drive development sessions. This is **dev infrastructure, not a runtime dependency** — it does not affect the deployed app.
- **Recommendation:** **Keep as-is** for the dev loop. If you want to cut costs on the dev loop, you could swap to Qwen-Coder or DeepSeek-Coder via the Anthropic-compatible API, but that is orthogonal to the runtime cost of the deployed app.

### A.7 — Summary cost table (monthly estimate at 1000 docs + 100 reports)

| Path | Current (Anthropic) | Recommended (Chinese) | Saving |
|---|---|---|---|
| Scan extraction | $100–$300 | $5–$20 (PaddleOCR self-host) | 80–95% |
| Report narrative | $0.10–$0.50 | $0.02–$0.10 (DeepSeek V3) | 80% |
| Azure Form Recognizer (unused) | $0 | $0 (remove) | n/a |
| Tesseract (unused) | $0 | $0 (remove) | n/a |
| **Total runtime AI cost** | **$100–$300/mo** | **$5–$20/mo** | **~90%** |

The 1–2 week engineering investment to swap pays back in <2 months for a bureau processing >100 scans/month.

### A.8 — Data residency & GDPR caveats (resolved in locked decision)
- §0.11 was a max-safety posture that conflicts with practical MA market use. The user has decided: managed-API providers are acceptable for raw scans (DPAs + audit_log non-repudiation); only the consultant-reviewed aggregate DOCX is exportable to Google Docs (opt-in, default OFF).
- This unblocks the use of Aliyun DashScope (PaddleOCR-VL-1.5), OpenRouter (Qwen3-Plus, DeepSeek V3, GLM-4-Plus), and Google Gemini Flash if needed. All calls must be logged to `audit_log`.

---

## B) Locked-invariants compliance (§0)

A walkthrough of the 12 invariants against the current code.

| # | Invariant | Status | Evidence |
|---|---|---|---|
| §0.1 | Kernel is pure & deterministic | **PASS** | `packages/kernel/src/adrar_kernel/calc.py:1-10` declares no-network, no-LLM, no-I/O. `compute_emissions` takes plain dataclasses. |
| §0.2 | `emissions = activity × factor × gwp`; uncertainty separate | **PASS** | `calc.py:101`: `emissions = converted_value * factor.value * gwp`. Uncertainty is in a separate dataclass (`ScopeUncertainty`), never added to totals. |
| §0.3 | Activity facts append-only; state proposed → validated | **PASS for API**, **PARTIAL for DB** | API enforces via Pydantic validator (`models/requests.py:42-51`). DB has trigger `activity_facts_state_guard` (`schema.sql:160-172`) preventing state regression. |
| §0.4 | No submit / finalize / approve endpoint | **PASS** | `test_api.py:258-268` enforces this structurally. No forbidden paths exist in any router. |
| §0.5 | Multi-tenancy enforced at DB via RLS | **PASS** | `migrations/20240101000002_rls.sql` has RLS on all 7 tenant tables. Adversarial tests in `test_rls_adversarial.py:212-249` verify cross-tenant SELECT/UPDATE blocked. |
| §0.6 | Every request injects bureau_id + role GUC | **PARTIAL** | API: `deps.py:79-80` sets both. Worker: `tasks/ingest.py:74-76` and `tasks/ingest.py:222-224` set both. **However:** RLS policies only check `current_bureau_id()` — `current_bureau_role()` exists but is not used in any policy. |
| §0.7 | Emission factors effective-dated | **PASS** | `factors.py:39-44` filters by `effective_from <= on_date and (effective_to is None or effective_to >= on_date)`. |
| §0.8 | Scope 2 dual-valued (location AND market) | **PASS** | `calc.py:277-284` iterates both `scope2_type` matches. Both are persisted. |
| §0.9 | Unit conversion is data, not code | **PASS** | `conversion.py:1-100` is pure graph traversal. `conversion_factors` table is the source of truth. No hardcoded coefficients in calc logic. |
| §0.10 | `compute_emissions` persists immutable snapshot | **PASS for immutability**, **MISSING audit_log writes** | Snapshot rows are insert-only (RLS allows SELECT/INSERT only; no UPDATE/DELETE policy). **BUT:** `audit_log` is supposed to receive an `EXTRACT`, `VALIDATE`, `COMPUTE` entry per BUILD_PLAN §7 — see [B.1] below. |
| §0.11 | Raw data never leaves region; only aggregate DOCX | **TO BE REWRITTEN per locked decision** | Per TODOLIST Phase 1.1, the strict clause is replaced with managed-API-allowed-under-DPA language. |
| §0.12 | AI transparency disclosure on every report | **PASS** | `narrative.py:21-36` defines `DISCLOSURE_BLOCK`. `renderer.py:95-97` always inserts it. `test_report.py:147-173` enforces structurally. |

### B.1 — CRITICAL: `audit_log` table is never written to
- **Location:** `schema.sql:219-231` defines the table. `rls.sql:123-130` enables RLS. But a grep across the entire `apps/` directory returns **zero `INSERT INTO audit_log` statements**. BUILD_PLAN §7 explicitly says: "populate audit_log for every extraction (with confidence) and every validated→snapshot transition."
- **Why it matters:** Audit trail is a hard regulatory requirement for bureau d'étude clients (who must demonstrate non-repudiation to their own clients and to ADEME auditors). Without writes, the table is a compliance hole.
- **Fix:** Phase 2 of TODOLIST. Effort: 0.5 day.

### B.2 — CRITICAL: `current_bureau_role()` GUC is set but never enforced
- **Location:** `deps.py:80` sets `app.role`; `rls.sql:10-18` defines `current_bureau_role()` function. But no policy uses it.
- **Why it matters:** A `consultant` user can do everything an `admin` can do, including changing `bureaus.google_export_enabled`.
- **Fix:** Phase 3 of TODOLIST (RBAC).

### B.3 — `users` table exists but has no API endpoint to manage it
- **Location:** `schema.sql:110-115` defines `users(id, bureau_id, role)`. RLS exists. But no router exposes CRUD.
- **Fix:** Phase 3 of TODOLIST.

### B.4 — `anomalies` can be created by anyone with a tenant token
- **Location:** `routers/anomalies.py:14-43`. No constraint on who can write `error`-level anomalies.
- **Recommendation:** Accept as-is; consultants flagging their own data as suspicious is fine.

---

## C) Bureau d'étude expert fixes

What a real carbon consulting firm in Morocco/France would demand before paying. Grouped by criticality.

### C.1 — Must-fix for MVP

#### C.1.1 — Onboarding / signup flow
- **Reality today:** No public signup endpoint. The only path to a new bureau is manual SQL.
- **What a bureau needs:** Admin-invited only for the first 6 months (per locked decision). Phase 3.

#### C.1.2 — Audit log writes
- See [B.1]. **Phase 2.**

#### C.1.3 — Role-based access control (admin/consultant/reviewer)
- See [B.2]. **Phase 3.**

#### C.1.4 — Per-bureau region pinning (residency enforcement)
- Locked decision: managed-API providers are acceptable under DPA + audit_log. The "region pinning" is now about *which* provider (cost-optimized) not *whether* provider.

#### C.1.5 — Data export for the client
- **Phase 6:** Snapshot share link.

#### C.1.6 — Backup / disaster recovery
- **Phase 5:** Hetzner Storage Box backup + restore drill.

#### C.1.7 — Reporting template flexibility
- Today the seed has exactly one methodology: `Bilan Carbone v8`. A French consulting firm also needs:
  - **GHG Protocol Corporate Standard**
  - **ISO 14064-1**
  - **CSRD/ESRS E1**
  - **CDP Climate**
  - **SBTi target tracking**
- **Phase 11:** CSRD-readiness first.

#### C.1.8 — French/Arabic template language
- **Phase 10:** Cherry-pick AR + AMEE Loi 47-09 from remote.

#### C.1.9 — Source data retention policy
- Defer to post-MVP. Document in DEPLOYMENT.md.

### C.2 — Should-fix soon (post-MVP, pre-first-paying-customer)

| Item | Effort | Note |
|---|---|---|
| Subscription / billing (Stripe) | 1-2 weeks | Defer. Manual invoicing for first 3-5 customers. |
| Multi-project dashboard / activity feed | 1-2 days | Standard SaaS feature. |
| Sector-specific factor sets | 1 day/sector | Per industry sector (cement, steel, agriculture). |
| Validation rules engine (advisory) | 1 week | Not blockers; surface as anomalies. |
| Mobile-friendly review | 0.5 day | Tailwind responsive; visual review on breakpoints. |
| Email notifications | 0.5 day | Resend / SendGrid. |
| Sector reporting benchmarks | 2-4 weeks | Sticky feature; needs anonymized data. |
| CSRD-readiness | 1 week | **Phase 11.** |
| Per-client historical trend | 1 week | Cross-project aggregation. |
| White-label option | 1 day | |

### C.3 — Nice-to-have

Public API for the bureau to integrate with their own ERP, Slack/Teams notifications, mobile app (PWA), AI-assisted fact proposal, carbon offset marketplace, real-time emissions dashboard, data connector integrations (Silae, Sage, Pennylane), multi-currency, IFRS S2 alignment.

---

## D) Deployment-readiness gaps

### D.1 — Production Dockerfile / docker-compose
- **Status:** Already done in remote `master` (commits `a8616b9`, `66f7387`). Cherry-pick on merge.

### D.2 — CORS middleware
- **Status:** Already done in remote (`0a2c039`). Cherry-pick.

### D.3 — Request body size limit
- **Status:** Already done in remote. Cherry-pick.

### D.4 — Rate limiting
- **Status:** Already done in remote (`66f7387`) via slowapi. Cherry-pick.

### D.5 — Secrets management
- **Status:** Has hardcoded defaults in `config.py:10,12`:
  ```python
  supabase_jwt_secret: str = "super-secret-jwt-key-for-testing"
  secret_key: str = "dev-secret"
  ```
  Remote has a fix (`03c3ce6`); cherry-pick.

### D.6 — HTTPS / TLS termination
- Caddy reverse proxy with auto-TLS (Let's Encrypt). Document in DEPLOYMENT.md.

### D.7 — Observability / error tracking
- **Phase 7:** Sentry + structlog + deep health check.

### D.8 — Database connection pooling
- `deps.py:71-87` opens a fresh psycopg2 connection per request. Use Supabase pgbouncer (port 6543) or `psycopg2.pool.ThreadedConnectionPool`. Effort: 2 hours.

### D.9 — Background job retry / dead-letter queue
- Celery has `max_retries=3` on `ingest.py:297` and `max_retries=2` on `generate_report.py:66`. Add `task_failure` signal handler that logs to a `dead_letters` table.

### D.10 — Health check depth
- `main.py:22-23` returns `{"status": "ok"}` always. Doesn't check DB or Redis. **Phase 7.3.**

### D.11 — Database migrations are SQL files, not managed
- Manual `psql`-paste into Supabase SQL Editor. Adopt `supabase db push` or wire up Alembic. Effort: 1 day.

### D.12 — `psql` dependency not declared
- Tests use portable PG17 in `C:\Users\Hamza\AppData\Local\pg17_portable\bin\`. Document in README.

---

## E) Security gaps

### E.1 — Hardcoded secret defaults
- See [D.5]. **CRITICAL.** Cherry-pick from remote.

### E.2 — `google_access_token` as query parameter
- **Location:** `apps/api/src/adrar_api/routers/reports.py:128`
- **Code:** `google_access_token: str = ""` in the function signature
- **Why it's bad:** Query parameters are logged in nginx access logs, FastAPI access logs, any reverse proxy logs, browser history, error tracking breadcrumbs, uptime monitors. **A Google OAuth access token is a bearer credential.** Leaking it = full Google Drive access for the user's account until the token expires (1 hour).
- **Fix:** Move to request body. The remote master (commit `0a2c039`) already has this fix. Cherry-pick.

### E.3 — No MIME validation on uploads
- **Attack:** A file named `energy.csv` containing `<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>` — the route is "csv" and pdfplumber/openpyxl will be called, but the underlying parser is a PDF parser on what is actually XML/HTML. Library-specific CVEs.
- **Fix:** Use `python-magic` to check magic bytes match the expected MIME. The remote commit `0a2c039` mentions "magic byte file checks" — already fixed remotely. Cherry-pick.

### E.4 — No antivirus / malware scan
- Acceptable for MVP. Document as "tenant trusts uploaded documents; consultant must scan client docs before upload."

### E.5 — No rate limiting
- An attacker with a valid JWT can issue 1000 compute requests in 1 second, OOMing the kernel and DB. The kernel is fast (no I/O) but `compute_emissions` fetches ALL factors, ALL edges, ALL GWP values for the methodology.
- **Fix:** Per-bureau rate limit on `POST /projects/{id}/compute` (e.g. 10/min). Already done in remote. Cherry-pick.

### E.6 — JWT `verify_aud: False`
- **Location:** `apps/api/src/adrar_api/deps.py:35` — `options={"verify_aud": False}`
- **Fix:** Set to `True` and require `aud="authenticated"`. The remote master has this fix. Cherry-pick.

### E.7 — No CSRF
- **Status: ACCEPTABLE.** JWT-only, so traditional CSRF doesn't apply.

### E.8 — SQL injection
- **Status: PASS.** Every SQL uses `%s` placeholders + tuple params. The dynamic `merge_sql` in `routers/activity.py:142-154` is safe (validated model, not user input). Worth a code comment.

### E.9 — Dependency CVEs
- `python-jose[cryptography]>=3.3` has had CVEs (CVE-2024-33663, CVE-2024-33664) for algorithm confusion. **Recommend switching to `pyjwt` which is actively maintained.** Effort: 1 hour.
- `fastapi==0.111+` (range) — should pin. Add `pip-audit` to CI.

### E.10 — No CSP / security headers on web
- **Location:** `apps/web/next.config.js:1-8` — has only `experimental.typedRoutes`. No `headers()` block.
- **Missing headers:** CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- **Fix:** 15 min. Add to `next.config.js`. The remote commit `62f615b` has this. Cherry-pick.

### E.11 — `Supabase JWT secret` and database password in plain `.env`
- Add a pre-commit hook (`detect-private-keys`, `gitleaks`) and a `pre-commit` config.

### E.12 — Multi-tenancy in the worker
- **Status: PASS** if the API is the only caller (it is). Document in `SECURITY.md`.

### E.13 — Logging credentials
- `ingest.py:323` logs `bureau_id`, `project_id`, `filename` on failure. None of these are secrets. **PASS.**

---

## F) Testing gaps

### F.1 — Audit log tests
- **Gap:** No tests for `audit_log` because no code writes to it (see B.1). When Phase 2 lands, add 4 tests:
  1. Extraction inserts audit_log with action='EXTRACT' and confidence populated.
  2. Validate inserts audit_log with action='VALIDATE' and after_state.state='validated'.
  3. Compute inserts audit_log with action='COMPUTE' and after_state.state_hash.
  4. Export inserts audit_log with action='EXPORT' and metadata.google_doc_id.
  5. audit_log rows are insert-only (RLS denies UPDATE/DELETE).

### F.2 — Snapshot immutability
- **Already tested** (`test_rls_adversarial.py:286-313`). PASS.

### F.3 — Cross-tenant adversarial
- **Tested for SELECT/UPDATE.** Not tested for: cross-tenant DELETE on documents, cross-tenant INSERT with different bureau_id, bureau_id field swapped on PATCH/PUT.

### F.4 — API edge cases
- Missing: `gwp_basis="AR7"` (invalid Literal); `reporting_year=1900` (no factor set); pagination (`GET /projects/{id}/snapshots?limit=10000`).

### F.5 — Worker pipeline integration
- No end-to-end test: upload → extract → propose → validate → compute → snapshot → report DOCX. **Recommend:** one E2E test that runs all of it against the portable PG.

### F.6 — Concurrency / load testing
- **Zero.** No `locust` script, no `k6` script. A burst of 10 concurrent compute requests from 10 different bureaux may not isolate cleanly.

### F.7 — Security tests
- **Zero.** No tests for SQL injection, malicious JWT, XSS, path traversal, XXE, CSV formula injection, 4GB file upload DoS.

### F.8 — `audit_log` cannot be tampered with
- Once Phase 2 lands, add a test that proves: an `app_user` (RLS-enforced) cannot UPDATE or DELETE audit_log rows.

### F.9 — Conversion as data — round-trip
- Missing: round-trip test where `from_unit=A→to_unit=B` and `B→A` are both well-defined and `combined_coefficient × inverse = 1`.

### F.10 — Determinism under Decimal edge cases
- Test with values that produce non-terminating decimal expansions.

### F.11 — Coverage reporting
- `pyproject.toml:21-22` has `testpaths` but no `pytest-cov` config, no coverage reporting in CI. Add `pytest-cov` with `--cov-fail-under=80`.

### F.12 — Frontend test coverage
- The single `test_ui_invariants.mjs` is a structural regex test, not a real test. For a 3-page app, Playwright would be 1 day of work.

### F.13 — `activity_facts.state` filter parameter
- `routers/activity.py:85` accepts `state: str | None`. Not validated against `Literal`. **Phase 9.5.**

---

## G) YAGNI / over-engineering

### G.1 — YAGNI candidates to remove

#### G.1.1 — Hardcoded narrative stub
- `narrative.py:38-54` defines `_STUB_NARRATIVE` as a French multi-paragraph narrative. In production, if the LLM is unavailable, returning a 6-sentence stub is misleading.
- **Recommendation:** On no-key/no-network, **raise an exception** that the API returns as 503. **Phase 9.4.**

#### G.1.2 — Duplicate Scope 2 fields in `report_snapshots`
- `schema.sql:186-187` has `scope2_location_t NUMERIC` and `scope2_market_t NUMERIC` as top-level columns, **and** the `totals_co2e` JSONB has `scope2_location` and `scope2_market`. Data duplication.
- **Recommendation:** Keep `totals_co2e` as single source, drop the two top-level columns. **Phase 9.1.**

#### G.1.3 — `ConversionStep` has unused `source` field
- `types.py:82` defines `source: str | None` in `ConversionStep`. The seed has it populated. But `compute_svc.py:245-260` does NOT include `source` in the trace JSON.
- **Either:** include `source` in the trace (audit requirement) and display in DOCX. **Or:** drop the field.

#### G.1.4 — `_gwp` baseline assumption
- `_lookup_gwp` in `calc.py:46-47` and `52-53` short-circuits CO2 and CO2e to value=1. The seed has the data row but the kernel ignores it.
- **Recommendation:** Drop the short-circuit. **Phase 9.2.**

#### G.1.5 — `application/octet-stream` fallback
- `documents.py:40` accepts any content_type if filename has no extension. The route then falls into "unknown" and returns no facts. A consultant uploading a `.bin` file silently gets "0 facts extracted" with no error. Should 415 or 400.

#### G.1.6 — `api.ts:38` swallows non-JSON errors
- `try { j = await res.json(); msg = j.detail ?? msg; } catch {}` — silently ignores JSON parse errors. Acceptable for MVP; document the limitation.

#### G.1.7 — Unused `reviewer_note` is one-to-one with `provenance` blob
- `routers/activity.py:134-138` merges `reviewer_note` into `provenance` JSONB. But `provenance` was designed for extraction metadata. Putting a user comment there is mixing concerns.
- **Recommendation:** Add a `reviewer_note TEXT` column to `activity_facts` (migration 004). **Phase 9.3.**

#### G.1.8 — Hardcoded methodology UUID in UI
- `apps/web/src/app/projects/page.tsx:45` hardcodes the Bilan Carbone UUID `00000000-0000-0000-0000-000000000001`. **Wrong** — breaks if seed is regenerated.
- **Recommendation:** Use the `/methodologies` endpoint (remote commit `06ff1dd`). **Phase 9.6.**

#### G.1.9 — `xlrd` legacy mention (none, just `openpyxl`)
- Confirmed only `openpyxl` is used for XLSX; good. **PASS** — ponytail-clean.

### G.2 — Things that look over-engineered but are correct (don't remove)

- `PureType` dataclasses being `frozen=True` — necessary for state_hash determinism.
- `Decimal` everywhere — correct, prevents float drift in financial reporting.
- The `ConversionChain` returning a list of `ConversionStep`s — needed for the audit trace.
- `state_hash` being a 64-char hex — needed for reproducibility verification by external auditors.
- `report_snapshots` being insert-only — needed for §0.10 and for ADEME audit trail.

---

## H) Documentation gaps

For a deployable SaaS, what should exist but doesn't.

### H.1 — README.md
- **Status: ABSENT.** The only top-level markdown files are `CLAUDE.md`, `HANDOVER.md`, `PROGRESS.md`, `BUILD_PLAN.md`. **Phase 8.1.**

### H.2 — LICENSE
- **Status: ABSENT.** No LICENSE file. **Phase 8.2.**

### H.3 — ARCHITECTURE.md
- **Status: ABSENT.** **Phase 8.3.**

### H.4 — CONTRIBUTING.md
- **Status: ABSENT.** OK for a private product.

### H.5 — CHANGELOG.md
- **Status: ABSENT.** **Phase 8.5.**

### H.6 — DEPLOYMENT.md / RUNBOOK
- **Status: ABSENT.** **Phase 8.4.**

### H.7 — API documentation
- **Status: PARTIAL.** FastAPI auto-generates `/docs` and `/redoc`. Add a `docs/api-overview.md` describing the trust tiers.

### H.8 — Customer-facing onboarding guide
- **Status: ABSENT.** A new bureau admin has zero documentation. Effort: 1 day.

### H.9 — Compliance documentation
- **Status: ABSENT.** RGPD compliance statement, AI Act compliance, DPAs. **Phase 8.8** (`docs/dpa-providers.md`).

### H.10 — Database schema documentation
- **Status: PARTIAL.** SQL comments in the migrations are good. **Phase 8.6** (`docs/data-model.md`).

---

## I) Phased implementation plan

See `TODOLIST.md` for the canonical phased plan. This audit's full phased plan has been merged into `TODOLIST.md` with priority labels (P0/P1/P2), cost model, and locked architectural decisions.

---

## J) Open questions (resolved in this session)

### J.1 — Local working tree vs remote origin/master — **RESOLVED: merge origin/master first**
### J.2 — Chinese OCR provider — **RESOLVED: PaddleOCR-VL-1.5 via Aliyun DashScope**
### J.3 — LLM extraction provider — **RESOLVED: Qwen3-Plus via OpenRouter (fallback GLM-4-Plus), full Chinese stack**
### J.4 — Data residency strategy — **RESOLVED: managed API only, no self-host, Hetzner CX33 hosts all compute**
### J.5 — Onboarding model — **RESOLVED: admin-invited only for first 6 months**
### J.6 — §0.11 wording — **RESOLVED: rewrite to managed-API-allowed-under-DPA scope**
### J.7 — TODO list location — **RESOLVED: TODOLIST.md in repo root**

### Open (carried into TODOLIST.md "Open items" section)

1. Supabase Pro plan confirmation
2. Caddy vs nginx
3. Hetzner Storage Box
4. DPA collection checklist
5. First pilot bureau

### Deferred questions (post-MVP)

- Stripe billing model
- CSRD / ISO 14064 / GHG Protocol methodology priority
- First customer vertical (MA industrial vs FR tertiary)
- AR in MVP or post-MVP
- Audit retention period
- Open-source vs proprietary
- Google Drive export as hard requirement
- Confirmed design partner before shipping

---

## K) Local vs Remote Discrepancy

The remote `origin/master` (and feature branches like `claude/friendly-gates-m8zhxm`) contains ~30 additional commits not in the local working tree. Major items already done remotely that this audit would otherwise recommend:

| Item | Local | Remote | Recommendation |
|---|---|---|---|
| Phase 6 UI (login, projects, project detail) | Partial (uncommitted WIP) | Done (62f615b) | Cherry-pick |
| Phase 7 hardening (audit + residency) | Not done | Done (eaf807f) | Cherry-pick |
| SECURITY.md | Not present | Done (5361c6b) | Cherry-pick |
| Production secret checks | Hardcoded defaults | Hardened (03c3ce6) | Cherry-pick |
| Rate limiting (slowapi) | Not present | Done (66f7387) | Cherry-pick |
| Docker Compose + Dockerfiles | Not present | Done (a8616b9) | Cherry-pick |
| Multi-provider LLM cascade | Single Anthropic | Done (36d01c4) | Cherry-pick — **this is the Chinese AI swap you want** |
| CORS middleware | Not present | Done (0a2c039) | Cherry-pick |
| Body size limit middleware | Not present | Done (0a2c039) | Cherry-pick |
| CSP / security headers (next.config.js) | Not present | Done (62f615b) | Cherry-pick |
| Magic byte file checks | Not present | Done (0a2c039) | Cherry-pick |
| Filename sanitization | Not present | Done (0a2c039) | Cherry-pick |
| MIME allowlist | Not present | Done (0a2c039) | Cherry-pick |
| UUID path parameter validation | Not present | Done (1ab707b) | Cherry-pick |
| JWT audience validation | Disabled | Enabled (0a2c039) | Cherry-pick |
| Generic error messages | Leaks server details | Sanitized (0a2c039) | Cherry-pick |
| google_access_token in body not query | In query (logs leak) | In body (0a2c039) | Cherry-pick |
| JAD2 brand UI (navy #1a2e5e) | Plain Tailwind | Branded (0a2c039) | Cherry-pick — verify brand approval |
| FR/EN language toggle | Not present | Done (0a2c039) | Cherry-pick |
| Morocco BVC RSE / Piliers E/S/G | Not present | Done (86f9677, 460cb4e) | Cherry-pick if targeting MA |
| AMEE Loi 47-09 / Bilan Énergétique | Not present | Done (a099be0) | Cherry-pick if targeting MA |
| GRI 305-4 intensity / NDC Morocco | Not present | Done (a49f35a, 5447da3) | Cherry-pick if targeting MA |
| AR language | Not present | Done (becdd24) | Cherry-pick if MA market |
| Error boundary (error.tsx) | Not present | Done (e0c140e) | Cherry-pick |
| Document list UI | Not present | Done (159fb05) | Cherry-pick |
| 404/loading pages + metadata | Not present | Done (ed649da) | Cherry-pick |
| Project cards hover + JAD2 topbar | Not present | Done (dcb2710) | Cherry-pick |
| /methodologies endpoint | Hardcoded UUID in UI | Done (06ff1dd) | Cherry-pick |
| Rate-limit decorator imports | Not present | Done (66f7387) | Cherry-pick |

**Concrete recommendation:** Before any new phase work, do a one-session merge of `origin/master` into local `master`, resolve any conflicts (the working tree's WIP UI work will likely conflict with the remote's full UI), and then audit the merged result. The remote has done 90% of the "obvious" work this audit would recommend. The local is just stale.

---

## L) TL;DR (the 1-page version)

1. **The biggest cost win is the fully-Chinese provider swap.** Replace Anthropic Haiku 4.5 with **PaddleOCR-VL-1.5 via Aliyun DashScope** for OCR, **Qwen3-Plus via OpenRouter** for structured extraction, **DeepSeek V3 via OpenRouter** for narrative. ~80% cost reduction; from $100–$300/month to $5–$20/month at typical bureau load. All via API. No self-host. No separate GPU node — Hetzner CX33 hosts everything else.

2. **The biggest regulatory risk is the unwritten `audit_log` table.** The table exists, RLS exists, no code writes to it. ADEME-grade auditability is broken. Half a day to fix. **Phase 2.**

3. **The biggest deployment risk is the lack of Docker, CORS, rate limit, and prod secret checks** in the local working tree. All four exist in the remote — cherry-pick. **Phase 0 + Phase 4.**

4. **The biggest commercial gap is onboarding** — no public signup, no admin user management, no role-based access. A first paying customer cannot actually use the product today. **Phase 3.**

5. **The biggest YAGNI win is removing the duplicate `scope2_location_t`/`scope2_market_t` columns** (and the hardcoded CO2 GWP short-circuit) in favor of single-source-of-truth fields. **Phase 9.**

6. **The biggest documentation gap is the missing README, LICENSE, ARCHITECTURE, DEPLOYMENT, CHANGELOG** — a paying customer will not buy software with no README. **Phase 8.**

7. **The local working tree is stale by ~30 commits** vs `origin/master`, which already has most of what this audit recommends. Merge the remote first, then re-audit. **Phase 0.**

8. **§0.11 needs rewriting** — the strict "raw never leaves region" rule conflicts with practical MA market use. The locked decision allows managed-API providers under DPA + audit_log. The disclosure (§0.12) and aggregate-DOCX-export (Google Docs opt-in) halves stay.

9. **YAGNI in scope:** the stub narrative in `narrative.py`, the duplicate S2 columns, the hardcoded CO2 GWP short-circuit, the UUID hardcoded in the UI, the `provenance` blob doubling as a review-comment store.

10. **Total realistic effort to MVP-ready: 6–8 weeks of focused engineering**, sequenced per `TODOLIST.md` Phase 0 → Phase 12.
