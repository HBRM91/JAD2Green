# PROGRESS

## Current phase: 3
## Next phase: 4

## Done
- [x] Phase 0 — scaffold + control files (commit: ff9bb2f)
- [x] Phase 1 — schema + RLS + seed (commit: 5236c43)
- [x] Phase 2 — kernel (commit: 169bcbd)
- [ ] Phase 3 — api
- [ ] Phase 4 — ingestion
- [ ] Phase 5 — report + delivery
- [ ] Phase 6 — ui
- [ ] Phase 7 — hardening
- [ ] Phase 8 — CBAM (deferred)

## Deviations from spec
- PostgreSQL run for tests uses portable pg17 at ~/AppData/Local/pg17_portable (no system install).
  Tests connect as 'app_user' (non-superuser) to exercise RLS, matching Supabase 'authenticated' role.
  Teardown uses pg_ctl stop -m fast (Windows-compatible; SIGINT not supported on Win32).

## OPEN QUESTIONS (stop and ask rather than guess on invariants)
- none
