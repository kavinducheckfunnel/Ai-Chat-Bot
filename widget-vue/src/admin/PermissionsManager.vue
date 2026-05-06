<template>
  <div class="perm-app">
    <Sidebar />
    <main class="perm-main">

      <div class="page-header">
        <div>
          <h1 class="page-title">Permissions Manager</h1>
          <p class="page-sub">Control per-tenant feature access — override plan defaults for individual tenants</p>
        </div>
      </div>

      <div class="perm-layout">

        <!-- Left: tenant list -->
        <div class="tenant-list-panel">
          <div class="panel-header">
            <input v-model="tenantSearch" class="search-input" placeholder="Search tenants…" />
          </div>
          <div v-if="loadingTenants" class="panel-loading">
            <div class="spinner-sm"></div>
          </div>
          <div v-else class="tenant-list">
            <div
              v-for="t in filteredTenants" :key="t.id"
              class="tenant-row"
              :class="{ selected: selectedTenant?.id === t.id }"
              @click="selectTenant(t)"
            >
              <div class="tenant-avatar">{{ (t.company_name || t.username).slice(0,2).toUpperCase() }}</div>
              <div class="tenant-info">
                <div class="tenant-name">{{ t.company_name || t.username }}</div>
                <div class="tenant-plan">
                  <span class="plan-dot" :class="'dot-'+(t.plan||'none').toLowerCase()"></span>
                  {{ t.plan || 'No plan' }}
                </div>
              </div>
              <div v-if="overrideCounts[t.id]" class="override-count">{{ overrideCounts[t.id] }}</div>
            </div>
            <div v-if="!filteredTenants.length" class="no-tenants">No tenants found</div>
          </div>
        </div>

        <!-- Right: permissions grid -->
        <div class="permissions-panel">
          <div v-if="!selectedTenant" class="empty-prompt">
            <div class="empty-icon">🔒</div>
            <div class="empty-msg">Select a tenant to manage their permissions</div>
          </div>

          <template v-else>
            <div class="perms-header">
              <div>
                <h2 class="perms-title">{{ selectedTenant.company_name || selectedTenant.username }}</h2>
                <p class="perms-sub">
                  Plan: <strong>{{ selectedTenant.plan || 'None' }}</strong>
                  <span v-if="overrides.length" class="override-badge-inline">{{ overrides.length }} active override{{ overrides.length !== 1 ? 's' : '' }}</span>
                </p>
              </div>
              <div v-if="saveMsg" class="save-flash">{{ saveMsg }}</div>
            </div>

            <div v-if="loadingOverrides" class="panel-loading"><div class="spinner-sm"></div></div>

            <template v-else>
              <!-- Feature groups -->
              <div v-for="group in featureGroups" :key="group.label" class="feat-group">
                <h3 class="group-label">{{ group.label }}</h3>
                <div class="feat-grid">
                  <div v-for="feat in group.features" :key="feat.key" class="feat-card" :class="getCardClass(feat.key)">
                    <div class="feat-top">
                      <div class="feat-icon" v-html="feat.icon"></div>
                      <div class="feat-info">
                        <div class="feat-name">{{ feat.label }}</div>
                        <div class="feat-source">{{ getSource(feat.key) }}</div>
                      </div>
                    </div>
                    <div class="feat-actions">
                      <button
                        class="feat-btn grant-btn"
                        :class="{ active: getOverride(feat.key)?.enabled === true }"
                        @click="setOverride(feat.key, true)"
                        :disabled="saving"
                        title="Grant this feature"
                      >Grant</button>
                      <button
                        class="feat-btn plan-btn"
                        :class="{ active: !getOverride(feat.key) }"
                        @click="removeOverride(feat.key)"
                        :disabled="saving"
                        title="Use plan default"
                      >Plan Default</button>
                      <button
                        class="feat-btn revoke-btn"
                        :class="{ active: getOverride(feat.key)?.enabled === false }"
                        @click="setOverride(feat.key, false)"
                        :disabled="saving"
                        title="Revoke this feature"
                      >Revoke</button>
                    </div>
                    <div v-if="getOverride(feat.key)" class="feat-override-info">
                      <span class="ov-label">Override</span>
                      <input
                        class="ov-reason"
                        type="text"
                        placeholder="Reason…"
                        :value="getOverride(feat.key).reason"
                        @change="updateReason(feat.key, $event.target.value)"
                      />
                      <input
                        class="ov-expiry"
                        type="datetime-local"
                        :value="getOverride(feat.key).expires_at ? getOverride(feat.key).expires_at.slice(0,16) : ''"
                        @change="updateExpiry(feat.key, $event.target.value)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </div>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Sidebar from './Sidebar.vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()

