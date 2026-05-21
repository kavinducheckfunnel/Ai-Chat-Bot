<template>
  <div class="ed-page">
    <!-- ── Header ─────────────────────────────────────────────────── -->
    <div class="ed-header">
      <button class="ed-back" @click="$router.push('/admin/prompts')">
        ← Back to prompts
      </button>
      <h1 class="ed-title">
        {{ slugLabel }}
        <span v-if="template?.active_version" class="ed-version-pill">
          v{{ template.active_version.version }}
        </span>
      </h1>
      <p class="ed-sub">
        Edits go live for all tenants within ~60 seconds of saving.
        Password confirmation is required to save or roll back.
      </p>
    </div>

    <div v-if="loading" class="ed-loading"><div class="ed-spinner"></div></div>

    <div v-else-if="loadError" class="ed-error">{{ loadError }}</div>

    <template v-else>
      <!-- ── Top toolbar ────────────────────────────────────────── -->
      <div class="ed-toolbar">
        <div class="ed-left">
          <label class="ed-label">View / Compare:</label>
          <select v-model="compareWithId" class="ed-select" @change="onCompareChange">
            <option value="">Active (v{{ template.active_version?.version }})</option>
            <option
              v-for="v in versions"
              :key="v.id"
              :value="v.id"
              :disabled="v.id === template.active_version?.id"
            >
              v{{ v.version }} —
              {{ v.is_default ? 'factory default' : (v.notes || '(no notes)') }}
              · {{ formatTime(v.created_at) }}
              {{ v.created_by ? `· ${v.created_by}` : '' }}
            </option>
          </select>
        </div>
        <div class="ed-right">
          <button
            class="btn-secondary"
            :disabled="rollbackPending || compareWithId === '' || compareWithId === template.active_version?.id"
            @click="onRollback"
          >
            Roll back to selected
          </button>
          <button class="btn-secondary" :disabled="resetPending" @click="onReset">
            Reset to factory default
          </button>
        </div>
      </div>

      <!-- ── Two-column edit + diff ─────────────────────────────── -->
      <div class="ed-cols">
        <!-- LEFT: editor -->
        <div class="ed-col">
          <div class="ed-col-head">
            <span class="ed-col-title">Editor</span>
            <span class="ed-col-stats">
              {{ editorBody.length.toLocaleString() }} chars
              · ~{{ approxTokens(editorBody) }} tokens
              <span v-if="dirty" class="ed-dirty-dot" title="Unsaved changes" />
            </span>
          </div>
          <textarea
            v-model="editorBody"
            class="ed-textarea"
            :class="{ 'invalid': validation.errors.length > 0 }"
            spellcheck="false"
            @input="onEditorInput"
          ></textarea>

          <div v-if="validation.errors.length" class="ed-validation">
            <div class="ed-validation-title">Validation errors</div>
            <ul>
              <li v-for="(e, i) in validation.errors" :key="i">{{ e }}</li>
            </ul>
          </div>
          <div v-else-if="validation.checked && validation.ok" class="ed-validation ok">
            ✓ Validation passed.
            <template v-if="validation.stats">
              ({{ validation.stats.lines }} lines · ~{{ validation.stats.approx_tokens }} tokens)
            </template>
          </div>
        </div>

        <!-- RIGHT: diff -->
        <div class="ed-col">
          <div class="ed-col-head">
            <span class="ed-col-title">
              Diff <span class="ed-col-sub">(active vs editor)</span>
            </span>
            <span v-if="diffStats" class="ed-col-stats">
              +{{ diffStats.added }} / -{{ diffStats.removed }}
            </span>
          </div>
          <div class="ed-diff">
            <template v-if="diffLines.length === 0">
              <div class="ed-diff-empty">No changes yet.</div>
            </template>
            <template v-else>
              <div
                v-for="(d, i) in diffLines"
                :key="i"
                class="ed-diff-line"
                :class="`ed-diff-${d.kind}`"
              >
                <span class="ed-diff-marker">{{ d.marker }}</span>
                <span class="ed-diff-text">{{ d.text || ' ' }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- ── Action bar ─────────────────────────────────────────── -->
      <div class="ed-action-bar">
        <div class="ed-left">
          <button class="btn-secondary" :disabled="previewing" @click="onPreview">
            {{ previewing ? 'Checking…' : 'Preview / Validate' }}
          </button>
          <button class="btn-secondary" :disabled="!dirty" @click="onRevert">
            Revert edits
          </button>
        </div>
        <div class="ed-right">
          <input
            v-model="notes"
            placeholder="Notes for this version (optional)"
            class="ed-notes"
            maxlength="500"
          />
          <button
            class="btn-primary"
            :disabled="!canSave"
            @click="onSaveClick"
          >
            {{ saving ? 'Saving…' : 'Save new version' }}
          </button>
        </div>
      </div>
    </template>

    <!-- ── Re-auth modal ──────────────────────────────────────────── -->
    <div v-if="reauth.open" class="modal-backdrop" @click.self="closeReauth">
      <div class="modal">
        <h3 class="modal-title">Confirm your password</h3>
        <p class="modal-desc">
          Editing the live prompt is a sensitive action.
          Please re-enter your password to authorize this change.
        </p>
        <input
          ref="reauthInputEl"
          v-model="reauth.password"
          type="password"
          class="modal-input"
          placeholder="Your password"
          autocomplete="current-password"
          @keydown.enter="submitReauth"
          @keydown.escape="closeReauth"
        />
        <div v-if="reauth.error" class="modal-error">{{ reauth.error }}</div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeReauth">Cancel</button>
          <button class="btn-primary" :disabled="reauth.submitting || !reauth.password" @click="submitReauth">
            {{ reauth.submitting ? 'Confirming…' : 'Confirm' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── Toast ─────────────────────────────────────────────────── -->
    <div v-if="toast" class="ed-toast" :class="`ed-toast-${toast.kind}`">
      {{ toast.text }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const api    = useAdminApi()
const route  = useRoute()
const router = useRouter()

const slug = computed(() => route.params.slug)
const slugLabel = computed(() => {
  if (slug.value === 'system_persona')     return 'System Persona'
  if (slug.value === 'state_instructions') return 'State Instructions'
  return slug.value
})

// ── Page state ───────────────────────────────────────────────────────────
const loading     = ref(true)
const loadError   = ref('')
const template    = ref(null)
const versions    = ref([])
const editorBody  = ref('')   // current editor content
const activeBody  = ref('')   // body of the currently-active version (for diff)
const notes       = ref('')
const compareWithId = ref('') // '' = compare against active; else a version id

const validation  = ref({ checked: false, ok: false, errors: [], stats: null })
const previewing  = ref(false)
const saving      = ref(false)
const rollbackPending = ref(false)
const resetPending    = ref(false)

const toast = ref(null)

// ── Re-auth state ────────────────────────────────────────────────────────
// We cache the token so a single password entry covers multiple saves
// within the 5-minute window the backend issues.
const reauthInputEl = ref(null)
const reauth = ref({
  open: false,
  password: '',
  error: '',
  submitting: false,
  token: '',                  // cached short-lived JWT
  expiresAt: 0,               // epoch ms when the token stops being valid
  pendingAction: null,        // closure invoked on success
})

function tokenValid() {
  return reauth.value.token && reauth.value.expiresAt > Date.now() + 5000
}

function openReauth(pendingAction) {
  reauth.value.open = true
  reauth.value.password = ''
  reauth.value.error = ''
  reauth.value.submitting = false
  reauth.value.pendingAction = pendingAction
  nextTick(() => reauthInputEl.value?.focus())
}

function closeReauth() {
  reauth.value.open = false
  reauth.value.pendingAction = null
}

async function submitReauth() {
  reauth.value.submitting = true
  reauth.value.error = ''
  try {
    const data = await api.promptReauth(reauth.value.password)
    reauth.value.token = data.reauth_token
    reauth.value.expiresAt = Date.now() + (data.expires_in || 300) * 1000
    const cb = reauth.value.pendingAction
    closeReauth()
    if (cb) await cb()
  } catch (e) {
    reauth.value.error = e.message || 'Authentication failed.'
  } finally {
    reauth.value.submitting = false
  }
}

// ── Dirty / save gating ──────────────────────────────────────────────────
const dirty = computed(() => editorBody.value !== activeBody.value)
const canSave = computed(() => dirty.value && !saving.value && validation.value.errors.length === 0)

// ── Loaders ──────────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const detail = await api.getPrompt(slug.value)
    template.value = detail
    activeBody.value = detail.active_body || ''
    editorBody.value = detail.active_body || ''

    const vs = await api.getPromptVersions(slug.value)
    versions.value = vs.results || []
  } catch (e) {
    loadError.value = e.message || 'Failed to load prompt.'
  } finally {
    loading.value = false
  }
}

async function onCompareChange() {
  // When a non-active version is selected, load its body into the editor
  // so the diff (active vs editor) shows the candidate change.
  if (!compareWithId.value) {
    editorBody.value = activeBody.value
    return
  }
  if (compareWithId.value === template.value.active_version?.id) {
    editorBody.value = activeBody.value
    return
  }
  try {
    const v = await api.getPromptVersionDetail(slug.value, compareWithId.value)
    editorBody.value = v.body
  } catch (e) {
    showToast('Failed to load version: ' + (e.message || 'unknown error'), 'error')
  }
}

function onEditorInput() {
  // Any keystroke clears the previous validation result.
  if (validation.value.checked) validation.value = { checked: false, ok: false, errors: [], stats: null }
}

function onRevert() {
  editorBody.value = activeBody.value
  validation.value = { checked: false, ok: false, errors: [], stats: null }
}

// ── Preview / validation ─────────────────────────────────────────────────
async function onPreview() {
  previewing.value = true
  try {
    const result = await api.previewPrompt(slug.value, editorBody.value)
    validation.value = {
      checked: true,
      ok: !!result.ok,
      errors: result.errors || [],
      stats:  result.stats || null,
    }
    if (result.ok) showToast('Validation passed.', 'success')
  } catch (e) {
    validation.value = { checked: true, ok: false, errors: [e.message || 'Validation failed.'], stats: null }
  } finally {
    previewing.value = false
  }
}

// ── Save ─────────────────────────────────────────────────────────────────
function onSaveClick() {
  if (!dirty.value) return
  if (tokenValid()) {
    doSave()
  } else {
    openReauth(doSave)
  }
}

async function doSave() {
  saving.value = true
  try {
    const result = await api.savePrompt(slug.value, editorBody.value, notes.value, reauth.value.token)
    showToast(`Saved as v${result.version.version}.`, 'success')
    notes.value = ''
    await loadAll()
  } catch (e) {
    // 422 with structured errors → show them inline
    if (e.status === 422 && e.response?.errors) {
      validation.value = { checked: true, ok: false, errors: e.response.errors, stats: null }
      showToast('Validation failed — see errors above.', 'error')
    } else if (e.status === 403) {
      // Token expired or invalid — force re-auth and retry once
      reauth.value.token = ''
      reauth.value.expiresAt = 0
      openReauth(doSave)
    } else {
      showToast(e.message || 'Save failed.', 'error')
    }
  } finally {
    saving.value = false
  }
}

// ── Rollback ─────────────────────────────────────────────────────────────
function onRollback() {
  if (!compareWithId.value) return
  if (tokenValid()) {
    doRollback()
  } else {
    openReauth(doRollback)
  }
}

async function doRollback() {
  rollbackPending.value = true
  try {
    const result = await api.rollbackPrompt(slug.value, compareWithId.value, reauth.value.token)
    showToast(result.detail || 'Rolled back.', 'success')
    compareWithId.value = ''
    await loadAll()
  } catch (e) {
    if (e.status === 403) {
      reauth.value.token = ''
      reauth.value.expiresAt = 0
      openReauth(doRollback)
    } else {
      showToast(e.message || 'Rollback failed.', 'error')
    }
  } finally {
    rollbackPending.value = false
  }
}

// ── Reset to factory default ────────────────────────────────────────────
function onReset() {
  if (!confirm('Reset this prompt to its factory default? This will create a new version with the original file content.')) return
  if (tokenValid()) {
    doReset()
  } else {
    openReauth(doReset)
  }
}

async function doReset() {
  resetPending.value = true
  try {
    const result = await api.resetPrompt(slug.value, reauth.value.token)
    showToast(result.detail || 'Reset to factory default.', 'success')
    await loadAll()
  } catch (e) {
    if (e.status === 403) {
      reauth.value.token = ''
      reauth.value.expiresAt = 0
      openReauth(doReset)
    } else {
      showToast(e.message || 'Reset failed.', 'error')
    }
  } finally {
    resetPending.value = false
  }
}

// ── Diff (line-based, simple LCS-free) ──────────────────────────────────
// For readability we use a naive diff: shared prefix, shared suffix,
// then all middle lines from each side marked as removed / added.
// This is sufficient for prompt-style edits which are usually localized.
const diffLines = computed(() => {
  const a = activeBody.value.split('\n')
  const b = editorBody.value.split('\n')

  let prefix = 0
  while (prefix < a.length && prefix < b.length && a[prefix] === b[prefix]) prefix++

  let aEnd = a.length, bEnd = b.length
  while (
    aEnd > prefix && bEnd > prefix &&
    a[aEnd - 1] === b[bEnd - 1]
  ) { aEnd--; bEnd-- }

  if (prefix === a.length && prefix === b.length) return []  // identical

  const out = []
  for (let i = 0; i < prefix; i++) out.push({ kind: 'same', marker: ' ', text: a[i] })
  for (let i = prefix; i < aEnd; i++) out.push({ kind: 'rem',  marker: '-', text: a[i] })
  for (let i = prefix; i < bEnd; i++) out.push({ kind: 'add',  marker: '+', text: b[i] })
  for (let i = aEnd; i < a.length; i++) out.push({ kind: 'same', marker: ' ', text: a[i] })

  // Trim very long "same" runs to keep the diff focused
  return trimSameRuns(out, 3)
})

function trimSameRuns(lines, contextLines) {
  const out = []
  let run = []
  function flushRun() {
    if (run.length <= 2 * contextLines + 1) {
      out.push(...run)
    } else {
      out.push(...run.slice(0, contextLines))
      out.push({ kind: 'ellipsis', marker: '⋯', text: `(${run.length - 2 * contextLines} unchanged lines)` })
      out.push(...run.slice(run.length - contextLines))
    }
    run = []
  }
  for (const l of lines) {
    if (l.kind === 'same') {
      run.push(l)
    } else {
      if (run.length) flushRun()
      out.push(l)
    }
  }
  if (run.length) flushRun()
  return out
}

const diffStats = computed(() => {
  let added = 0, removed = 0
  for (const l of diffLines.value) {
    if (l.kind === 'add') added++
    if (l.kind === 'rem') removed++
  }
  return { added, removed }
})

// ── Misc helpers ─────────────────────────────────────────────────────────
function approxTokens(s) { return Math.max(1, Math.ceil(s.length / 4)) }

function formatTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    const diff = Date.now() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1)  return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    const days = Math.floor(hrs / 24)
    if (days < 7) return `${days}d ago`
    return d.toLocaleDateString()
  } catch { return iso }
}

