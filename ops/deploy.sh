#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Checkfunnel deploy — invoked over SSH by .github/workflows/deploy.yml
#
# Pipeline:
#   1. Acquire a lock to prevent concurrent deploys
#   2. Snapshot the current git commit (for rollback)
#   3. Run the backup script — pre-deploy safety net
#   4. git fetch + git checkout origin/main
#   5. python manage.py migrate --check (dry-run) → fail fast on bad migrations
#   6. python manage.py migrate
#   7. systemctl restart checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat
#   8. Poll /health/ for up to 30s
#   9. On any failure → git reset --hard <previous>, restart services, exit 1
#
# Exit codes:
#   0  success
#   1  failed and rolled back
#   2  failed before any change was made (lock held / backup failed)
# ─────────────────────────────────────────────────────────────────────────────
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/var/www/checkfunnel}"
LOCK_FILE="/tmp/checkfunnel-deploy.lock"
# Hit the public URL through nginx — Django enforces SECURE_SSL_REDIRECT and
# ALLOWED_HOSTS, so localhost:8000 over plain HTTP gets 301'd / 400'd. Going
# through nginx on the same VPS also validates the proxy path is up.
HEALTH_URL="${HEALTH_URL:-https://ai.checkfunnels.com/api/health/}"
SERVICES="checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts)] $*"; }

# ─── Lock ─────────────────────────────────────────────────────────────────────
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    log "ERROR: Another deploy is already in progress (lock $LOCK_FILE held)."
    exit 2
fi

cd "$PROJECT_ROOT"

PREVIOUS_COMMIT="$(git rev-parse HEAD)"
log "Deploy starting (currently at $PREVIOUS_COMMIT)"

# ─── Pre-deploy backup ────────────────────────────────────────────────────────
log "Running pre-deploy backup..."
if /usr/local/bin/checkfunnel-backup.sh > /tmp/checkfunnel-deploy-backup.log 2>&1; then
    log "✔ Backup OK"
else
    log "ERROR: Backup failed — aborting deploy. See /tmp/checkfunnel-deploy-backup.log"
    exit 2
fi

# ─── Pull new code ────────────────────────────────────────────────────────────
log "Fetching origin..."
git fetch origin main
TARGET_COMMIT="$(git rev-parse origin/main)"
if [[ "$TARGET_COMMIT" == "$PREVIOUS_COMMIT" ]]; then
    log "Already at origin/main ($TARGET_COMMIT). Nothing to deploy."
    exit 0
fi
log "Deploying $PREVIOUS_COMMIT → $TARGET_COMMIT"
git reset --hard "$TARGET_COMMIT"

# ─── Rollback helper ──────────────────────────────────────────────────────────
rollback() {
    local reason="$1"
    log "ROLLBACK: $reason"
    git reset --hard "$PREVIOUS_COMMIT"
    systemctl restart $SERVICES || true
    log "Rolled back to $PREVIOUS_COMMIT and restarted services."
    exit 1
}

trap 'rollback "Unexpected error at $(ts)"' ERR

# ─── Migrations ───────────────────────────────────────────────────────────────
# Activate venv for management commands
# shellcheck disable=SC1091
source "$PROJECT_ROOT/venv/bin/activate"

log "Checking migrations..."
if ! python manage.py migrate --check >/dev/null 2>&1; then
    log "Unapplied migrations detected — applying..."
    if ! python manage.py migrate --noinput; then
        rollback "Migration failed"
    fi
    log "✔ Migrations applied"
else
    log "✔ Migrations already up to date"
fi

# Collect static if needed (no-op when collectstatic isn't configured)
python manage.py collectstatic --noinput >/dev/null 2>&1 || true

# ─── Restart services ─────────────────────────────────────────────────────────
log "Restarting services..."
systemctl restart $SERVICES

# ─── Health check ─────────────────────────────────────────────────────────────
log "Waiting for /health/ to come up..."
HEALTH_OK=false
for i in {1..15}; do
    sleep 2
    if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
        HEALTH_OK=true
        log "✔ Health check passed (after ${i}x2s)"
        break
    fi
done

if [[ "$HEALTH_OK" != true ]]; then
    rollback "Health check did not return 200 within 30s"
fi

# Disable error trap — we're past the rollback window
trap - ERR

log "Deploy OK — now at $TARGET_COMMIT"
exit 0
