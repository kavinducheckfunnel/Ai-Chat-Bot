"""
Filesystem helpers for the super-admin Backups page.

Backups live on disk at /var/backups/checkfunnel/ in three tiers:
    daily/<YYYY-MM-DD>/     ← every cron run lands here
    weekly/<YYYY-MM-DD>/    ← Sundays hard-linked from daily/
    monthly/<YYYY-MM-DD>/   ← 1st of month hard-linked from daily/

Each snapshot contains a fixed set of files written by ops/backup.sh:
    db.dump            postgres custom-format dump
    project.tar.gz     project tree
    env.tar.gz         .env files (sensitive — UI requires extra confirm)
    systemd.tar.gz     /etc/systemd/system/checkfunnel-*.service
    nginx.tar.gz       /etc/nginx/sites-*/checkfunnel*
    media.tar.gz       optional, only if /var/www/checkfunnel/media exists
    MANIFEST.txt       sha256s, sizes, git commit, hostname

This module returns sanitized dicts ready for JSON serialization and
strictly validates any user-supplied path components against allowlists
before touching the filesystem. The download endpoint relies on this
module to never return a path outside BACKUP_ROOT.
"""
import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Path the cron writes to. Configurable via env so tests can point elsewhere.
BACKUP_ROOT = Path(os.environ.get('BACKUP_ROOT', '/var/backups/checkfunnel'))

ALLOWED_TIERS = {'daily', 'weekly', 'monthly'}

# Only these filenames can be served. Anything else 404s. Critical guardrail:
# prevents an attacker (or a bug) from streaming arbitrary files via
# /api/admin/backups/<tier>/<date>/<file>/.
ALLOWED_FILES = {
    'db.dump',
    'project.tar.gz',
    'env.tar.gz',
    'systemd.tar.gz',
    'nginx.tar.gz',
    'media.tar.gz',
    'MANIFEST.txt',
}

# env.tar.gz contains API keys + DB password. The UI gates this with a
# type-the-date confirm modal but we also mark it server-side for audit.
SENSITIVE_FILES = {'env.tar.gz'}

# Tier+date must match exact shapes so we can't be tricked by ../ or weird
# unicode tricks before os.path.realpath check.
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _safe_snapshot_dir(tier, date):
    """
    Resolve <tier>/<date> to an absolute path inside BACKUP_ROOT.
    Returns Path or None. None means: bad tier, bad date, traversal attempt,
    or the snapshot doesn't exist.
    """
    if tier not in ALLOWED_TIERS:
        return None
    if not _DATE_RE.match(date or ''):
        return None
    candidate = (BACKUP_ROOT / tier / date).resolve()
    root_resolved = BACKUP_ROOT.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        # Traversal attempt — path escaped BACKUP_ROOT
        logger.warning(f'[backup_admin] Path traversal blocked: {tier}/{date}')
        return None
    if not candidate.is_dir():
        return None
    return candidate


def _safe_file_in_snapshot(tier, date, filename):
    """Resolve <tier>/<date>/<filename> with double validation."""
    if filename not in ALLOWED_FILES:
        return None
    snap = _safe_snapshot_dir(tier, date)
    if not snap:
        return None
    target = (snap / filename).resolve()
    try:
        target.relative_to(snap)
    except ValueError:
        return None
    if not target.is_file():
        return None
    return target


def _parse_manifest(snap_dir):
    """
    Read MANIFEST.txt into a dict of:
      { 'timestamp_utc': ..., 'git_commit': ..., 'hostname': ...,
        'files': { 'db.dump': {'sha256': ..., 'size': int}, ... } }
    """
    manifest_path = snap_dir / 'MANIFEST.txt'
    if not manifest_path.is_file():
        return {}

    info = {'files': {}}
    try:
        with manifest_path.open() as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Header lines: "key: value"
                if ': ' in line and not line[0].isdigit() and len(line.split()) <= 3:
                    key, _, value = line.partition(': ')
                    info[key.strip()] = value.strip()
                    continue
                # File lines: "<sha256>  <size_bytes>  <filename>"
                parts = line.split()
                if len(parts) == 3 and len(parts[0]) == 64:
                    sha, size, name = parts
                    try:
                        info['files'][name] = {'sha256': sha, 'size': int(size)}
                    except ValueError:
                        pass
    except Exception as e:
        logger.warning(f'[backup_admin] Manifest parse failed for {snap_dir}: {e}')
    return info


def _snapshot_summary(tier, date, snap_dir):
    """Build the JSON shape returned by list_backups for one snapshot."""
    manifest = _parse_manifest(snap_dir)
    files = []
    total_size = 0
    for fname in sorted(ALLOWED_FILES):
        p = snap_dir / fname
        if not p.is_file():
            continue
        size = p.stat().st_size
        total_size += size
        files.append({
            'name': fname,
            'size': size,
            'sha256': manifest.get('files', {}).get(fname, {}).get('sha256', ''),
            'is_sensitive': fname in SENSITIVE_FILES,
        })
    return {
        'tier': tier,
        'date': date,
        'total_size': total_size,
        'git_commit': manifest.get('git_commit', ''),
        'timestamp_utc': manifest.get('timestamp_utc', ''),
        'files': files,
    }


def list_all_backups():
    """Enumerate every snapshot across all three tiers, newest first per tier."""
    if not BACKUP_ROOT.exists():
        return {'daily': [], 'weekly': [], 'monthly': []}

    result = {}
    for tier in ('daily', 'weekly', 'monthly'):
        tier_dir = BACKUP_ROOT / tier
        if not tier_dir.is_dir():
            result[tier] = []
            continue
        snaps = []
        for child in sorted(tier_dir.iterdir(), reverse=True):  # newest first
            if not child.is_dir() or not _DATE_RE.match(child.name):
                continue
            snaps.append(_snapshot_summary(tier, child.name, child))
        result[tier] = snaps
    return result


def backup_status():
    """Top-of-page status strip: latest run, total disk usage, tier counts."""
    counts = {'daily': 0, 'weekly': 0, 'monthly': 0}
    latest_date = None
    latest_size = 0
    total_disk = 0

    for tier in counts:
        tier_dir = BACKUP_ROOT / tier
        if not tier_dir.is_dir():
            continue
        for child in tier_dir.iterdir():
            if not child.is_dir() or not _DATE_RE.match(child.name):
                continue
            counts[tier] += 1
            snap_size = sum(p.stat().st_size for p in child.iterdir() if p.is_file())
            total_disk += snap_size
            # Track latest from daily tier only (most recent point-in-time)
            if tier == 'daily' and (latest_date is None or child.name > latest_date):
                latest_date = child.name
                latest_size = snap_size

    # Read tail of the backup log for the last cron exit status
    last_log_line = ''
    last_log_path = '/var/log/checkfunnel-backup.log'
    try:
        if os.path.isfile(last_log_path):
            with open(last_log_path, 'rb') as f:
                # Seek near end (cheap "tail")
                f.seek(0, 2)
                end = f.tell()
                f.seek(max(0, end - 2048))
                tail = f.read().decode('utf-8', 'replace')
            for line in reversed(tail.splitlines()):
                if line.strip():
                    last_log_line = line.strip()
                    break
    except Exception:
        pass

    return {
        'counts': counts,
        'latest_date': latest_date,
        'latest_size': latest_size,
        'total_disk_bytes': total_disk,
        'backup_root': str(BACKUP_ROOT),
        'last_log_tail': last_log_line,
    }


def snapshot_dir_size(snap_dir):
    """Total bytes occupied by a snapshot directory (top-level files only)."""
    return sum(p.stat().st_size for p in snap_dir.iterdir() if p.is_file())
