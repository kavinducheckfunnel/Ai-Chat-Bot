#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Checkfunnel daily backup
#
# Captures everything needed to fully recover production:
#   • postgres dump (custom binary format — smaller + supports pg_restore -j)
#   • project tree (code + built dist) excluding venv/node_modules/cache
#   • environment files (.env*)
#   • systemd unit files (checkfunnel-*.service)
#   • nginx site config (anything matching checkfunnel*)
#   • media uploads if any
#
# Layout:
#   /var/backups/checkfunnel/
#     daily/YYYY-MM-DD/   ← every run lands here
#     weekly/             ← Sunday's daily is hard-linked here
#     monthly/            ← First of month's daily is hard-linked here
#
# Retention (auto-pruned each run):
#   7 daily, 4 weekly, 6 monthly
#
# Invoked by /etc/cron.d/checkfunnel-backup at 03:00 UTC daily, AND by the
# CI/CD deploy script as a pre-deploy safety net.
# ─────────────────────────────────────────────────────────────────────────────
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/var/www/checkfunnel}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/checkfunnel}"
DAILY_KEEP="${DAILY_KEEP:-7}"
WEEKLY_KEEP="${WEEKLY_KEEP:-4}"
MONTHLY_KEEP="${MONTHLY_KEEP:-6}"

TIMESTAMP="$(date -u +%Y-%m-%d_%H-%M-%S)"
TODAY="$(date -u +%Y-%m-%d)"
DOW="$(date -u +%u)"           # 1..7, where 7=Sunday
DOM="$(date -u +%d)"           # 01..31
GIT_COMMIT="$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"

DAILY_DIR="$BACKUP_ROOT/daily/$TODAY"
LOG_FILE="$BACKUP_ROOT/backup.log"

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"
}

# ─── Source the project's .env so we get POSTGRES_* creds ─────────────────────
# pg_dump reads PG* env vars natively; we map from POSTGRES_* (Django convention)
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

if [[ -z "$PGPASSWORD" ]]; then
    log "ERROR: POSTGRES_PASSWORD is empty — refusing to run blind backup."
    exit 1
fi

# ─── Begin ────────────────────────────────────────────────────────────────────
mkdir -p "$DAILY_DIR" "$BACKUP_ROOT/weekly" "$BACKUP_ROOT/monthly"
log "Starting backup → $DAILY_DIR (git=$GIT_COMMIT)"

cd "$DAILY_DIR"

# 1. Postgres dump (custom binary format — better compression, parallel restore)
log "Dumping database $DB_NAME..."
pg_dump --format=custom --compress=9 --no-owner --no-acl \
    --file="db.dump" "$DB_NAME"
DB_SIZE="$(du -h db.dump | cut -f1)"
log "  ✔ db.dump ($DB_SIZE)"

# 2. Project tree — code + built dist + Vue source. Skip the heavy junk.
log "Archiving project tree..."
tar --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='widget-vue/dist/cache' \
    --exclude='.git' \
    --exclude='staticfiles' \
    -czf project.tar.gz -C "$(dirname "$PROJECT_ROOT")" "$(basename "$PROJECT_ROOT")"
PROJ_SIZE="$(du -h project.tar.gz | cut -f1)"
log "  ✔ project.tar.gz ($PROJ_SIZE)"

# 3. Env files — separate so they can be restored without overwriting code
ENV_PATHS=()
for f in .env .env.production .env.local; do
    [[ -f "$PROJECT_ROOT/$f" ]] && ENV_PATHS+=("$PROJECT_ROOT/$f")
