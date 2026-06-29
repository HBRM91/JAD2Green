#!/usr/bin/env bash
# Daily encrypted backup of the Supabase Postgres database to Hetzner Storage Box.
# Run via cron on the Hetzner CX33 host.
#
# Schedule (root crontab):
#   0 3 * * * /opt/adrar/scripts/backup.sh >> /var/log/adrar-backup.log 2>&1
#
# Env: BACKUP_PASSPHRASE, STORAGE_BOX_USER, STORAGE_BOX_HOST, DATABASE_URL,
# RETENTION_DAYS (default 30).

set -euo pipefail

: "${BACKUP_PASSPHRASE:?BACKUP_PASSPHRASE is required (gpg symmetric key)}"
: "${STORAGE_BOX_USER:?STORAGE_BOX_USER is required (e.g. u123456)}"
: "${STORAGE_BOX_HOST:?STORAGE_BOX_HOST is required (e.g. u123456.your-storagebox.de)}"
: "${DATABASE_URL:?DATABASE_URL is required (Supabase direct connection, NOT pooler)}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="adrar-${TS}.sql.gz.gpg"
LOCAL="/tmp/${NAME}"
REMOTE_DIR="/backups/postgres"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "starting backup: ${NAME}"

# 1. Dump, gzip, encrypt in one pipeline. --no-owner --no-privileges for portability.
pg_dump \
    --dbname="${DATABASE_URL}" \
    --no-owner \
    --no-privileges \
    --format=plain \
    --quote-all-identifiers \
    | gzip -9 \
    | gpg --batch --yes --symmetric --cipher-algo AES256 --compress-algo none \
          --passphrase "${BACKUP_PASSPHRASE}" \
          --output "${LOCAL}"

SIZE=$(stat -c '%s' "${LOCAL}")
log "local backup size: ${SIZE} bytes"

# 2. Upload via sftp to Hetzner Storage Box. sshpass piped password for non-interactive cron.
#    Storage Box accepts sftp on port 23 by default; check your control panel.
export SSHPASS="${STORAGE_BOX_PASSWORD:-}"
if [[ -n "${SSHPASS}" ]]; then
    sshpass -e sftp -o StrictHostKeyChecking=accept-new -P 23 \
        "${STORAGE_BOX_USER}@${STORAGE_BOX_HOST}" <<EOF
mkdir ${REMOTE_DIR}
put ${LOCAL} ${REMOTE_DIR}/${NAME}
bye
EOF
else
    # Passwordless via ssh key
    sftp -o StrictHostKeyChecking=accept-new -P 23 \
        "${STORAGE_BOX_USER}@${STORAGE_BOX_HOST}" <<EOF
mkdir ${REMOTE_DIR}
put ${LOCAL} ${REMOTE_DIR}/${NAME}
bye
EOF
fi

# 3. Retention: delete remote backups older than RETENTION_DAYS.
CUTOFF=$(date -u -d "-${RETENTION_DAYS} days" +%Y%m%d 2>/dev/null || \
         date -u -v-"${RETENTION_DAYS}"d +%Y%m%d)
log "pruning remote backups older than ${CUTOFF}"
sftp -o StrictHostKeyChecking=accept-new -P 23 \
    "${STORAGE_BOX_USER}@${STORAGE_BOX_HOST}" <<EOF
cd ${REMOTE_DIR}
-rm adrar-${CUTOFF}*.sql.gz.gpg
ls -1
bye
EOF

rm -f "${LOCAL}"
log "backup complete: ${NAME}"
