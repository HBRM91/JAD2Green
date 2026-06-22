# BUILD_PLAN.md — Adrar AI Phase Checklist

One phase per session. Each ends: acceptance test → git commit → PROGRESS.md update → STOP.

---

## PHASE 0 — Scaffold + control files
Create repo structure, CLAUDE.md, BUILD_PLAN.md, PROGRESS.md, .env.example, root tooling
(uv, pnpm), .gitignore.
**Acceptance**: control files exist, compile/lint config runs, repo builds empty.
**Commit**: `chore: scaffold + control files`

## PHASE 1 — Data model + RLS + seed
Migrations for all tables (bureaus, clients, users, projects, methodologies, factor_sets,
emission_factors, conversion_factors, gwp_values, activity_facts, report_snapshots, anomalies,
audit_log). RLS on every tenant table using app.bureau_id GUC. report_snapshots insert-only.
Seed: Bilan Carbone/ADEME methodology, FY2024 factor set, ONEE grid factor, fuel conversion
graph, AR6 GWP values.
**Acceptance**: adversarial — bureau A session cannot SELECT/UPDATE bureau B rows; snapshot rows
reject UPDATE/DELETE.
**Commit**: `feat: schema + RLS + bilan carbone seed`

## PHASE 2 — Pure kernel + tests (THE MOAT)
packages/kernel: (a) conversion-graph resolver (multi-hop, full chain), (b) factor-set selector
by methodology+region+year (effective-dating), (c) emissions calc activity×factor×gwp, dual
Scope 2 (location+market), (d) uncertainty computed separately, (e) computation_trace assembler,
(f) deterministic state_hash. Pure functions only. No web/AI/network imports.
**Acceptance**: determinism (same inputs → identical totals AND identical state_hash); dual S2
present; uncertainty NOT in totals; changing a conversion_factors coefficient changes result with
zero code change; FY2023 vs FY2024 select different factor sets.
**Commit**: `feat: deterministic calc kernel + tests`

## PHASE 3 — Backend API + auth + tenant injection
FastAPI app. Supabase Auth token validation → middleware sets app.bureau_id + app.role GUC per
request. 8 service endpoints by trust tier:
- READ: search_factor_sets, get_conversion, get_activity_data, get_report_snapshot
- PROPOSE (writes proposed only; reject validated): propose_activity, flag_anomaly
- COMPUTE (calls kernel; validated facts only; persists snapshot): compute_emissions, reconcile
Plus minimal CRUD: orgs/projects. No finalize endpoint.
**Acceptance**: endpoint tests; tenant isolation across ALL endpoints; propose_activity cannot set
validated; compute_emissions blocks if un-validated facts exist.
**Commit**: `feat: api + auth + tenant-scoped endpoints`

## PHASE 4 — Document ingestion + extraction
Celery pipeline: upload → virus/format normalize → route: structured (xlsx/csv) via deterministic
parsers; clean PDF via Doc Intelligence; messy multilingual scan via Haiku. Output →
propose_activity with field-level provenance (doc_id, page, bbox, per-field confidence).
Idempotency/dedup by content hash. Reconciliation hooks (Σ monthly = annual; extracted vs
stated-on-doc).
**Acceptance**: dedup proven; provenance populated; extraction writes proposed only; LLM never
touches calc.
**Commit**: `feat: ingestion + extraction → proposed facts`

## PHASE 5 — Report generation + delivery adapter
Jinja2 Bilan Carbone DOCX template; charts (scope pie, category bar, trend) as PNG; LLM
narrative (exec summary/recommendations) — clearly outside kernel, fed only from snapshot
aggregates. AI-transparency disclosure block (§0.12).
Delivery adapter: download (default, in-region); Google Docs export opt-in, default OFF, converts
DOCX via Drive files.create. One-way; raw data never sent to Google.
**Acceptance**: report builds from report_snapshot only; Google export gated + off by default;
verify no raw document/fact data leaves region on export.
**Commit**: `feat: report render + delivery adapter`

## PHASE 6 — Frontend (consultant workflow UI)
Next.js: login (Supabase), project create, document upload, validation gate UI (review proposed
facts → promote to validated — human-only trust boundary), trigger compute, results dashboard
(totals, dual S2, by category, reconciliation flags), report download + opt-in Google export,
review/approval notes.
**Acceptance**: validation gate is the ONLY path to validated; no UI path to auto-finalize;
export toggle defaults off.
**Commit**: `feat: consultant workflow ui`

## PHASE 7 — Hardening (residency, audit, isolation, legal-grade logging)
Region pinning per tenant at onboarding; encrypt Google refresh tokens at rest in-region;
populate audit_log for every extraction (with confidence) and every validated→snapshot
transition; final adversarial multi-tenant pass across the full app.
**Acceptance**: full suite green — reproducibility, no-finalize, cross-tenant isolation,
effective-dating, dual S2, uncertainty separation, conversion-as-data, residency boundary.
**Commit**: `chore: hardening + audit + residency`

## PHASE 8 — CBAM module (DEFERRED — after bureau validates v1)
Reuse the kernel. Add: installation-level embedded-emissions config, EU default-value fallback,
declarant export format, CBAM methodology config + template. Pure config + module.
Build only on explicit go. Do not touch in Phases 0–7.
**Commit**: `feat: cbam module`

---

## ACCEPTANCE SUITE (green from phase introduced onwards)

- Reproducibility: compute_emissions twice → identical totals + identical state_hash
- No-finalize: no code path sets final or auto-validated
- Tenant isolation: bureau A cannot read/write bureau B row, every endpoint + UI flow
- Effective-dating: different reporting years pull different factor sets automatically
- Dual Scope 2: snapshot holds both location- and market-based totals
- Uncertainty separation: totals carry no uncertainty inflation
- Conversion-as-data: editing a coefficient changes results with zero code change
- Residency: report export carries no raw document/fact data; Google export off by default
