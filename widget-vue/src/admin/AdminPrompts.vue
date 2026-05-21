<template>
  <div class="pr-page">
    <!-- ── Header strip ───────────────────────────────────────────── -->
    <div class="pr-header">
      <div>
        <h1 class="pr-title">System Prompts</h1>
        <p class="pr-sub">
          Live system prompts used for every chatbot reply. Edits propagate
          to all tenants within ~60 seconds. Password confirmation is required
          before any save or rollback.
        </p>
      </div>
    </div>

    <!-- ── Sensitivity banner ─────────────────────────────────────── -->
    <div class="warn-banner">
      <svg width="16" height="16" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="9"  x2="12" y2="13"  stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="12" y1="17" x2="12.01" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span>
        These prompts shape every chatbot reply for every tenant. A bad save
        affects production immediately. Use Preview before Save.
      </span>
    </div>

    <div v-if="loading" class="pr-loading"><div class="pr-spinner"></div></div>

    <div v-else-if="error" class="pr-error">
      Failed to load prompts: {{ error }}
    </div>

    <div v-else class="pr-grid">
      <div v-for="p in prompts" :key="p.slug" class="pr-card">
        <div class="pr-card-head">
          <div>
            <h2 class="pr-card-title">{{ slugLabel(p.slug) }}</h2>
            <p class="pr-card-slug">{{ p.slug }}</p>
          </div>
          <span class="pr-version-pill">
            v{{ p.active_version?.version || '—' }}
          </span>
        </div>

        <p class="pr-card-desc">{{ p.description }}</p>

        <div class="pr-card-meta">
          <span class="pr-meta-label">Last edited</span>
          <span class="pr-meta-val">
            {{ formatTime(p.active_version?.created_at) }}
            <template v-if="p.active_version?.created_by">
              by <strong>{{ p.active_version.created_by }}</strong>
            </template>
          </span>
        </div>

        <div v-if="p.active_version?.notes" class="pr-card-notes">
          {{ p.active_version.notes }}
        </div>

        <button class="pr-edit-btn" @click="$router.push(`/admin/prompts/${p.slug}`)">
          Open editor →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()

const prompts = ref([])
const loading = ref(true)
const error   = ref('')

function slugLabel(slug) {
  if (slug === 'system_persona')     return 'System Persona'
  if (slug === 'state_instructions') return 'State Instructions'
  return slug
}

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

async function load() {
  loading.value = true
  error.value = ''
  try {
    prompts.value = await api.listPrompts()
  } catch (e) {
    error.value = e.message || 'Unknown error'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.pr-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
.pr-header { margin-bottom: 1.5rem; }
.pr-title  { font-size: 1.5rem; font-weight: 600; margin: 0 0 0.25rem 0; }
.pr-sub    { color: #6b7280; font-size: 0.875rem; margin: 0; line-height: 1.5; }

.warn-banner {
  display: flex; align-items: center; gap: 0.5rem;
  background: #fffaf0; border: 1px solid #f5d491;
  color: #92400e; padding: 0.75rem 1rem; border-radius: 0.5rem;
  font-size: 0.825rem; margin-bottom: 1.5rem;
}

.pr-loading { display: flex; justify-content: center; padding: 4rem 0; }
.pr-spinner {
  width: 1.75rem; height: 1.75rem; border-radius: 50%;
  border: 3px solid #e5e7eb; border-top-color: #6366f1;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg) } }

.pr-error {
  background: #fef2f2; color: #991b1b; padding: 1rem; border-radius: 0.5rem;
}

.pr-grid {
  display: grid; gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}
.pr-card {
  background: white; border: 1px solid #e5e7eb; border-radius: 0.75rem;
  padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.pr-card:hover { border-color: #c7d2fe; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }

.pr-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }
.pr-card-title { font-size: 1rem; font-weight: 600; margin: 0; color: #111827; }
.pr-card-slug  { font-size: 0.75rem; color: #9ca3af; margin: 0; font-family: ui-monospace, monospace; }

.pr-version-pill {
  background: #eef2ff; color: #4338ca;
  padding: 0.125rem 0.5rem; border-radius: 9999px;
  font-size: 0.75rem; font-weight: 600;
}

.pr-card-desc {
  color: #4b5563; font-size: 0.825rem; margin: 0;
  line-height: 1.5; min-height: 2.6em;
}

.pr-card-meta { font-size: 0.75rem; color: #6b7280; }
.pr-meta-label { display: inline-block; margin-right: 0.25rem; }
.pr-meta-val   { color: #374151; }

.pr-card-notes {
  background: #f9fafb; padding: 0.5rem 0.75rem; border-radius: 0.375rem;
  font-size: 0.75rem; color: #4b5563; font-style: italic;
}

.pr-edit-btn {
  margin-top: auto;
  background: #4f46e5; color: white; border: 0; padding: 0.5rem 0.875rem;
  border-radius: 0.5rem; cursor: pointer; font-weight: 500;
  font-size: 0.875rem;
  transition: background 0.15s;
}
.pr-edit-btn:hover { background: #4338ca; }
</style>
