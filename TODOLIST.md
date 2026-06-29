# TODOLIST.md — Adrar AI MVP-Readiness Plan

**Generated:** 2026-06-29
**Target:** MVP-ready SaaS, deployed on existing Hetzner CX33 (8 vCPU / 16 GB, peak 20% usage), MA market first, expand to EU later.
**Strategy:** Merge `origin/master` first (it has Phase 6, Phase 7, multi-provider LLM cascade, Docker, security headers, Morocco GRI/AMEE features already done). Then layer in the fully-Chinese provider swap, audit log writes, MA-deployment, and onboarding.
**All AI/OCR/LLM via API. No self-host. No separate GPU node.** Hetzner CX33 hosts api + web + worker + redis; Postgres on Supabase; AI providers via OpenRouter / Aliyun DashScope.

---

## Locked architectural decisions (this session)

- **No self-host** of any model. All inference via managed API.
- **CX33 single host** for api + web + worker + redis (headroom is fine; 20% peak leaves plenty).
- **Provider stack — fully Chinese**:
  - **OCR (raw PDF → text)**: PaddleOCR-VL-1.5 via Aliyun DashScope managed API. SOTA on multilingual FR/AR, ~$0.002–0.005/page.
  - **LLM extraction (text → structured activity facts)**: Qwen3-Plus via OpenRouter, fallback GLM-4-Plus. ~$0.001–0.005/extraction.
  - **LLM narrative (snapshot aggregates → French report)**: DeepSeek V3 via OpenRouter, fallback Qwen3-Plus. ~$0.001–0.003/report.
- **§0.11 update**: rewrite to MA legal scope, not the universal "raw never leaves region" rule. Allow managed-API OCR for raw scans; keep the AI transparency disclosure (§0.12); keep the "consultant-reviewed aggregate DOCX → Google Docs opt-in" half.
- **Onboarding**: admin-invited only for the first 6 months.

---

## Cost model at 3 scales (per-bureau TCO)

Assumptions: 1 scan = 10-page raw PDF; 1 report = 1 Bilan Carbone DOCX. Old = current Anthropic Haiku 4.5. New = fully Chinese stack.

| Scale | Scans/mo | Reports/mo | Old (Anthropic) | New (Chinese) | Saving | + Hetzner CX33 | + Supabase Pro | New TCO |
|---|---|---|---|---|---|---|---|---|
| **1 bureau (pilot)** | 100 | 10 | $10–30/mo | $2.50–5.50/mo | ~80% | €15/mo | €25/mo | **~$45–50/bureau** |
| **10 bureaux (early SaaS)** | 1,000 | 100 | $100–300/mo | $25–55/mo | ~80% | €15/mo (shared) | €25/mo (shared) | **~$7–10/bureau** |
| **100 bureaux (scaled)** | 10,000 | 1,000 | $1,000–3,000/mo | $250–550/mo | ~80% | scale-out (CX53 + DB) | ~$200/mo Supabase team | **~$3–6/bureau** |

Breakeven vs Sweep (~$500–2,000/workspace/mo) or Watershed (~$5,000+/yr): **5–10 paying bureaux is already profitable**, dominated by Supabase + Hetzner, not by API costs.

---

## Phase 0 — Merge origin/master into local (1 day)
- 0.1 Stash WIP Phase 6 UI on `feature/phase6-wip` branch (current changes uncommitted).
- 0.2 `git fetch origin && git merge origin/master` — resolve conflicts with the WIP UI.
- 0.3 Run full test suite — must stay green (75+ tests: 25 kernel + 23 API + 12 ingestion + 15 report + Phase 6 UI invariant).
- 0.4 Update `PROGRESS.md` to reflect merged state.
- 0.5 Confirm the remote's `narrative.py` cascade now lists DeepSeek + Qwen + GLM + Gemini; record the source.

## Phase 1 — Fully-Chinese provider swap (P0, ~3–5 days)
**Why:** ~80% API cost reduction; better FR/AR quality on managed models; reduces MA tenant regulatory friction.

