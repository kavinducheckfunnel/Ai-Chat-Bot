<template>
  <div class="bk-page">
    <!-- ── Header strip ──────────────────────────────────────────── -->
    <div class="bk-header">
      <div>
        <h1 class="bk-title">Backups</h1>
        <p class="bk-sub">
          Daily snapshots of database, code, env, and infra config.
          Restore via SSH: <code>checkfunnel-restore.sh &lt;tier&gt;/&lt;date&gt;</code>
        </p>
      </div>
      <button class="trigger-btn" :disabled="triggering || status?.last_run_in_progress" @click="onTriggerBackup">
        <span v-if="triggering || running" class="dot pulse"></span>
        <svg v-else width="14" height="14" fill="none" viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        {{ running ? 'Running…' : 'Trigger backup now' }}
      </button>
    </div>

    <!-- ── Warning banner (sensitivity) ─────────────────────────── -->
    <div class="warn-banner">
      <svg width="16" height="16" fill="none" viewBox="0 0 24 24">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="12" y1="17" x2="12.01" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span>
        These archives contain the full database dump and platform API keys.
        Anyone with the files can impersonate the platform — handle with care.
      </span>
    </div>

    <!-- ── Status row ──────────────────────────────────────────── -->
    <div v-if="status" class="stat-row">
      <div class="stat-card">
        <p class="stat-label">Latest snapshot</p>
        <p class="stat-value">{{ status.latest_date || '—' }}</p>
        <p class="stat-sub" v-if="status.latest_date">{{ relativeFromDate(status.latest_date) }}</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Total disk</p>
        <p class="stat-value">{{ formatBytes(status.total_disk_bytes) }}</p>
        <p class="stat-sub">across all tiers</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Daily</p>
        <p class="stat-value">{{ status.counts.daily }}<span class="stat-of">/7</span></p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Weekly</p>
        <p class="stat-value">{{ status.counts.weekly }}<span class="stat-of">/4</span></p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Monthly</p>
        <p class="stat-value">{{ status.counts.monthly }}<span class="stat-of">/6</span></p>
      </div>
    </div>

    <!-- ── Tier tabs ───────────────────────────────────────────── -->
    <div class="tier-tabs">
      <button
        v-for="t in tiers" :key="t.key"
        class="tier-tab" :class="{ active: activeTier === t.key }"
        @click="activeTier = t.key"
      >
        {{ t.label }}
        <span class="tier-count">{{ (backups?.[t.key]?.length) || 0 }}</span>
      </button>
    </div>

    <div v-if="loading" class="bk-loading"><div class="bk-spinner"></div></div>

    <div v-else-if="!currentSnapshots.length" class="bk-empty">
      No snapshots in this tier yet.
    </div>

    <!-- ── Snapshot list ──────────────────────────────────────── -->
    <div v-else class="snap-list">
      <div v-for="snap in currentSnapshots" :key="snap.date" class="snap-card">
        <button class="snap-head" @click="toggleExpanded(snap.date)">
          <span class="snap-icon">📦</span>
          <span class="snap-date">{{ snap.date }}</span>
          <span class="snap-size">{{ formatBytes(snap.total_size) }}</span>
          <span class="snap-git" v-if="snap.git_commit">git={{ snap.git_commit }}</span>
          <span class="snap-rel">{{ relativeFromDate(snap.date) }}</span>
          <svg class="snap-chev" :class="{ open: expanded[snap.date] }" width="14" height="14" fill="none" viewBox="0 0 24 24">
            <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>

        <div v-show="expanded[snap.date]" class="snap-files">
          <div v-for="f in snap.files" :key="f.name" class="file-row" :class="{ 'file-sensitive': f.is_sensitive }">
            <span class="file-name">{{ f.name }}</span>
            <span class="file-size">{{ formatBytes(f.size) }}</span>
            <span class="file-sha" :title="f.sha256">{{ f.sha256 ? f.sha256.slice(0, 12) + '…' : '—' }}</span>
            <span v-if="f.is_sensitive" class="file-warn-pill">⚠ contains secrets</span>
            <button class="file-dl" :disabled="downloadingKey === snap.date + ':' + f.name" @click="onDownload(snap, f)">
              <span v-if="downloadingKey === snap.date + ':' + f.name" class="dot pulse"></span>
              <svg v-else width="13" height="13" fill="none" viewBox="0 0 24 24">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Download
            </button>
          </div>

          <div class="snap-actions">
            <button class="delete-btn" @click="askDelete(snap)" :disabled="isMostRecent(snap)">
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              Delete snapshot
            </button>
            <span v-if="isMostRecent(snap)" class="snap-locked-hint">most recent — protected</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Sensitive-file confirm modal ───────────────────────── -->
    <div v-if="confirmSensitive.show" class="modal-overlay" @click.self="closeSensitive">
      <div class="modal-card">
        <div class="modal-head">
          <span class="modal-icon-warn">⚠</span>
          <h3>Download sensitive file</h3>
        </div>
        <p class="modal-body">
          <strong>{{ confirmSensitive.file?.name }}</strong> contains API keys, the
          database password, and other secrets. Type the snapshot date
          <code>{{ confirmSensitive.snap?.date }}</code> below to confirm.
        </p>
        <input
          ref="sensitiveInput"
          v-model="confirmSensitive.typed"
          class="modal-input"
          :placeholder="confirmSensitive.snap?.date"
          @keydown.enter="proceedSensitive"
        />
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeSensitive">Cancel</button>
          <button
            class="btn-danger"
            :disabled="confirmSensitive.typed !== confirmSensitive.snap?.date"
            @click="proceedSensitive"
          >Download anyway</button>
        </div>
      </div>
    </div>

    <!-- ── Delete confirm modal ───────────────────────────────── -->
    <div v-if="confirmDelete.show" class="modal-overlay" @click.self="closeDelete">
      <div class="modal-card">
        <div class="modal-head">
          <span class="modal-icon-warn">🗑</span>
          <h3>Delete snapshot</h3>
        </div>
        <p class="modal-body">
          You are about to permanently delete the
          <strong>{{ activeTier }}/{{ confirmDelete.snap?.date }}</strong> snapshot
          ({{ formatBytes(confirmDelete.snap?.total_size || 0) }}).
          Type the path below to confirm.
        </p>
        <input
          ref="deleteInput"
          v-model="confirmDelete.typed"
          class="modal-input"
          :placeholder="`${activeTier}/${confirmDelete.snap?.date}`"
          @keydown.enter="proceedDelete"
        />
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeDelete">Cancel</button>
          <button
            class="btn-danger"
            :disabled="confirmDelete.typed !== `${activeTier}/${confirmDelete.snap?.date}`"
            @click="proceedDelete"
          >Permanently delete</button>
        </div>
      </div>
    </div>

    <!-- Toast for transient success messages -->
    <div v-if="toastMsg" class="bk-toast">{{ toastMsg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()

const backups = ref({ daily: [], weekly: [], monthly: [] })
const status = ref(null)
const loading = ref(true)
const triggering = ref(false)
const running = ref(false)
const activeTier = ref('daily')
const expanded = ref({})
const downloadingKey = ref('')
const toastMsg = ref('')

const tiers = [
  { key: 'daily',   label: 'Daily'   },
  { key: 'weekly',  label: 'Weekly'  },
  { key: 'monthly', label: 'Monthly' },
]

const currentSnapshots = computed(() => backups.value?.[activeTier.value] || [])

function isMostRecent(snap) {
  const arr = currentSnapshots.value
  if (!arr.length) return false
  return arr[0]?.date === snap.date  // backend already returns newest-first
}

function toggleExpanded(date) {
  expanded.value = { ...expanded.value, [date]: !expanded.value[date] }
}

function formatBytes(n) {
  if (n == null) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`
  return `${(n / 1024 ** 3).toFixed(2)} GB`
}

function relativeFromDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(`${dateStr}T00:00:00Z`)
    const diff = Date.now() - d.getTime()
    const days = Math.floor(diff / 86400000)
    if (days < 1) return 'today'
    if (days === 1) return 'yesterday'
    if (days < 7) return `${days} days ago`
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`
    return `${Math.floor(days / 30)} months ago`
  } catch { return '' }
}

// ── Loaders ───────────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true
  try {
    const [list, st] = await Promise.all([api.getBackups(), api.getBackupStatus()])
    backups.value = list || { daily: [], weekly: [], monthly: [] }
    status.value = st
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// ── Trigger backup with polling for completion ────────────────────────────
let pollTimer = null
async function onTriggerBackup() {
  triggering.value = true
  try {
    await api.triggerBackup()
    running.value = true
    flash('Backup started — refreshing list shortly…')
    // Poll status every 4s; treat "latest_date != today" → still running
    const todayUTC = new Date().toISOString().slice(0, 10)
    let attempts = 0
    pollTimer = setInterval(async () => {
      attempts += 1
      try {
        const st = await api.getBackupStatus()
        status.value = st
        if (st.latest_date === todayUTC) {
          clearInterval(pollTimer); pollTimer = null
          running.value = false
          await loadAll()
          flash('Backup complete.')
        }
      } catch {}
      if (attempts > 60) {  // 4 minutes hard cap
        clearInterval(pollTimer); pollTimer = null
        running.value = false
        flash('Backup is taking longer than expected — check VPS logs.')
      }
    }, 4000)
  } catch (e) {
    flash('Trigger failed: ' + (e.message || 'unknown'))
  } finally {
    triggering.value = false
  }
}

// ── Download flow ─────────────────────────────────────────────────────────
const confirmSensitive = ref({ show: false, snap: null, file: null, typed: '' })
const sensitiveInput = ref(null)

function onDownload(snap, file) {
  if (file.is_sensitive) {
    confirmSensitive.value = { show: true, snap, file, typed: '' }
    nextTick(() => sensitiveInput.value?.focus())
    return
  }
  doDownload(snap, file)
}

function closeSensitive() {
  confirmSensitive.value = { show: false, snap: null, file: null, typed: '' }
}

function proceedSensitive() {
  const { snap, file, typed } = confirmSensitive.value
  if (typed !== snap?.date) return
  closeSensitive()
  doDownload(snap, file)
}

async function doDownload(snap, file) {
  const key = snap.date + ':' + file.name
  downloadingKey.value = key
  try {
    await api.downloadBackupFile(activeTier.value, snap.date, file.name)
    flash(`Downloaded ${file.name}`)
  } catch (e) {
    flash('Download failed: ' + (e.message || 'unknown'))
  } finally {
    if (downloadingKey.value === key) downloadingKey.value = ''
  }
}

// ── Delete flow ───────────────────────────────────────────────────────────
const confirmDelete = ref({ show: false, snap: null, typed: '' })
const deleteInput = ref(null)

function askDelete(snap) {
  if (isMostRecent(snap)) return
  confirmDelete.value = { show: true, snap, typed: '' }
  nextTick(() => deleteInput.value?.focus())
}

function closeDelete() {
  confirmDelete.value = { show: false, snap: null, typed: '' }
}

async function proceedDelete() {
  const { snap, typed } = confirmDelete.value
  const expected = `${activeTier.value}/${snap?.date}`
  if (typed !== expected) return
  try {
    await api.deleteBackup(activeTier.value, snap.date)
    closeDelete()
    await loadAll()
    flash('Snapshot deleted.')
  } catch (e) {
    flash('Delete failed: ' + (e.message || 'unknown'))
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────
function flash(msg) {
  toastMsg.value = msg
  setTimeout(() => { if (toastMsg.value === msg) toastMsg.value = '' }, 3500)
}

onMounted(loadAll)
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.bk-page { padding: 24px 32px; max-width: 1100px; }

.bk-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; gap: 16px; flex-wrap: wrap; }
.bk-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.4px; }
.bk-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 4px; max-width: 700px; line-height: 1.5; }
.bk-sub code { font-family: 'Fira Mono', monospace; background: var(--cf-bg-input); padding: 1px 6px; border-radius: 4px; font-size: 12px; }

.trigger-btn {
  display: inline-flex; align-items: center; gap: 7px;
  background: linear-gradient(135deg, #6366F1, #8B5CF6); color: white;
  border: none; border-radius: 9px; padding: 9px 16px;
  font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
  transition: opacity 0.15s;
}
.trigger-btn:hover:not(:disabled) { opacity: 0.9; }
.trigger-btn:disabled { opacity: 0.55; cursor: not-allowed; }

/* Sensitivity warning banner */
.warn-banner {
  display: flex; align-items: center; gap: 10px;
  background: rgba(234,179,8,0.10); border: 1px solid rgba(234,179,8,0.30);
  color: #fbbf24; padding: 10px 14px; border-radius: 9px;
  font-size: 12.5px; line-height: 1.5; margin-bottom: 20px;
}

/* Stat strip */
.stat-row { display: grid; grid-template-columns: 2fr 1.5fr 1fr 1fr 1fr; gap: 12px; margin-bottom: 20px; }
.stat-card { background: var(--cf-bg-surface); border: 1px solid var(--cf-border-subtle); border-radius: 11px; padding: 14px 16px; }
.stat-label { font-size: 10.5px; font-weight: 700; color: var(--cf-text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); margin-top: 4px; letter-spacing: -0.3px; }
.stat-of   { font-size: 13px; color: var(--cf-text-muted); font-weight: 500; margin-left: 2px; }
.stat-sub  { font-size: 11px; color: var(--cf-text-secondary); margin-top: 4px; }

/* Tier tabs */
.tier-tabs { display: flex; gap: 6px; margin-bottom: 14px; }
.tier-tab {
  display: inline-flex; align-items: center; gap: 7px;
  background: var(--cf-bg-input); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-secondary); border-radius: 9px;
  padding: 8px 16px; font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.tier-tab:hover { color: var(--cf-text-primary); border-color: var(--cf-border-strong); }
.tier-tab.active {
  background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.4); color: #a5b4fc;
}
.tier-count {
  background: var(--cf-bg-ghost-hover); color: var(--cf-text-secondary);
  font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 10px;
}
.tier-tab.active .tier-count { background: rgba(99,102,241,0.2); color: #a5b4fc; }

/* Loading / empty */
.bk-loading { display: flex; justify-content: center; padding: 60px; }
.bk-spinner { width: 32px; height: 32px; border: 3px solid var(--cf-border-default); border-top-color: #6366F1; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.bk-empty {
  padding: 40px; text-align: center;
  background: var(--cf-bg-surface); border: 1px dashed var(--cf-border-default);
  border-radius: 11px; color: var(--cf-text-muted); font-size: 13px;
}

/* Snapshot list */
.snap-list { display: flex; flex-direction: column; gap: 8px; }
.snap-card { background: var(--cf-bg-surface); border: 1px solid var(--cf-border-subtle); border-radius: 11px; overflow: hidden; }
.snap-head {
  width: 100%; display: flex; align-items: center; gap: 14px;
  padding: 14px 18px; background: none; border: none; cursor: pointer;
  font-family: inherit; text-align: left;
  border-bottom: 1px solid transparent; transition: background 0.12s;
}
.snap-head:hover { background: var(--cf-bg-surface-hover); }
.snap-icon { font-size: 18px; }
.snap-date { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); }
.snap-size { font-size: 12px; color: var(--cf-text-secondary); }
.snap-git  { font-size: 11px; color: var(--cf-text-muted); font-family: monospace; }
.snap-rel  { margin-left: auto; font-size: 11.5px; color: var(--cf-text-muted); }
.snap-chev { color: var(--cf-text-muted); transition: transform 0.15s; }
.snap-chev.open { transform: rotate(180deg); }

/* File rows inside a snapshot */
.snap-files { border-top: 1px solid var(--cf-border-subtle); padding: 6px 0; }
.file-row {
  display: grid;
  grid-template-columns: 1.4fr 80px 130px 1fr 110px;
  gap: 12px; align-items: center;
  padding: 9px 18px;
  border-bottom: 1px solid var(--cf-border-subtle);
  font-size: 12.5px;
}
.file-row:last-of-type { border-bottom: none; }
.file-name { font-family: 'Fira Mono', monospace; color: var(--cf-text-primary); font-weight: 500; }
.file-size { color: var(--cf-text-secondary); }
.file-sha  { font-family: 'Fira Mono', monospace; font-size: 11px; color: var(--cf-text-muted); }
.file-sensitive .file-name { color: #fbbf24; }
.file-warn-pill {
  font-size: 10.5px; font-weight: 600; color: #fbbf24;
  background: rgba(234,179,8,0.12); border: 1px solid rgba(234,179,8,0.30);
  border-radius: 6px; padding: 2px 7px; white-space: nowrap;
}
.file-dl {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--cf-bg-ghost-hover); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-primary); border-radius: 7px;
  padding: 5px 12px; font-size: 12px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.file-dl:hover:not(:disabled) { background: var(--cf-border-default); }
.file-dl:disabled { opacity: 0.6; cursor: not-allowed; }

/* Snapshot-level actions */
.snap-actions {
  display: flex; align-items: center; justify-content: flex-end; gap: 10px;
  padding: 10px 18px; border-top: 1px solid var(--cf-border-subtle);
  background: var(--cf-bg-surface-hover);
}
.delete-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(239,68,68,0.10); border: 1px solid rgba(239,68,68,0.30);
  color: #fca5a5; border-radius: 7px; padding: 5px 12px;
  font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit;
  transition: background 0.15s;
}
.delete-btn:hover:not(:disabled) { background: rgba(239,68,68,0.20); }
.delete-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.snap-locked-hint { font-size: 11px; color: var(--cf-text-muted); }

