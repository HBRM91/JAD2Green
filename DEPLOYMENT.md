# DEPLOYMENT.md — Hetzner CX33 runbook

Target: single Hetzner CX33 (8 vCPU / 16 GB / ~€15/mo) hosting api + web + worker
+ redis + Caddy. Postgres on Supabase. Document storage on Supabase Storage.
Daily encrypted backups to Hetzner Storage Box (~€3.50/mo). Total infra:
**~€20/mo + Supabase Pro (€25/mo)** — comfortably under 1 bureau's break-even.

---

## 0. Prerequisites

- Hetzner Cloud account, CX33 server running Ubuntu 24.04 LTS
- Public IPv4 + IPv6 attached
- Domain (e.g. `adrar.ai`) with DNS access for `api.` and `app.` subdomains
- Supabase project (Pro plan) created in the **eu-west-1** (Ireland) or
  **eu-central-1** (Frankfurt) region for MA-resident MA tenants — verify with
  the tenant's CNDP filing which region applies
- Hetzner Storage Box sub-account (optional, for backup destination)
- Email address for Let's Encrypt registration (`ops@yourdomain.com`)

## 1. First-time server bootstrap

From your laptop:

```bash
HETZNER_HOST=<server-ip> ./scripts/setup-hetzner.sh
```

This installs Docker, UFW, the `adrar` user, the backup cron, and logrotate.

## 2. Deploy the application

```bash
# On your laptop, push the code to the server
scp -r . adrar@${HETZNER_HOST}:/opt/adrar/
ssh adrar@${HETZNER_HOST}

# On the server: configure env
cd /opt/adrar
cp .env.example .env
vi .env   # fill in real values (see §3 below)

# DNS MUST be pointing at the server before first Caddy boot:
dig +short api.yourdomain.com
dig +short app.yourdomain.com
# Both should return the Hetzner public IP

# Build + start
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull   # if using registry
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify
docker compose ps
docker compose logs --tail=200 caddy
./scripts/healthcheck.sh
```

## 3. Environment variables

See `.env.example` for the full list. The minimum production set:

```bash
ENVIRONMENT=production
ALLOWED_ORIGINS=https://app.yourdomain.com

# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=<anon>
SUPABASE_SERVICE_ROLE_KEY=<service-role>
SUPABASE_JWT_SECRET=<32+ char secret>
DATABASE_URL=postgresql://postgres:<pwd>@db.<project>.supabase.co:5432/postgres

# App secrets (generate with: openssl rand -hex 32)
SECRET_KEY=<64 hex chars>
TOKEN_ENCRYPT_KEY=<64 hex chars>

# Web (NEXT_PUBLIC_* — these end up in the browser bundle)
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon>
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Caddy
API_DOMAIN=api.yourdomain.com
WEB_DOMAIN=app.yourdomain.com
CADDY_EMAIL=ops@yourdomain.com

# LLM / OCR (Phase 1 — Chinese primary, Gemini as safety net)
OPENROUTER_API_KEY=sk-or-...
DASHSCOPE_API_KEY=sk-...
NARRATIVE_MODEL=deepseek/deepseek-chat-v3
EXTRACTION_MODEL=qwen/qwen3-plus
OCR_ENGINE=paddleocr_vl_15
# Optional: GEMINI_API_KEY=...

# Backups
BACKUP_PASSPHRASE=<32+ char passphrase>
STORAGE_BOX_USER=u123456
STORAGE_BOX_HOST=u123456.your-storagebox.de
STORAGE_BOX_PASSWORD=<sftp password, or use ssh key>
```

## 4. Database migrations

The Supabase project must have all migrations applied before the first request.
Two options:

**Option A — via Supabase CLI (recommended):**
```bash
supabase login
supabase link --project-ref <project-id>
supabase db push
```