### 1.1 — Update CLAUDE.md stack list (§0.11 wording)
- 1.1.1 Replace §0.11 strict clause with: *"Raw documents and raw activity facts may be processed by managed-API providers under data-processing agreement; only the consultant-reviewed aggregate DOCX may be exported to Google Docs (opt-in, default OFF). All provider calls must be logged to `audit_log` for non-repudiation."*
- 1.1.2 Update the "docs processing" line in the stack to: *"pymupdf, pdfplumber, openpyxl, python-docx; PaddleOCR-VL-1.5 via Aliyun DashScope (multilingual FR/AR scans, API). No self-hosted models."*
- 1.1.3 Add the cascade list to the "narrative" line: *"DeepSeek V3 (primary, cheapest, good French) → Qwen3-Plus (FR best) → GLM-4-Plus (cheap, last fallback)."*

### 1.2 — OCR: PaddleOCR-VL-1.5 via Aliyun DashScope
- 1.2.1 Add `aliyun_dashscope.py` parser in `apps/worker/src/adrar_worker/parsers/`. Calls DashScope's `paddleocr-vl` endpoint with the raw PDF, returns text + bounding boxes + per-page confidence.
- 1.2.2 Add `DASHSCOPE_API_KEY` + `OCR_ENGINE=paddleocr_vl_15` env vars to `.env.example`.
- 1.2.3 Refactor `scan_parser.py` to call PaddleOCR first, fall back to Anthropic only if `OCR_ENGINE=anthropic` (offline dev escape hatch).
- 1.2.4 Keep the deterministic parsers (pdfplumber, openpyxl, csv) as the cheap path; only messy scans go to PaddleOCR.
- 1.2.5 Tests with mocked HTTP responses (use `responses` lib).

### 1.3 — Structured extraction: Qwen3-Plus via OpenRouter
- 1.3.1 Refactor the extraction step in `scan_parser.py` (post-OCR) to call Qwen3-Plus for "raw OCR text → activity facts JSON". Replaces the current Haiku single-prompt extraction.
- 1.3.2 Add `OPENROUTER_API_KEY` + `EXTRACTION_MODEL=qwen/qwen3-plus` to `.env.example`.
- 1.3.3 Cascade: Qwen3-Plus → GLM-4-Plus (fallback). Skip Gemini (user pivoted away).
- 1.3.4 Tests.

### 1.4 — Narrative: DeepSeek V3 via OpenRouter (already in remote cascade; verify primary)
- 1.4.1 Confirm the remote's `narrative.py` lists DeepSeek V3 as primary. If Anthropic still primary, swap.
- 1.4.2 Set `NARRATIVE_MODEL=deepseek/deepseek-chat-v3` in `.env.example`.
- 1.4.3 Test narrative generation against a real snapshot.

### 1.5 — Cost instrumentation
- 1.5.1 Log per-call cost (input tokens × price + output tokens × price) to `audit_log.metadata` for every EXTRACT/NARRATIVE action.
- 1.5.2 Document how to query the cost in `DEPLOYMENT.md`.

## Phase 2 — Audit log writes (P0, ~0.5 day)
**Why:** `audit_log` table exists, RLS exists, **no code writes to it** in the local tree. ADEME-grade auditability is broken.

- 2.1 EXTRACT — in `tasks/ingest.py:_write_proposed_facts`, INSERT into `audit_log` with `action='EXTRACT'`, `entity_type='document'`, `entity_id=doc_id`, `confidence=avg(f.confidence)`, `metadata={"provider": ..., "cost_usd": ...}`.
- 2.2 VALIDATE — in `routers/activity.py:validate_activity_fact`, INSERT with `action='VALIDATE'`, `entity_type='activity_fact'`, `entity_id=fact_id`, `before_state={"state":"proposed"}`, `after_state={"state":"validated","reviewer_note":...}`.
- 2.3 COMPUTE — in `services/compute_svc.py:run_compute_and_persist`, INSERT with `action='COMPUTE'`, `entity_type='snapshot'`, `entity_id=snap_id`, `after_state={"state_hash":...,"scope1":...,"total":...,"provider_costs":...}`.
- 2.4 EXPORT — in `routers/reports.py:export_to_google_docs`, INSERT with `action='EXPORT'`, `entity_type='snapshot'`, `entity_id=snap_id`, `metadata={"google_doc_id":...}`.
- 2.5 Tests: each action writes a row; `audit_log` rows are insert-only under RLS.