const tenants = ref([])
const loadingTenants = ref(false)
const tenantSearch = ref('')
const selectedTenant = ref(null)
const overrides = ref([])
const loadingOverrides = ref(false)
const saving = ref(false)
const saveMsg = ref('')
const overrideCounts = ref({})

const featureGroups = [
  {
    label: 'Channels',
    features: [
      { key: 'allow_whatsapp',  label: 'WhatsApp Business', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="#25d366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884"/></svg>' },
      { key: 'allow_telegram',  label: 'Telegram Bot',      icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#0088cc" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>' },
      { key: 'allow_messenger', label: 'FB Messenger',      icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="#0084FF"><path d="M12 2C6.477 2 2 6.145 2 11.243c0 2.842 1.358 5.38 3.504 7.106V22l3.36-1.847A10.94 10.94 0 0012 20.486c5.523 0 10-4.145 10-9.243S17.523 2 12 2z"/></svg>' },
    ],
  },
  {
    label: 'AI & Knowledge',
    features: [
      { key: 'allow_byok',        label: 'Custom AI (BYOK)',     icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#c084fc" stroke-width="2"><path d="M21 2H3v16h5v4l4-4h9V2z"/></svg>' },
      { key: 'allow_voice_input', label: 'Voice Input',          icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#60a5fa" stroke-width="2"><path d="M12 1a3 3 0 013 3v8a3 3 0 11-6 0V4a3 3 0 013-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"/></svg>' },
      { key: 'allow_image_input', label: 'Image Input',          icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#34d399" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>' },
    ],
  },
  {
    label: 'Integrations',
    features: [
      { key: 'allow_hubspot',  label: 'HubSpot CRM',       icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#ff7a00" stroke-width="2"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg>' },
      { key: 'allow_slack',    label: 'Slack Notifications',icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#4a154b" stroke-width="2"><rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="2" y="14" width="8" height="8" rx="2"/><rect x="14" y="14" width="8" height="8" rx="2"/></svg>' },
      { key: 'allow_webhooks', label: 'Outbound Webhooks',  icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#f97316" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>' },
    ],
  },
  {
    label: 'Inbox & Support',
    features: [
      { key: 'allow_god_view',          label: 'Live Takeover',      icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#a78bfa" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' },
      { key: 'allow_canned_responses',  label: 'Canned Responses',   icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#38bdf8" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>' },
      { key: 'allow_conversation_tags', label: 'Conversation Tags',  icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#fbbf24" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>' },
      { key: 'allow_csv_export',        label: 'CSV Export',         icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#86efac" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' },
    ],
  },
  {
    label: 'Branding & Advanced',
    features: [
      { key: 'remove_branding',     label: 'Remove Branding',  icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#f472b6" stroke-width="2"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/></svg>' },
      { key: 'allow_custom_domain', label: 'Custom Domain',    icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#e879f9" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/></svg>' },
      { key: 'allow_api_access',    label: 'API Access',       icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#94a3b8" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>' },
      { key: 'allow_fomo_triggers', label: 'FOMO Triggers',    icon: '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#fb923c" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>' },
    ],
  },
]

const filteredTenants = computed(() =>
  tenants.value.filter(t =>
    !tenantSearch.value ||
    (t.company_name || '').toLowerCase().includes(tenantSearch.value.toLowerCase()) ||
    t.username.toLowerCase().includes(tenantSearch.value.toLowerCase())
  )
)

function getOverride(key) {
  return overrides.value.find(o => o.feature_name === key) || null
}

function getCardClass(key) {
  const ov = getOverride(key)
  if (!ov) return ''
  return ov.enabled ? 'card-granted' : 'card-revoked'
}

function getSource(key) {
  const ov = getOverride(key)
  if (ov) return ov.enabled ? '✓ Overridden: GRANTED' : '✗ Overridden: REVOKED'
  return 'Using plan default'
}

async function selectTenant(t) {
  selectedTenant.value = t
  loadingOverrides.value = true
  overrides.value = []
  try {
    overrides.value = await api.getTenantFeatureOverrides(t.id) || []
  } catch {}
  loadingOverrides.value = false
}

async function setOverride(featureKey, enabled) {
  if (!selectedTenant.value) return
  saving.value = true
  try {
    const existing = getOverride(featureKey)
    await api.createFeatureOverride(selectedTenant.value.id, {
      feature_name: featureKey,
      enabled,
      reason: existing?.reason || '',
      expires_at: existing?.expires_at || null,
    })
    overrides.value = await api.getTenantFeatureOverrides(selectedTenant.value.id) || []
    overrideCounts.value[selectedTenant.value.id] = overrides.value.length
    flashSave('Saved!')
  } catch (e) {
    flashSave('Error: ' + (e.message || 'failed'))
  } finally {
    saving.value = false
  }
}

async function removeOverride(featureKey) {
  if (!selectedTenant.value) return
  const existing = getOverride(featureKey)
  if (!existing) return
  saving.value = true
  try {
    await api.deleteFeatureOverride(selectedTenant.value.id, existing.id)
    overrides.value = overrides.value.filter(o => o.id !== existing.id)
    overrideCounts.value[selectedTenant.value.id] = overrides.value.length
    flashSave('Reset to plan default')
  } catch {}
  saving.value = false
}

async function updateReason(featureKey, reason) {
  const ov = getOverride(featureKey)
  if (!ov) return
  saving.value = true
  try {
    await api.createFeatureOverride(selectedTenant.value.id, {
      feature_name: featureKey,
      enabled: ov.enabled,
      reason,
      expires_at: ov.expires_at,
    })
    overrides.value = await api.getTenantFeatureOverrides(selectedTenant.value.id) || []
    flashSave('Saved!')
  } catch {}
  saving.value = false
}

async function updateExpiry(featureKey, expiryStr) {
  const ov = getOverride(featureKey)
  if (!ov) return
  saving.value = true
  try {
    await api.createFeatureOverride(selectedTenant.value.id, {
      feature_name: featureKey,
      enabled: ov.enabled,
      reason: ov.reason,
      expires_at: expiryStr || null,
    })
    overrides.value = await api.getTenantFeatureOverrides(selectedTenant.value.id) || []
    flashSave('Expiry set!')
  } catch {}
  saving.value = false
}

function flashSave(msg) {
  saveMsg.value = msg
  setTimeout(() => { saveMsg.value = '' }, 2500)
}

onMounted(async () => {
  loadingTenants.value = true
  try {
    const data = await api.getTenants()
    tenants.value = data || []
    // Pre-load override counts
    await Promise.all(tenants.value.map(async t => {
      try {
        const ovs = await api.getTenantFeatureOverrides(t.id) || []
        if (ovs.length) overrideCounts.value[t.id] = ovs.length
      } catch {}
    }))
  } catch {}
  loadingTenants.value = false
})
</script>

<style scoped>
* { box-sizing: border-box; }
.perm-app { display: flex; min-height: 100vh; background: #0a0a0a; color: #e2e8f0; font-family: 'Inter', -apple-system, sans-serif; }
.perm-main { flex: 1; padding: 28px 32px; overflow-y: auto; }

.page-header { margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 4px; }

.perm-layout { display: flex; gap: 20px; height: calc(100vh - 130px); }

/* Left panel */
.tenant-list-panel {
  width: 260px; flex-shrink: 0;
  background: #111; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px;
  display: flex; flex-direction: column; overflow: hidden;
}
.panel-header { padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.search-input {
  width: 100%; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; padding: 8px 12px; font-size: 13px; color: #e2e8f0; outline: none;
  font-family: inherit;
}
.search-input::placeholder { color: #475569; }
.tenant-list { flex: 1; overflow-y: auto; padding: 8px; }
.tenant-row {
  display: flex; align-items: center; gap: 10px; padding: 10px 10px;
  border-radius: 9px; cursor: pointer; transition: background 0.12s; position: relative;
}
.tenant-row:hover { background: rgba(255,255,255,0.05); }
.tenant-row.selected { background: rgba(99,102,241,0.12); border: 1px solid rgba(99,102,241,0.3); }
.tenant-avatar {
  width: 34px; height: 34px; border-radius: 8px; background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.tenant-info { flex: 1; min-width: 0; }
.tenant-name { font-size: 13px; font-weight: 600; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tenant-plan { font-size: 11px; color: #64748b; display: flex; align-items: center; gap: 5px; margin-top: 2px; }
.plan-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-free { background: #94a3b8; }
.dot-starter { background: #60a5fa; }
.dot-growth { background: #34d399; }
.dot-pro { background: #a78bfa; }
.dot-none { background: #475569; }
.override-count {
  background: rgba(99,102,241,0.2); color: #a5b4fc; font-size: 10px; font-weight: 700;
  border-radius: 10px; padding: 2px 7px; flex-shrink: 0;
}
.no-tenants { padding: 20px; text-align: center; font-size: 13px; color: #475569; }
.panel-loading { display: flex; justify-content: center; padding: 24px; }
.spinner-sm { width: 22px; height: 22px; border: 2px solid rgba(255,255,255,0.1); border-top-color: #6366f1; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Right panel */
.permissions-panel {
  flex: 1; background: #111; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px;
  overflow-y: auto; padding: 24px;
}
.empty-prompt { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 14px; }
.empty-icon { font-size: 42px; }
.empty-msg { font-size: 14px; color: #475569; }

.perms-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.perms-title { font-size: 18px; font-weight: 700; color: #f1f5f9; }
.perms-sub { font-size: 13px; color: #64748b; margin-top: 4px; }
.perms-sub strong { color: #a5b4fc; }
.override-badge-inline { background: rgba(99,102,241,0.15); color: #a5b4fc; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
.save-flash { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 600; }

/* Feature groups */
.feat-group { margin-bottom: 28px; }
.group-label { font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px; }
.feat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }

.feat-card {
  background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 12px;
  padding: 14px; display: flex; flex-direction: column; gap: 12px; transition: border-color 0.15s;
}
.feat-card.card-granted { border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.04); }
.feat-card.card-revoked { border-color: rgba(239,68,68,0.35); background: rgba(239,68,68,0.04); }

.feat-top { display: flex; align-items: center; gap: 10px; }
.feat-icon { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05); border-radius: 7px; flex-shrink: 0; }
.feat-name { font-size: 13px; font-weight: 600; color: #f1f5f9; }
.feat-source { font-size: 11px; color: #64748b; margin-top: 2px; }
.card-granted .feat-source { color: #4ade80; }
.card-revoked .feat-source { color: #f87171; }

.feat-actions { display: flex; gap: 4px; }
.feat-btn {
  flex: 1; padding: 6px 4px; border-radius: 7px; font-size: 11px; font-weight: 600; cursor: pointer;
  border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.04); color: #64748b;
  font-family: inherit; transition: all 0.12s;
}
.feat-btn:hover:not(:disabled) { background: rgba(255,255,255,0.08); color: #94a3b8; }
.feat-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.grant-btn.active { background: rgba(34,197,94,0.15); border-color: rgba(34,197,94,0.4); color: #4ade80; }
.plan-btn.active  { background: rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.4); color: #a5b4fc; }
.revoke-btn.active { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.4); color: #f87171; }

.feat-override-info { display: flex; gap: 6px; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; flex-wrap: wrap; }
.ov-label { font-size: 10px; font-weight: 700; color: #6366f1; text-transform: uppercase; white-space: nowrap; }
.ov-reason, .ov-expiry {
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px; padding: 4px 8px; font-size: 11px; color: #e2e8f0; outline: none;
  font-family: inherit;
}
.ov-reason { flex: 1; min-width: 80px; }
.ov-expiry { width: 150px; }
</style>