done
if (( ${#ENV_PATHS[@]} > 0 )); then
    tar -czf env.tar.gz -C / $(printf '%s\n' "${ENV_PATHS[@]}" | sed 's|^/||')
    log "  ✔ env.tar.gz"
fi

# 4. systemd units
# Pass absolute paths directly to tar — it strips the leading `/` itself
# (you'll see a benign "Removing leading /" warning). The glob is expanded
# by bash into the array IN A SCOPE WHERE /etc/... resolves, then passed
# verbatim to tar. We can't glob-expand inside `tar -C / etc/...` args
# because bash tries to expand relative to cwd (which is the daily/ dir).
SYSTEMD_FILES=(/etc/systemd/system/checkfunnel-*.service)
if [[ -e "${SYSTEMD_FILES[0]}" ]]; then
    tar -czf systemd.tar.gz --transform='s|^/||' "${SYSTEMD_FILES[@]}"
    log "  ✔ systemd.tar.gz ($(du -h systemd.tar.gz | cut -f1))"
fi

# 5. nginx site config (anything mentioning checkfunnel)
NGINX_FILES=(/etc/nginx/sites-available/*checkfunnel* /etc/nginx/conf.d/*checkfunnel*)
# Bash leaves unexpanded globs literal — filter to real files only.
NGINX_REAL=()
for f in "${NGINX_FILES[@]}"; do
    [[ -f "$f" ]] && NGINX_REAL+=("$f")
done
if (( ${#NGINX_REAL[@]} > 0 )); then
    tar -czf nginx.tar.gz --transform='s|^/||' "${NGINX_REAL[@]}"
    log "  ✔ nginx.tar.gz ($(du -h nginx.tar.gz | cut -f1))"
fi

# 6. Media uploads if present
if [[ -d "$PROJECT_ROOT/media" ]] && [[ -n "$(ls -A "$PROJECT_ROOT/media" 2>/dev/null)" ]]; then
    tar -czf media.tar.gz -C "$PROJECT_ROOT" media
    log "  ✔ media.tar.gz"
fi

# 7. Manifest — sha256, sizes, git commit, hostname
{
    echo "# Checkfunnel backup manifest"
    echo "timestamp_utc:   $TIMESTAMP"
    echo "git_commit:      $GIT_COMMIT"
    echo "hostname:        $(hostname)"
    echo "project_root:    $PROJECT_ROOT"
    echo "db_name:         $DB_NAME"
    echo ""
    echo "# Files (sha256, size, name)"
    for f in db.dump project.tar.gz env.tar.gz systemd.tar.gz nginx.tar.gz media.tar.gz; do
        if [[ -f "$f" ]]; then
            printf '%s  %s  %s\n' \
                "$(sha256sum "$f" | awk '{print $1}')" \
                "$(du -b "$f" | awk '{print $1}')" \
                "$f"
        fi
    done
} > MANIFEST.txt

TOTAL_SIZE="$(du -sh . | cut -f1)"
log "Daily backup complete → $TOTAL_SIZE total"

# ─── Promote to weekly / monthly via hard links ──────────────────────────────
# Hard linking means no extra disk usage but makes pruning independent.
if [[ "$DOW" == "7" ]]; then
    WEEKLY_DIR="$BACKUP_ROOT/weekly/$TODAY"
    if [[ ! -d "$WEEKLY_DIR" ]]; then
        cp -al "$DAILY_DIR" "$WEEKLY_DIR"
        log "Promoted to weekly: $WEEKLY_DIR"
    fi
fi
if [[ "$DOM" == "01" ]]; then
    MONTHLY_DIR="$BACKUP_ROOT/monthly/$TODAY"
    if [[ ! -d "$MONTHLY_DIR" ]]; then
        cp -al "$DAILY_DIR" "$MONTHLY_DIR"
        log "Promoted to monthly: $MONTHLY_DIR"
    fi
fi

# ─── Prune old backups ────────────────────────────────────────────────────────
prune_tier() {
    local tier="$1" keep="$2"
    local dir="$BACKUP_ROOT/$tier"
    [[ -d "$dir" ]] || return 0
    # ls -1 sorts ascending → oldest first; tail removes the newest $keep
    local victims
    victims="$(ls -1 "$dir" 2>/dev/null | sort | head -n "-${keep}" || true)"
    if [[ -n "$victims" ]]; then
        while read -r v; do
            [[ -z "$v" ]] && continue
            rm -rf "$dir/$v"
            log "Pruned $tier/$v"
        done <<< "$victims"
    fi
}

prune_tier daily   "$DAILY_KEEP"
prune_tier weekly  "$WEEKLY_KEEP"
prune_tier monthly "$MONTHLY_KEEP"

log "Backup pipeline finished. Disk usage at $BACKUP_ROOT:"
du -sh "$BACKUP_ROOT"/{daily,weekly,monthly} 2>/dev/null | tee -a "$LOG_FILE" || true

exit 0
