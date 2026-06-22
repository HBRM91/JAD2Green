# HANDOVER — Adrar AI Build Continuation

This file lets you resume the build from **any device** (Claude Code mobile app,
web, CLI) or schedule automated phase runs via GitHub Actions / Claude Code cloud.

---

## CURRENT STATE

| Item | Value |
|---|---|
| Next phase | **Phase 6 — Frontend (Next.js consultant UI)** |
| Git branch | `master` |
| Last commit | `2b6c7ca` — Phase 5 done |
| Kernel | ✅ Pure deterministic calc, 25/25 tests |
| API | ✅ FastAPI + JWT + RLS, 23/23 tests |
| Ingestion | ✅ Celery pipeline + dedup + provenance, 12/12 tests |
| Report | ✅ DOCX + charts + AI disclosure + Google gating, 15/15 tests |
| UI | ⬜ Phase 6 — next |
| Hardening | ⬜ Phase 7 |
| CBAM | ⬜ Phase 8 (deferred) |

---

## COPY-PASTE PROMPT (mobile / web / CLI)

Open Claude Code, navigate to the `adrar/` folder, paste this **exactly**:

```
go
```

That's it. The operating protocol in CLAUDE.md does the rest:
it reads CLAUDE.md + BUILD_PLAN.md + PROGRESS.md, executes the current phase,
runs acceptance tests, commits, updates PROGRESS.md, and stops.

---

## WHAT EACH "go" SESSION WILL DO

| Session | Phase | Key output |
|---|---|---|
| Next → | 6 — Frontend UI | Next.js login, validation gate, dashboard, download |
| Then → | 7 — Hardening | Audit log, region pinning, adversarial multi-tenant |
| Then → | 8 — CBAM (on demand) | CBAM module, EU default values |

---

## SETUP FOR NEW MACHINE / FRESH CLONE

```bash
# 1. Clone
git clone https://github.com/<your-org>/JAD2Green.git
cd JAD2Green/adrar

# 2. Python deps (kernel + api + worker)
pip install uv
uv sync   # or: pip install -e packages/kernel -e apps/api -e apps/worker

# 3. Node deps (web UI)
npm install -g pnpm
pnpm install

# 4. Copy env
cp .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_ANON_KEY, DATABASE_URL, ANTHROPIC_API_KEY

# 5. Run migrations against your Supabase project
# (go to Supabase dashboard → SQL Editor → paste each supabase/migrations/*.sql)

# 6. Resume build
claude   # then type: go
```

---

## GITHUB ACTIONS — SCHEDULED PHASE RUNNER

Create `.github/workflows/adrar-build.yml` in the repo root (not in adrar/):

```yaml
name: Adrar AI Phase Build

on:
  workflow_dispatch:          # Manual trigger from GitHub mobile/web
  schedule:
    - cron: '0 9 * * 1'      # Every Monday 09:00 UTC (optional)

jobs:
  build-next-phase:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: |
          pip install uv
          cd adrar && uv pip install -e packages/kernel -e apps/api -e apps/worker

      - name: Run Claude Code — next phase
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          cd adrar
          npx @anthropic-ai/claude-code --print "go" \
            --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
            --no-auto-approve
```

**To trigger from your phone:**
1. Open GitHub mobile app → your repo → Actions tab
2. Select "Adrar AI Phase Build" → "Run workflow"
3. Done — Claude runs the next phase and commits the result

---

## INVARIANTS REMINDER (never violate)

1. Kernel is **pure** — no LLM, no network, no I/O
2. `emissions = activity × factor × gwp` — no uncertainty in totals
3. Extraction writes **proposed** only — validated via UI only
4. **No finalize endpoint** anywhere
5. RLS enforces multi-tenancy at DB — not app code
6. Every request sets `app.bureau_id` GUC before any query
7. Emission factors are effective-dated by year
8. Scope 2 is dual-valued (location + market)
9. Unit conversion is **data** (conversion_factors table), not code
10. Snapshot = immutable, insert-only
11. Raw docs/facts never leave region; only aggregate DOCX exports
12. Every report has AI transparency disclosure block

---

## QUICK STATUS CHECK

```bash
cd adrar
git log --oneline -10
python -m pytest packages/ apps/ -q --tb=no 2>/dev/null
cat PROGRESS.md
```

---

## CONTACTS / REPO

- Repo: `https://github.com/<your-org>/JAD2Green`
- Stack: FastAPI · Next.js 14 · Supabase · Celery · adrar-kernel (pure Python)
- Method: Bilan Carbone® v8 / ADEME Base Carbone
