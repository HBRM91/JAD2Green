#!/usr/bin/env bash
# Post-deploy smoke test. Runs from the Hetzner CX33 host (or any node that
# can reach the api + web public URLs).
#
# Exits 0 if every check passes; non-zero on the first failure. Designed to
# be called by cron (every 5 min) AND by humans right after deploy.

set -euo pipefail

API="${API_URL:-https://api.yourdomain.com}"
WEB="${WEB_URL:-https://app.yourdomain.com}"
ALLOW_HEADERS=("-H" "Accept: application/json")

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
fail()  { red "FAIL: $*"; exit 1; }
ok()    { green "OK:   $*"; }

check_http() {
    local label="$1" url="$2" expected="$3"
    local code
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 -L "${ALLOW_HEADERS[@]}" "${url}" || echo "000")
    if [[ "${code}" =~ ^(${expected})$ ]]; then
        ok "${label} → ${code}"
    else
        fail "${label} → ${code} (expected ${expected}) at ${url}"
    fi
}

# 1. TLS reachable
check_http "api TLS" "${API}/health" "200"
check_http "web TLS" "${WEB}/" "200|307|308"

# 2. Security headers present
for url in "${API}/health" "${WEB}/"; do
    hdrs=$(curl -sS -I --max-time 10 "${url}")
    grep -qi 'Strict-Transport-Security' <<<"${hdrs}" || fail "missing HSTS at ${url}"
    grep -qi 'X-Content-Type-Options: nosniff' <<<"${hdrs}" || fail "missing X-Content-Type-Options at ${url}"
    grep -qi 'X-Frame-Options' <<<"${hdrs}" || fail "missing X-Frame-Options at ${url}"
done
ok "security headers present"

# 3. No-finalize invariant: these paths must not exist (404 or 405, never 200)
for path in finalize approve submit; do
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 -X POST \
        "${API}/projects/00000000-0000-0000-0000-000000000000/${path}" || echo "000")
    if [[ "${code}" =~ ^(404|405)$ ]]; then
        ok "no-${path} (${code})"
    else
        fail "${path} returned ${code} — endpoint exists!"
    fi
done

# 4. API responds to unauthenticated /factor-sets with 401 (RLS + JWT required)
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "${API}/factor-sets" || echo "000")
if [[ "${code}" == "401" ]]; then
    ok "API requires auth (401)"
else
    fail "/factor-sets returned ${code} without auth (expected 401)"
fi

# 5. Worker heartbeat: probe Redis directly
if command -v redis-cli &>/dev/null; then
    redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" PING | grep -q PONG \
        && ok "redis reachable" \
        || fail "redis not reachable"
fi

echo
green "smoke test passed"
