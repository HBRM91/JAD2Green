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
- [x] Phase 6 — ui (commit: 62f615b)
- [x] Phase 7 — hardening (commit: eaf807f)
- [x] Security hardening pass — JWT/UUID validation, magic bytes, CORS, body limit, MIME allowlist (commit: 0a2c039)
- [x] UI brand polish — JAD2 Advisory navy design, FR/EN toggle on all pages, metrics bar, login stats (commit: 333c264)

## Deviations from spec
- PostgreSQL run for tests uses portable pg17 at ~/AppData/Local/pg17_portable (no system install).
  Tests connect as 'app_user' (non-superuser) to exercise RLS, matching Supabase 'authenticated' role.
  Teardown uses pg_ctl stop -m fast (Windows-compatible; SIGINT not supported on Win32).
- git push 403 on proxy recovered; all commits through 333c264 pushed to claude/friendly-gates-m8zhxm.

## OPEN QUESTIONS (stop and ask rather than guess on invariants)
- none