## Phase 3 — Onboarding + RBAC (P0, ~1 week)
**Why:** Without onboarding, first paying customer cannot use the product.

- 3.1 `users` CRUD endpoints (admin-only): `GET /users`, `PATCH /users/{id}/role` (admin/consultant/reviewer).
- 3.2 `POST /admin/invite-user` — sends Supabase magic-link, sets role. Admin-invited only.
- 3.3 `POST /admin/bureaus` — service-role-only, creates new bureau. CLI/SQL today, endpoint later.
- 3.4 Role enforcement in `deps.py`: `require_role("admin")` helper; wire to `validate_activity_fact` (consultant+), `invite_user` (admin only), `flag_anomaly` (all roles).
- 3.5 Frontend: minimal admin page to invite users. Server-side auth.
- 3.6 Tests.

## Phase 4 — Production deployment on Hetzner CX33 (P0, ~2 days)
**Why:** First paying customer needs a real URL.

- 4.1 Use the remote's existing `docker-compose.yml` + `Dockerfile`s (already there per `a8616b9`).
- 4.2 Provision Hetzner CX33 (already in use, peaks at 20%): api + web + worker + redis all in one docker-compose. Postgres on Supabase. No GPU node.
- 4.3 Configure env: `SUPABASE_URL`, `DATABASE_URL`, `REDIS_URL`, `DASHSCOPE_API_KEY`, `OPENROUTER_API_KEY`, `ALLOWED_ORIGINS`, `SESSION_SECRET`, `ENV=production`.
- 4.4 Caddy reverse proxy with auto-TLS (Let's Encrypt).
- 4.5 Hetzner Volume for postgres data; daily `pg_dump` to Hetzner Storage Box (~€3.50/mo).
- 4.6 Verify all remote hardening landed: CORS, body limits, slowapi rate limits, prod secret checks, CSP headers, `google_access_token` in body, MIME allowlist, magic-byte checks, JWT audience validation.

## Phase 5 — Backup + DR (P0, ~1 day)
- 5.1 `pg_dump` script (Hetzner cron, daily 03:00).
- 5.2 Encrypted offsite backup to Hetzner Storage Box (gpg + 30-day retention).
- 5.3 Restore drill: `scripts/restore.sh` tested on sandbox.
- 5.4 Document RPO (24h) and RTO (4h) in `DEPLOYMENT.md`.
- 5.5 GitHub Action: runs the backup, alerts on failure.

## Phase 6 — Snapshot share link (P1, ~2 days)
**Why:** "Wow" feature — clients get a read-only link to their own report. Removes the "how does my client see this?" friction.

- 6.1 `share_links` table: `(snapshot_id, token, expires_at, created_by)`.
- 6.2 `POST /snapshots/{id}/share-link` (bureau) → returns URL.
- 6.3 `GET /share/{token}` (public, no JWT) → DOCX download with the AI transparency disclosure.
- 6.4 RLS: `share_links` visible only to owning bureau; the public endpoint bypasses JWT but checks token.
- 6.5 Frontend: "Share with client" button.
- 6.6 Tests.

## Phase 7 — Observability (P1, ~1 day)
- 7.1 Sentry SDK in api (`sentry-sdk[fastapi]`), worker (`sentry-sdk[celery]`), web (`@sentry/nextjs`).
- 7.2 `structlog` for JSON logging.
- 7.3 Deep `/health` (DB + Redis + Celery worker count).
- 7.4 Frontend error boundary (`app/error.tsx`) → Sentry.

## Phase 8 — Documentation (P1, ~1 day)
- 8.1 `README.md` — what is Adrar AI, who it's for, 5-min local quickstart, tech stack.
- 8.2 `LICENSE` — proprietary (default unless you flip to AGPL).
- 8.3 `ARCHITECTURE.md` — mermaid diagram + per-component paragraph.
- 8.4 `DEPLOYMENT.md` — Hetzner CX33-specific runbook.
- 8.5 `CHANGELOG.md` — auto from `git log`.
- 8.6 `docs/data-model.md` — mermaid ER.
- 8.7 `SECURITY.md` — cherry-pick from remote if not yet present.
- 8.8 `docs/dpa-providers.md` — list of managed providers + their DPAs + data-flow map (for MA regulatory review).

## Phase 9 — YAGNI cleanup (P2, ~1 day)
- 9.1 Drop duplicate `scope2_location_t` / `scope2_market_t` columns from `report_snapshots` (keep `totals_co2e` JSONB). Backfill UPDATE then ALTER.
- 9.2 Drop hardcoded `CO2/CO2e GWP=1` short-circuit in `calc.py:46-47,52-53` — the seed has the data row.
- 9.3 Add `reviewer_note TEXT` column to `activity_facts` (migration 004). Drop the JSONB-into-provenance pattern.
- 9.4 Remove `_STUB_NARRATIVE` in `narrative.py` — on no-key, raise 503 instead of returning a misleading stub.
- 9.5 Validate `state` filter against `Literal["proposed","validated"]` in `routers/activity.py:85`.
- 9.6 Hardcoded methodology UUID in `apps/web/src/app/projects/page.tsx:45` — verify `/methodologies` endpoint landed; use it.

## Phase 10 — Morocco-specific (P1, ~1 week, mostly cherry-picks)
- 10.1 Cherry-pick from remote: AMEE Loi 47-09 / Bilan Énergétique template.
- 10.2 Cherry-pick: GRI 305-4 intensity.
- 10.3 Cherry-pick: NDC Morocco alignment.
- 10.4 Cherry-pick: BVC RSE / Piliers E/S/G scores.
- 10.5 Cherry-pick: AR language + UI toggle.
- 10.6 Cherry-pick: Morocco manual fact picker + BVC/RSE fields.

## Phase 11 — CSRD-readiness (P2, ~1 week)
**Why:** EU expansion (next year) needs CSRD. Unlocks EU enterprise sales.

- 11.1 Seed CSRD methodology + factor set.
- 11.2 CSRD DOCX template (different section structure than Bilan Carbone).
- 11.3 Methodology picker in project create form.
- 11.4 Tests.

## Phase 12 — Post-MVP (defer — NOT in this list)
Stripe billing, sector factor sets, validation rules engine, mobile UI review, email notifications, public API for ERPs, white-label option, carbon offset integration, IFRS S2, SBTi target tracking, CDP Climate.

---

## Critical notes (read before executing)

- **Ponytail rules** govern every phase: YAGNI first, stdlib over deps, native platform features, no unrequested abstractions, intentional simplifications marked with `# ponytail:`.
- **CLAUDE.md §0 invariants** are non-negotiable except for §0.11 (rewriting to MA scope, per this session). Keep:
  - §0.1 Kernel pure & deterministic
  - §0.2 `emissions = activity × factor × gwp` (no uncertainty in totals)
  - §0.3 Activity facts append-only, state proposed → validated (human-only)
  - §0.4 No submit/finalize/approve endpoint
  - §0.5 RLS-enforced multi-tenancy
  - §0.6 bureau_id GUC per request
  - §0.7 Effective-dated emission factors
  - §0.8 Dual Scope 2
  - §0.9 Conversion as data
  - §0.10 Immutable snapshots
  - §0.11 **REWRITE per Phase 1.1** (managed API allowed under DPA + audit_log)
  - §0.12 AI transparency disclosure on every report
- **One phase per session**, per `CLAUDE.md` operating protocol. Run the phase's acceptance test → git commit → update `PROGRESS.md` → 3-line summary → STOP.
- **Cost guard**: at every phase, run the cost projection in Phase 1's table. If new feature adds >$50/mo per 100 scans, document and ask.

---

## Open items (resolve before Phase 1 starts)

1. **Supabase Pro plan confirmation**: €25/mo is the assumption. Confirm your current plan + region.
2. **Caddy vs nginx**: I default to Caddy (auto-TLS, simpler). OK?
3. **Hetzner Storage Box**: €3.50/mo for the backup destination. OK?
4. **DPA collection**: for §0.11 rewrite to land cleanly, you need DPAs (or public DPA URLs) for: Aliyun DashScope, OpenRouter, Supabase, Hetzner. Do you have these or need me to draft a checklist?
5. **First pilot bureau**: do you have a confirmed design partner before launch? Affects scope.
