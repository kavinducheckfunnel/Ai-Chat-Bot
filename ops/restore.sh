#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Checkfunnel restore — pairs with backup.sh
#
# Usage:
#   checkfunnel-restore.sh <tier>/<YYYY-MM-DD>          (e.g. daily/2026-05-20)
#   checkfunnel-restore.sh latest                       (most recent daily)
#   checkfunnel-restore.sh list                         (show what's available)
#
# What it does:
#   1. Confirms the choice with the operator (this WIPES the live DB)
#   2. Stops daphne/celery/celerybeat
#   3. Drops and recreates the database
#   4. pg_restores from db.dump
#   5. Restores env / systemd / nginx files IF the operator asks
#   6. Restarts services
#   7. Hits /health/ to verify
#
# Project code is NOT auto-restored — that's `git checkout <commit>` from the
# manifest. Avoids accidentally overwriting in-flight changes.
# ─────────────────────────────────────────────────────────────────────────────
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/var/www/checkfunnel}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/checkfunnel}"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi
export PGHOST="${POSTGRES_HOST:-localhost}"
export PGPORT="${POSTGRES_PORT:-5432}"
export PGUSER="${POSTGRES_USER:-checkfunnel_user}"
export PGPASSWORD="${POSTGRES_PASSWORD:-}"
DB_NAME="${POSTGRES_DB:-checkfunnel_db}"

usage() {
    cat <<EOF
Usage: $(basename "$0") <selector>

Selectors:
  daily/YYYY-MM-DD     restore from that daily backup
  weekly/YYYY-MM-DD    restore from that weekly snapshot
  monthly/YYYY-MM-DD   restore from that monthly snapshot
  latest               most recent daily
  list                 list available backups

Env (optional):
  PROJECT_ROOT (default $PROJECT_ROOT)
  BACKUP_ROOT  (default $BACKUP_ROOT)
EOF
}

list_backups() {
    for tier in daily weekly monthly; do
        local dir="$BACKUP_ROOT/$tier"
        [[ -d "$dir" ]] || continue
        echo "── $tier ──"
        for d in $(ls -1 "$dir" 2>/dev/null | sort); do
            local size
            size=$(du -sh "$dir/$d" 2>/dev/null | cut -f1)
            local commit
            commit=$(awk -F': *' '/^git_commit:/{print $2; exit}' "$dir/$d/MANIFEST.txt" 2>/dev/null || echo '?')
            printf '  %-30s  %5s  git=%s\n' "$tier/$d" "$size" "$commit"
        done
    done
}

if [[ $# -lt 1 ]]; then usage; exit 2; fi

SELECTOR="$1"
case "$SELECTOR" in
    -h|--help|help) usage; exit 0 ;;
    list)           list_backups; exit 0 ;;
    latest)
        SELECTOR="daily/$(ls -1 "$BACKUP_ROOT/daily" 2>/dev/null | sort | tail -1)"
        if [[ "$SELECTOR" == "daily/" ]]; then
            echo "No daily backups found in $BACKUP_ROOT/daily"
            exit 1
        fi
        ;;
esac

SRC="$BACKUP_ROOT/$SELECTOR"
if [[ ! -d "$SRC" ]] || [[ ! -f "$SRC/db.dump" ]]; then
    echo "Backup not found or incomplete: $SRC"
    list_backups
    exit 1
fi

echo "About to restore from: $SRC"
if [[ -f "$SRC/MANIFEST.txt" ]]; then
    grep -E '^(timestamp_utc|git_commit|db_name|hostname)' "$SRC/MANIFEST.txt"
fi
echo ""
echo "This will DROP and recreate database '$DB_NAME'. Service downtime ~30s."
read -r -p "Type 'yes' to proceed: " CONFIRM
[[ "$CONFIRM" == "yes" ]] || { echo "Aborted."; exit 1; }

echo "Stopping services..."
systemctl stop checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat 2>/dev/null || true

echo "Dropping database $DB_NAME..."
psql -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -d postgres -c "CREATE DATABASE $DB_NAME OWNER $PGUSER;"

echo "Restoring db.dump (this can take a while)..."
pg_restore --no-owner --no-acl --jobs=4 --dbname="$DB_NAME" "$SRC/db.dump"

# Optional file restores — prompt for each
restore_if_yes() {
    local tar="$1" prompt="$2"
    [[ -f "$tar" ]] || return 0
    read -r -p "$prompt [y/N]: " ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        tar -xzf "$tar" -C /
        echo "  restored $tar"
    fi
}
restore_if_yes "$SRC/env.tar.gz"     "Restore env files (.env)?"
restore_if_yes "$SRC/systemd.tar.gz" "Restore systemd units?"
restore_if_yes "$SRC/nginx.tar.gz"   "Restore nginx config?"
restore_if_yes "$SRC/media.tar.gz"   "Restore media uploads?"

echo "Reloading systemd + restarting services..."
systemctl daemon-reload
systemctl start checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat

sleep 4
echo "Health check..."
if curl -fsS http://localhost:8000/health/ >/dev/null 2>&1; then
    echo "✔ /health/ is OK"
else
    echo "⚠ /health/ did not respond OK — check journalctl -u checkfunnel-daphne"
fi

echo ""
echo "Restore complete from $SRC."
if [[ -f "$SRC/MANIFEST.txt" ]]; then
    COMMIT=$(awk -F': *' '/^git_commit:/{print $2; exit}' "$SRC/MANIFEST.txt")
    echo ""
    echo "Backup was at git commit $COMMIT."
    echo "If you need to also roll the code back, run:"
    echo "  cd $PROJECT_ROOT && git fetch && git checkout $COMMIT"
fi