/* Pulse dot for running states */
.dot { width: 9px; height: 9px; border-radius: 50%; background: currentColor; display: inline-block; }
.pulse { animation: pulse-anim 1.2s ease-in-out infinite; }
@keyframes pulse-anim { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.55); backdrop-filter: blur(3px);
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.modal-card {
  width: 100%; max-width: 460px;
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-default); border-radius: 13px;
  padding: 22px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}
.modal-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.modal-icon-warn { font-size: 22px; }
.modal-head h3 { font-size: 16px; font-weight: 700; color: var(--cf-text-primary); }
.modal-body { font-size: 13px; color: var(--cf-text-secondary); line-height: 1.6; margin-bottom: 14px; }
.modal-body code { font-family: monospace; background: var(--cf-bg-input); padding: 1px 6px; border-radius: 4px; font-size: 12px; color: #fbbf24; }
.modal-input {
  width: 100%; background: var(--cf-bg-input); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-primary); border-radius: 9px;
  padding: 9px 12px; font-size: 13px; font-family: 'Fira Mono', monospace;
  outline: none; transition: border-color 0.15s; margin-bottom: 16px;
}
.modal-input:focus { border-color: rgba(99,102,241,0.5); }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
.btn-secondary, .btn-danger {
  border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 600;
  cursor: pointer; font-family: inherit; border: 1px solid;
  transition: opacity 0.15s;
}
.btn-secondary { background: var(--cf-bg-input); border-color: var(--cf-border-default); color: var(--cf-text-secondary); }
.btn-secondary:hover { color: var(--cf-text-primary); }
.btn-danger { background: #DC2626; border-color: #DC2626; color: white; }
.btn-danger:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-danger:hover:not(:disabled) { opacity: 0.88; }

/* Transient toast */
.bk-toast {
  position: fixed; bottom: 28px; right: 28px;
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-default); border-radius: 10px;
  padding: 10px 16px; font-size: 13px; color: var(--cf-text-primary);
  box-shadow: 0 10px 30px rgba(0,0,0,0.4);
  animation: toast-in 0.2s ease;
  z-index: 1100;
}
@keyframes toast-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 900px) {
  .stat-row { grid-template-columns: 1fr 1fr; }
  .file-row { grid-template-columns: 1fr 1fr; }
  .file-sha { display: none; }
}
@media (max-width: 600px) {
  .bk-page { padding: 16px; }
  .stat-row { grid-template-columns: 1fr 1fr; }
}
</style>