**Option B — manual via psql:**
```bash
PGPASSWORD=<password> psql "${DATABASE_URL}" \
    -f supabase/migrations/20240101000001_schema.sql \
    -f supabase/migrations/20240101000002_rls.sql \
    -f supabase/migrations/20240101000003_seed.sql \
    -f supabase/migrations/20240101000004_hardening.sql \
    -f supabase/migrations/20240101000005_morocco_enhancement.sql \
    -f supabase/migrations/20240101000006_intensity_rse.sql
```

(Order matters: schema → seed → data migrations, per conftest.py)

## 5. Smoke test after deploy

```bash
# From the server
./scripts/healthcheck.sh

# From your laptop, full happy path
open https://app.yourdomain.com/login
# Sign up with a magic link
# Create a bureau in the DB:
psql "${DATABASE_URL}" -c "INSERT INTO bureaus (id, name, region) VALUES (gen_random_uuid(), 'JAD2 Advisory', 'MA');"
# Create a client, project, upload a PDF, validate a fact, compute, view snapshot
```

## 6. Backups + DR

- **What**: full pg_dump of the Supabase database, gpg-encrypted (AES-256),
  uploaded to Hetzner Storage Box over sftp
- **When**: daily at 03:00 UTC (cron in `/etc/cron.d/adrar-backup`)
- **Retention**: 30 days
- **RPO**: 24h
- **RTO**: ~4h (decrypt + restore is fast; the bottleneck is human decisions)

Verify the first backup manually:

```bash
sudo -u adrar /opt/adrar/scripts/backup.sh
ls -la /tmp/adrar-*.sql.gz.gpg
# Should appear immediately; check Hetzner Storage Box UI to confirm
```

Quarterly DR drill:

```bash
# 1. Provision a throwaway Supabase project
# 2. Run restore.sh against it
./scripts/restore.sh adrar-20260629T030000Z.sql.gz.gpg "postgresql://...:5432/postgres"
# 3. Spot-check: count rows, validate a known snapshot
psql "$RESTORE_URL" -c "SELECT count(*) FROM report_snapshots;"
# 4. Tear down the throwaway project
```

## 7. Updates + rollback

```bash
# Update
ssh adrar@${HETZNER_HOST} 'cd /opt/adrar && git pull && \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml build && \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d'

# Rollback (pin to previous commit)
ssh adrar@${HETZNER_HOST} 'cd /opt/adrar && git checkout <previous-sha> && \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build'
```

The Caddyfile and the database schema are the only two things that can
break a deploy. Caddy validates its config on every reload (zero-downtime);
migrations are forward-only — write a `_down.sql` for any rollback you care
about, or restore from the most recent backup.

## 8. Monitoring

TODO (Phase 7 from TODOLIST): Sentry SDK + structlog JSON logging + deep
`/health` endpoint (DB + Redis + Celery worker count).

Until then, monitor manually:
- `docker compose ps` — services healthy
- `docker compose logs --tail=200 api` — error rate
- `docker compose logs --tail=200 worker` — Celery task failures
- Hetzner Storage Box — backup arrival
- Let's Encrypt — cert expiry (Caddy auto-renews, but watch for rate limits)

## 9. Open items for first paying customer

Per TODOLIST.md, these are P0 and **must be done before** the first customer:

- **Phase 2** — audit log writes (EXTRACT/VALIDATE/COMPUTE/EXPORT) — `audit_log` table
  is empty today, no code writes to it
- **Phase 3** — onboarding + RBAC — no admin invite endpoint, no role enforcement
- **Phase 5** — backup + DR verification (this runbook is the design; the script
  needs a real run on the live Hetzner box)
- **Phase 6** — snapshot share link (read-only public URL for clients)
- **Phase 7** — observability (Sentry + structlog + /health)
- **Phase 8** — docs: `dpa-providers.md` (CNDP filing), `DEPLOYMENT.md` (this file),
  `CHANGELOG.md`, `docs/data-model.md`
- **CNDP DPA** — formal agreement with Aliyun, OpenRouter, Google before any
  production traffic carrying personal data
