# PROGRESS

## Current phase: 7
## Next phase: 8

## Done
- [x] Phase 0 — scaffold + control files (commit: ff9bb2f)
- [x] Phase 1 — schema + RLS + seed (commit: 5236c43)
- [x] Phase 2 — kernel (commit: 169bcbd)
- [x] Phase 3 — api (commit: 0b5bc7c)
- [x] Phase 4 — ingestion (commit: 8a660f0)
- [x] Phase 5 — report + delivery (commit: 087b57a)
- [x] Phase 6 — consultant workflow UI + reviewer_note API (commit: 523e9ed)
- [ ] Phase 7 — hardening
- [ ] Phase 8 — CBAM (deferred)

## Meta-docs
- TODOLIST.md (45a65f1) — full MVP-readiness plan with cost model
- AUDIT.md (45a65f1) — A–Z audit with locked architectural decisions

## Deviations from spec
- PostgreSQL run for tests uses portable pg17 at ~/AppData/Local/pg17_portable (no system install).
  Tests connect as 'app_user' (non-superuser) to exercise RLS, matching Supabase 'authenticated' role.
  Teardown uses pg_ctl stop -m fast (Windows-compatible; SIGINT not supported on Win32).

## OPEN QUESTIONS (stop and ask rather than guess on invariants)
- none
