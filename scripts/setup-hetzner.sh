#!/usr/bin/env bash
# One-shot Hetzner CX33 bootstrap. Assumes a fresh Ubuntu 24.04 LTS server
# reachable over SSH as root. Idempotent — safe to re-run.
#
# Usage (from your laptop):
#   HETZNER_HOST=1.2.3.4 ./scripts/setup-hetzner.sh
#
# What it does:
#   - Creates the `adrar` system user (no password, sudo via SSH key)
#   - Installs Docker Engine + Compose v2 + Caddy prerequisites
#   - Configures UFW (allow 22, 80, 443; deny everything else)
#   - Sets up /opt/adrar with the project + .env template
#   - Installs backup cron + logrotate

set -euo pipefail

: "${HETZNER_HOST:?HETZNER_HOST is required (server IP or hostname)}"
SSH_TARGET="root@${HETZNER_HOST}"

ssh_run() { ssh -o StrictHostKeyChecking=accept-new "${SSH_TARGET}" "$@"; }

ssh_run <<'REMOTE'
set -euo pipefail

# 1. System user
if ! id adrar &>/dev/null; then
    adduser --disabled-password --gecos "" adrar
    mkdir -p /home/adrar/.ssh
    cp /root/.ssh/authorized_keys /home/adrar/.ssh/ 2>/dev/null || true
    chown -R adrar:adrar /home/adrar/.ssh
    chmod 700 /home/adrar/.ssh
fi

# 2. Docker
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker adrar
fi

# 3. Compose v2 (Docker CLI plugin)
if ! docker compose version &>/dev/null; then
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -fsSL "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# 4. GPG + rsync + sftp for backups
apt-get install -y --no-install-recommends gpg rsync openssh-client

# 5. UFW
if ! ufw status | grep -q "Status: active"; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
fi

# 6. App directory
mkdir -p /opt/adrar
chown adrar:adrar /opt/adrar

# 7. Backup cron
cat > /etc/cron.d/adrar-backup <<'CRON'
0 3 * * * adrar /opt/adrar/scripts/backup.sh >> /var/log/adrar-backup.log 2>&1
CRON
chmod 644 /etc/cron.d/adrar-backup

# 8. Logrotate
cat > /etc/logrotate.d/adrar <<'LOGROTATE'
/var/log/adrar-*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
LOGROTATE

echo "Hetzner CX33 bootstrap complete."
REMOTE

echo
echo "Next steps:"
echo "  1. scp -r . adrar@${HETZNER_HOST}:/opt/adrar/"
echo "  2. ssh adrar@${HETZNER_HOST} 'cd /opt/adrar && cp .env.example .env && vi .env'"
echo "  3. ssh adrar@${HETZNER_HOST} 'cd /opt/adrar && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d'"
echo "  4. ./scripts/healthcheck.sh  (set API_URL/WEB_URL to your prod domains)"
