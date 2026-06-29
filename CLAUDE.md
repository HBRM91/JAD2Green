# CLAUDE.md — Adrar AI (source of truth for every session)

## OPERATING PROTOCOL
1. One phase per session. Do the current phase from BUILD_PLAN.md, then STOP.
2. Start every session by reading ONLY: CLAUDE.md, BUILD_PLAN.md, PROGRESS.md.
3. End every phase: run acceptance test → git commit → update PROGRESS.md → 3-line summary → STOP.
4. Targeted edits over rewrites. Modify the minimum surface. No speculative refactors.
5. Test once per phase, at the end. Do not loop tests.
6. If blocked or ambiguous, write question into PROGRESS.md under OPEN QUESTIONS and stop.
7. Never violate §0 invariants. If a phase seems to require it, stop and flag.

---

## §0 — LOCKED INVARIANTS (violation = build failure)

1. Calculation kernel is pure & deterministic. No LLM, no network, no I/O beyond reading validated
   facts + factor sets. Same inputs → byte-identical outputs and identical state_hash, forever.
2. emissions = activity × emission_factor × gwp. NO (1 + uncertainty) term. Uncertainty is computed
   and stored SEPARATELY.
3. Activity facts are append-only, with state proposed → validated. Extraction/API may write
   proposed only. Nothing automated may write validated or final.
4. No submit / finalize / approve endpoint or function. Promotion to validated and report
   finalization happen ONLY through explicit human action in the UI (the trust boundary).
5. Multi-tenancy enforced at the DB via RLS, not app code. Tenancy: bureau → its clients.
   No call may ever traverse bureaux.
6. Every request injects tenant context (bureau_id, role) from the auth token into the DB session
   (GUC); RLS does isolation.
7. Emission factors are effective-dated. FY2024 uses the factor set valid for FY2024, never
   "latest". Factor sets carry effective_from/to, gwp_basis, version.
8. Scope 2 is dual-valued: location-based AND market-based, both persisted.
9. Unit conversion is data, not code — a conversion_factors graph (NCV, density, oxidation).
   Never hardcode conversions in calc logic.
10. compute_emissions persists an immutable report_snapshots row with state_hash, full
    computation_trace, factor_set_versions, gwp_basis, uncertainty (separate), reconciliation.
11. Résidence des données (cadre juridique marocain). Documents bruts, activity_facts, snapshots
    et traces de calcul sont hébergés dans la région du tenant (MA par défaut ; EU sur option).
    Tout transfert vers un fournisseur d'API managé (Aliyun DashScope, OpenRouter, Google) doit
    s'appuyer sur un accord de traitement conforme à la **Loi 09-08** (protection des données
    personnelles) et aux directives de la **CNDP**, et chaque appel est tracé dans `audit_log`
    (provider, coût, horodatage) pour non-répudiation. Seuls le rapport DOCX agrégé et revu par
    le consultant et le snapshot associé peuvent être exportés vers Google Docs (opt-in, OFF
    par défaut). L'export est à sens unique (snapshot → Doc) ; les modifications Google ne sont
    jamais resynchronisées. Le facteur **ONEE 2023 (0.679 kgCO₂e/kWh)** est la référence
    réglementaire MA pour Scope 2 location-based.
12. AI transparency: every generated report contains a disclosure block stating AI-assisted
    drafting + that emission factors require expert validation. Marketing says "accelerates expert
    reporting", never "guaranteed compliant".

---

## STACK

- Frontend: Next.js 14 (App Router) + Tailwind + shadcn/ui
- Backend: FastAPI (Python)
- Kernel: packages/kernel — pure Python, no deps on web/AI/network
- Data/Auth/Storage: Supabase (Postgres + pgvector + Storage + Auth). One surface.
  NO Qdrant, NO MinIO, NO Clerk.
- Async: Celery + Redis
- Docs processing: pymupdf, pdfplumber, openpyxl, python-docx; PaddleOCR-VL-1.5 via
  Aliyun DashScope for messy multilingual scans (FR/AR/EN), Qwen3-Plus via OpenRouter for
  OCR-text → structured facts. No self-hosted models. No Anthropic.
- Report render: Jinja2 DOCX + matplotlib/plotly PNG
- Delivery: in-region download (default) + Google Drive files.create adapter (opt-in)
- Hosting: in-region (MA or EU) per tenant

## OUT OF SCOPE (MVP phases 0–7)

❌ MCP server  ❌ CBAM (Phase 8 only, deferred)  ❌ ESRS XBRL  ❌ EcoInvent
❌ Scope 3 product-level  ❌ multilingual templates v1 (FR only)
❌ any auto-finalize path  ❌ LLM in compute path

---

## REPO STRUCTURE

```
adrar/
  CLAUDE.md
  BUILD_PLAN.md
  PROGRESS.md
  .env.example
  pyproject.toml          # uv workspace root
  pnpm-workspace.yaml
  package.json
  supabase/
    migrations/
    seed/
  packages/
    kernel/               # pure deterministic calc + tests
  apps/
    api/                  # FastAPI
    web/                  # Next.js
    worker/               # Celery
```