function showToast(text, kind = 'success') {
  toast.value = { text, kind }
  setTimeout(() => {
    if (toast.value && toast.value.text === text) toast.value = null
  }, 3500)
}

// Re-load when the route's slug changes (navigating between editor pages).
watch(slug, loadAll)
onMounted(loadAll)
</script>

<style scoped>
.ed-page {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  display: flex; flex-direction: column; gap: 1rem;
}

.ed-back {
  background: transparent; border: 0; color: #6366f1;
  cursor: pointer; padding: 0; margin-bottom: 0.5rem;
  font-size: 0.875rem; font-weight: 500;
}
.ed-back:hover { color: #4338ca; }

.ed-title {
  font-size: 1.5rem; font-weight: 600; margin: 0 0 0.25rem 0;
  display: flex; align-items: center; gap: 0.5rem;
}
.ed-version-pill {
  background: #eef2ff; color: #4338ca;
  padding: 0.125rem 0.5rem; border-radius: 9999px;
  font-size: 0.75rem; font-weight: 600;
}
.ed-sub { color: #6b7280; font-size: 0.825rem; margin: 0; }

.ed-loading { display: flex; justify-content: center; padding: 4rem 0; }
.ed-spinner {
  width: 1.75rem; height: 1.75rem; border-radius: 50%;
  border: 3px solid #e5e7eb; border-top-color: #6366f1;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg) } }

.ed-error {
  background: #fef2f2; color: #991b1b; padding: 1rem; border-radius: 0.5rem;
}

.ed-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  gap: 1rem; background: white; padding: 0.75rem 1rem;
  border: 1px solid #e5e7eb; border-radius: 0.5rem;
}
.ed-left, .ed-right { display: flex; align-items: center; gap: 0.5rem; }
.ed-label  { font-size: 0.825rem; color: #4b5563; }
.ed-select {
  border: 1px solid #d1d5db; border-radius: 0.375rem;
  padding: 0.375rem 0.625rem; font-size: 0.825rem; min-width: 280px;
  background: white;
}

.ed-cols {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; min-height: 60vh;
}
.ed-col {
  background: white; border: 1px solid #e5e7eb; border-radius: 0.5rem;
  display: flex; flex-direction: column;
}
.ed-col-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.625rem 0.875rem; border-bottom: 1px solid #e5e7eb;
  background: #f9fafb; border-radius: 0.5rem 0.5rem 0 0;
  font-size: 0.825rem; font-weight: 500; color: #374151;
}
.ed-col-title { display: flex; gap: 0.375rem; align-items: baseline; }
.ed-col-sub { font-weight: 400; color: #9ca3af; font-size: 0.75rem; }
.ed-col-stats { font-size: 0.75rem; color: #6b7280; }
.ed-dirty-dot {
  display: inline-block; width: 0.5rem; height: 0.5rem; border-radius: 50%;
  background: #f59e0b; margin-left: 0.375rem;
}

.ed-textarea {
  flex: 1; min-height: 50vh;
  border: 0; border-radius: 0 0 0.5rem 0.5rem;
  padding: 0.75rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.825rem; line-height: 1.5;
  resize: vertical; outline: none;
  color: #111827; background: white;
}
.ed-textarea.invalid { background: #fffaf0; }

.ed-diff {
  flex: 1; overflow: auto; padding: 0.5rem 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8rem; line-height: 1.45;
}
.ed-diff-empty {
  padding: 2rem; text-align: center; color: #9ca3af; font-style: italic;
}
.ed-diff-line { display: flex; padding: 0.05rem 0.875rem; white-space: pre; }
.ed-diff-marker {
  width: 1.25rem; flex-shrink: 0; color: #9ca3af; user-select: none;
}
.ed-diff-text { flex: 1; word-break: break-all; }
.ed-diff-same     { color: #6b7280; }
.ed-diff-add      { background: #ecfdf5; color: #065f46; }
.ed-diff-add .ed-diff-marker { color: #10b981; }
.ed-diff-rem      { background: #fef2f2; color: #991b1b; }
.ed-diff-rem .ed-diff-marker { color: #ef4444; }
.ed-diff-ellipsis { color: #9ca3af; font-style: italic; }

.ed-action-bar {
  display: flex; justify-content: space-between; align-items: center;
  gap: 1rem; background: white; padding: 0.75rem 1rem;
  border: 1px solid #e5e7eb; border-radius: 0.5rem;
}
.ed-notes {
  border: 1px solid #d1d5db; border-radius: 0.375rem;
  padding: 0.5rem 0.625rem; font-size: 0.825rem; min-width: 280px;
}

.ed-validation {
  background: #fef2f2; color: #991b1b; padding: 0.625rem 0.875rem;
  border-radius: 0.375rem; margin: 0.5rem 0.875rem 0.875rem;
  font-size: 0.825rem;
}
.ed-validation.ok { background: #ecfdf5; color: #065f46; }
.ed-validation-title { font-weight: 600; margin-bottom: 0.25rem; }
.ed-validation ul { margin: 0; padding-left: 1.25rem; }

.btn-primary {
  background: #4f46e5; color: white; border: 0;
  padding: 0.5rem 1rem; border-radius: 0.375rem;
  cursor: pointer; font-weight: 500; font-size: 0.875rem;
}
.btn-primary:hover:not(:disabled) { background: #4338ca; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: white; border: 1px solid #d1d5db; color: #374151;
  padding: 0.5rem 0.875rem; border-radius: 0.375rem;
  cursor: pointer; font-weight: 500; font-size: 0.825rem;
}
.btn-secondary:hover:not(:disabled) { background: #f3f4f6; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Modal ── */
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(15,23,42,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: white; padding: 1.5rem; border-radius: 0.75rem;
  width: 28rem; max-width: 90vw;
  box-shadow: 0 20px 50px rgba(0,0,0,0.2);
}
.modal-title { margin: 0 0 0.5rem 0; font-size: 1.125rem; font-weight: 600; }
.modal-desc  { margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem; line-height: 1.5; }
.modal-input {
  width: 100%; padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db; border-radius: 0.375rem;
  font-size: 0.875rem; box-sizing: border-box;
}
.modal-input:focus { border-color: #6366f1; outline: 2px solid #c7d2fe; }
.modal-error {
  margin-top: 0.5rem; color: #991b1b; font-size: 0.825rem;
  background: #fef2f2; padding: 0.5rem; border-radius: 0.375rem;
}
.modal-actions {
  display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;
}

/* ── Toast ── */
.ed-toast {
  position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 200;
  padding: 0.625rem 1rem; border-radius: 0.5rem;
  background: #111827; color: white; font-size: 0.875rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  animation: slide-in 0.2s ease-out;
}
.ed-toast-success { background: #059669; }
.ed-toast-error   { background: #dc2626; }
@keyframes slide-in {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0); opacity: 1; }
}
</style>
