#!/usr/bin/env bash
# Restore a Supabase Postgres backup from Hetzner Storage Box.
# DR drill: run against a fresh disposable database to verify backup integrity.
#
# Usage:
#   ./restore.sh <remote-filename> [target_database_url]
# Example:
#   ./restore.sh adrar-20260629T030000Z.sql.gz.gpg \
#       "postgresql://postgres:...@db.<project>.supabase.co:5432/postgres"
#
# DANGER: psql restore is destructive. The target database is dropped + recreated
# unless RESTORE_PRESERVE=1 is set (then we restore in place without DROP).

set -euo pipefail

: "${BACKUP_PASSPHRASE:?BACKUP_PASSPHRASE is required}"
: "${STORAGE_BOX_USER:?STORAGE_BOX_USER is required}"
: "${STORAGE_BOX_HOST:?STORAGE_BOX_HOST is required}"

REMOTE_FILE="${1:?usage: restore.sh <remote-filename> [target_database_url]}"
TARGET_URL="${2:-${DATABASE_URL:-}}"
: "${TARGET_URL:?target database URL is required (as 2nd arg or DATABASE_URL env)}"
WORK="/tmp/restore-$$"
mkdir -p "${WORK}"
trap 'rm -rf "${WORK}"' EXIT

log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "downloading ${REMOTE_FILE}"
sftp -o StrictHostKeyChecking=accept-new -P 23 \
    "${STORAGE_BOX_USER}@${STORAGE_BOX_HOST}" <<EOF
get ${REMOTE_FILE} ${WORK}/${REMOTE_FILE}
bye
EOF

log "decrypting + decompressing"
gpg --batch --yes --decrypt --passphrase "${BACKUP_PASSPHRASE}" \
    --output "${WORK}/dump.sql.gz" "${WORK}/${REMOTE_FILE}"
gunzip "${WORK}/dump.sql.gz"

SIZE=$(stat -c '%s' "${WORK}/dump.sql")
log "decrypted dump: ${SIZE} bytes"

if [[ "${RESTORE_PRESERVE:-0}" != "1" ]]; then
    log "DESTRUCTIVE: dropping + recreating target database"
    psql "${TARGET_URL}" -c "DROP DATABASE IF EXISTS postgres WITH (FORCE);" || true
    psql "${TARGET_URL}" -c "CREATE DATABASE postgres;"
fi

log "restoring into target"
psql "${TARGET_URL}" --single-transaction --variable=ON_ERROR_STOP=1 \
    -f "${WORK}/dump.sql"

log "restore complete"
