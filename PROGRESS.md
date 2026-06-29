# PROGRESS

## Current phase: complete (Phases 0–7 done)
## Next phase: 8 (CBAM — deferred, requires explicit go)

## Done
- [x] Phase 0 — scaffold + control files (commit: ff9bb2f)
- [x] Phase 1 — schema + RLS + seed (commit: 5236c43)
- [x] Phase 2 — kernel (commit: 169bcbd)
- [x] Phase 3 — api (commit: 0b5bc7c)
- [x] Phase 4 — ingestion (commit: 8a660f0)
- [x] Phase 5 — report + delivery (commit: 087b57a)
- [x] Phase 6 — consultant workflow UI (commit: 62f615b remote; 523e9ed local /minimal)
- [x] Phase 7 — hardening (commit: eaf807f)
- [x] Security hardening pass — JWT/UUID validation, magic bytes, CORS, body limit, MIME allowlist (commit: 0a2c039)
- [x] UI brand polish — JAD2 Advisory navy design, FR/EN toggle on all pages, metrics bar, login stats (commit: 333c264)
- [x] Morocco sustainability reporting enhancement:
  - Migration 000005: 4 methodologies (ISO 14064, GHG Protocol, GRI 305, AMEE), ~50 Morocco factors
    (butane, ONCF, OCP, Sonasid, ONEE, taxis, aviation, décharges sauvages, réfrigérants, agriculture, BTP, achats)
  - Migration 000006: intensity_denominators, project_intensity_config, rse_scores (BVC RSE-2019 piliers E/S/G),
    AMEE Loi 47-09 project fields, 11 new AMEE factors (GPL, charbon, gaz naturel, vapeur, transport)
  - UI: FR/EN/AR trilingual support across all pages, reporting_frameworks multi-select (8 options),
    17 Morocco sector dropdown, RSE/AMEE 4th tab, GRI 305 KPI display, NDC progress bar
  - UI: ManualFactForm with 29 Morocco-specific categories (butane bouteilles, ONCF, R-22, R-410A, OCP phosphate...)
  - UI: Client creation form with is_listed_bvc, rse_reporting_required, secteur_maroc
  - API: ProjectCreate/Response with reporting_frameworks[], sector_code, language, NDC fields
  - API: ClientCreate/Response with naics_code, secteur_maroc, is_listed_bvc, rse_reporting_required
  - API: RSE endpoints GET/POST /projects/{id}/rse (BVC RSE upsert per year)
  - API: /methodologies endpoint
  - Compute: auto GRI 305 (305-1/2-loc/2-mkt/3) and NDC alignment persisted in snapshots
  - Report: GRI 305 table + NDC alignment table in DOCX
  - Narrative: Morocco-aware prompt (Loi 99-12, 47-09, NDC 2021, SNDD 2030, BVC, ONEE factor)

- [x] Session 3 — continuous improvement loop (commits 460cb4e → 1ab707b):
  - RSE score history table in RSE/AMEE tab (fetched from API, tabular display with EnR%, GHG, social KPIs)
  - Intensity metrics display in RSE tab (from last snapshot's intensity_metrics JSONB)
  - Emissions trend sparkline (SVG polyline, auto-hides when only 1 snapshot)
  - Enhanced ProjectCard: framework color badges, sector code, language chip
  - Clients portfolio section on projects page (BVC/RSE badges, project count per client)
  - Login page: progressive lockout UX (5 attempts → 60s cooldown, attempt counter shown)
  - Project summary API endpoint GET /projects/{id}/summary (facts counts, anomalies, RSE count, last snapshot)
  - Total CO2e display in project detail stats bar (from latest snapshot)
  - GRI 305-4 intensity computation: _compute_intensity_metrics() in compute_svc.py uses project_intensity_config
  - Intensity denominator API: GET /intensity-denominators, GET/POST /projects/{id}/intensity-config
  - Intensity config UI: collapsible form in RSE tab, shows configured denominators as pills
  - DOCX report: GRI 305-4 intensity table section (when intensity_metrics present)
  - DOCX report: AMEE Bilan Énergétique section (when amee in reporting_frameworks)
  - Security: validate_path_uuid() helper in deps.py, applied to all new API endpoints
  - Kernel tests: 25/25 pass

## Meta-docs (this branch)
- TODOLIST.md (45a65f1) — full MVP-readiness plan with cost model and locked decisions
- AUDIT.md (45a65f1) — A–Z audit with locked architectural decisions
- Phase 6 minimal UI variant (523e9ed) — kept for the `reviewer_note` API addition; superseded by 62f615b's richer UI on merge

## Deviations from spec
- PostgreSQL run for tests uses portable pg17 at ~/AppData/Local/pg17_portable (no system install).
  Tests connect as 'app_user' (non-superuser) to exercise RLS, matching Supabase 'authenticated' role.
  Teardown uses pg_ctl stop -m fast (Windows-compatible; SIGINT not supported on Win32).
- git push 403 on proxy recovered; all commits through 1ab707b pushed to claude/friendly-gates-m8zhxm.

- [x] TODOLIST Phase 1 — fully-Chinese provider swap (CLAUDE.md §0.11 Moroccan wording,
  STACK docs-processing line, narrative cascade, scan_parser, ingest, deps, tests, .env.example):
  - §0.11 rewritten in MA legal context (Loi 09-08, CNDP, ONEE 2023, residency)
  - OCR: PaddleOCR-VL-1.5 via Aliyun DashScope (DASHSCOPE_API_KEY, OCR_ENGINE=paddleocr_vl_15)
  - Extraction: Qwen3-Plus via OpenRouter, fallback GLM-4-Plus (EXTRACTION_MODEL=qwen/qwen3-plus)
  - Narrative: DeepSeek V3 via OpenRouter, fallback Qwen3-Plus → GLM-4-Plus → Gemini 2.5
    Flash Lite last-resort cost safety net (NARRATIVE_MODEL=deepseek/deepseek-chat-v3)
  - All Anthropic models dropped (no Claude Haiku, no ANTHROPIC_API_KEY)
  - New `parsers/aliyun_dashscope.py`; pyproject swaps `anthropic` → `dashscope`
  - Worker test_report: 17/17 pass; kernel: 25/25; API: 38/1 skip
  - Pre-existing test_ingestion fixture FK error (factor_set_id seed drift) is unrelated

## OPEN QUESTIONS (stop and ask rather than guess on invariants)
- none
