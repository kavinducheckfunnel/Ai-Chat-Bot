<template>
  <div class="flex flex-col gap-6 p-6 h-full">

    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Permissions Manager</h1>
      <p class="text-sm text-muted-foreground mt-1">Control per-tenant feature access — override plan defaults for individual tenants</p>
    </div>

    <!-- Two-panel layout -->
    <div class="flex gap-4 flex-1 min-h-0">

      <!-- Left: tenant list -->
      <div class="w-64 shrink-0 flex flex-col rounded-xl border border-border bg-card overflow-hidden">
        <div class="p-3 border-b border-border">
          <input
            v-model="tenantSearch"
            class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Search tenants…"
          />
        </div>
        <div v-if="loadingTenants" class="flex justify-center p-6">
          <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
        <div v-else class="flex-1 overflow-y-auto p-2 space-y-0.5">
          <div
            v-for="t in filteredTenants" :key="t.id"
            class="flex items-center gap-2.5 rounded-md px-2.5 py-2 cursor-pointer transition-colors"
            :class="selectedTenant?.id === t.id ? 'bg-primary/10 border border-primary/30' : 'hover:bg-muted'"
            @click="selectTenant(t)"
          >
            <div class="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-violet-500 text-white text-[11px] font-bold flex items-center justify-center shrink-0">
              {{ (t.company_name || t.username).slice(0, 2).toUpperCase() }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-foreground truncate">{{ t.company_name || t.username }}</p>
              <div class="flex items-center gap-1.5 mt-0.5">
                <span class="h-1.5 w-1.5 rounded-full shrink-0" :class="planDotClass(t.plan)"></span>
                <span class="text-xs text-muted-foreground">{{ t.plan || 'No plan' }}</span>
              </div>
            </div>
            <span v-if="overrideCounts[t.id]" class="inline-flex rounded-full bg-primary/15 text-primary px-1.5 py-0.5 text-[10px] font-bold">
              {{ overrideCounts[t.id] }}
            </span>
          </div>
          <div v-if="!filteredTenants.length" class="py-5 text-center text-sm text-muted-foreground">No tenants found</div>
        </div>
      </div>

      <!-- Right: permissions panel -->
      <div class="flex-1 rounded-xl border border-border bg-card overflow-y-auto p-5">

        <!-- Empty state -->
        <div v-if="!selectedTenant" class="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
          <Lock class="h-8 w-8 opacity-40" />
          <p class="text-sm">Select a tenant to manage their permissions</p>
        </div>

        <template v-else>
          <!-- Header -->
          <div class="flex items-start justify-between mb-6">
            <div>
              <h2 class="text-lg font-bold text-foreground">{{ selectedTenant.company_name || selectedTenant.username }}</h2>
              <p class="text-sm text-muted-foreground mt-0.5">
                Plan: <strong class="text-foreground">{{ selectedTenant.plan || 'None' }}</strong>
                <span v-if="overrides.length" class="ml-2 inline-flex rounded-full bg-primary/15 text-primary px-2 py-0.5 text-[10px] font-bold">
                  {{ overrides.length }} override{{ overrides.length !== 1 ? 's' : '' }}
                </span>
              </p>
            </div>
            <div v-if="saveMsg" class="inline-flex rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-600">
              {{ saveMsg }}
            </div>
          </div>

          <div v-if="loadingOverrides" class="flex justify-center py-12">
            <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
          </div>

          <template v-else>
            <div v-for="group in featureGroups" :key="group.label" class="mb-7">
              <h3 class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-3">{{ group.label }}</h3>
              <div class="grid gap-2.5" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))">
                <div
                  v-for="feat in group.features" :key="feat.key"
                  class="rounded-xl border p-3.5 flex flex-col gap-3 transition-colors"
                  :class="getCardClass(feat.key)"
                >
                  <!-- Feature info -->
                  <div class="flex items-center gap-2.5">
                    <div class="h-7 w-7 rounded-lg bg-muted flex items-center justify-center shrink-0" v-html="feat.icon"></div>
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-semibold text-foreground">{{ feat.label }}</p>
                      <p class="text-[11px] mt-0.5" :class="getSourceClass(feat.key)">{{ getSource(feat.key) }}</p>
                    </div>
                  </div>

                  <!-- Action buttons -->
                  <div class="flex gap-1.5">
                    <button
                      class="flex-1 rounded-md border py-1 text-[11px] font-semibold transition-colors"
                      :class="getOverride(feat.key)?.enabled === true ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-border text-muted-foreground hover:bg-muted'"
                      @click="setOverride(feat.key, true)"
                      :disabled="saving"
                    >Grant</button>
                    <button
                      class="flex-1 rounded-md border py-1 text-[11px] font-semibold transition-colors"
                      :class="!getOverride(feat.key) ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-muted'"
                      @click="removeOverride(feat.key)"
                      :disabled="saving"
                    >Plan Default</button>
                    <button
                      class="flex-1 rounded-md border py-1 text-[11px] font-semibold transition-colors"
                      :class="getOverride(feat.key)?.enabled === false ? 'border-red-300 bg-red-50 text-red-700' : 'border-border text-muted-foreground hover:bg-muted'"
                      @click="setOverride(feat.key, false)"
                      :disabled="saving"
                    >Revoke</button>
                  </div>

                  <!-- Override details -->
                  <div v-if="getOverride(feat.key)" class="flex items-center gap-2 pt-2 border-t border-border flex-wrap">
                    <span class="text-[10px] font-bold text-primary uppercase">Override</span>
                    <input
                      class="flex-1 min-w-20 rounded border border-input bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      type="text"
                      placeholder="Reason…"
                      :value="getOverride(feat.key).reason"
                      @change="updateReason(feat.key, $event.target.value)"
                    />
                    <input
                      class="rounded border border-input bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      style="width:150px"
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Loader2, Lock } from 'lucide-vue-next'
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
      { key: 'allow_whatsapp',  label: 'WhatsApp Business', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="#25d366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884"/></svg>' },
      { key: 'allow_telegram',  label: 'Telegram Bot',      icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#0088cc" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>' },
      { key: 'allow_messenger', label: 'FB Messenger',      icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="#0084FF"><path d="M12 2C6.477 2 2 6.145 2 11.243c0 2.842 1.358 5.38 3.504 7.106V22l3.36-1.847A10.94 10.94 0 0012 20.486c5.523 0 10-4.145 10-9.243S17.523 2 12 2z"/></svg>' },
    ],
  },
  {
    label: 'AI & Knowledge',
    features: [
      { key: 'allow_byok',        label: 'Custom AI (BYOK)',     icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#c084fc" stroke-width="2"><path d="M21 2H3v16h5v4l4-4h9V2z"/></svg>' },
      { key: 'allow_voice_input', label: 'Voice Input',          icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#60a5fa" stroke-width="2"><path d="M12 1a3 3 0 013 3v8a3 3 0 11-6 0V4a3 3 0 013-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"/></svg>' },
      { key: 'allow_image_input', label: 'Image Input',          icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#34d399" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>' },
    ],
  },
  {
    label: 'Integrations',
    features: [
      { key: 'allow_hubspot',  label: 'HubSpot CRM',        icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#ff7a00" stroke-width="2"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg>' },
      { key: 'allow_slack',    label: 'Slack Notifications', icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#4a154b" stroke-width="2"><rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="2" y="14" width="8" height="8" rx="2"/><rect x="14" y="14" width="8" height="8" rx="2"/></svg>' },
      { key: 'allow_webhooks', label: 'Outbound Webhooks',   icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#f97316" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>' },
    ],
  },
  {
    label: 'Inbox & Support',
    features: [
      { key: 'allow_god_view',          label: 'Live Takeover',      icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#a78bfa" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' },
      { key: 'allow_canned_responses',  label: 'Canned Responses',   icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#38bdf8" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>' },
      { key: 'allow_conversation_tags', label: 'Conversation Tags',  icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#fbbf24" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>' },
      { key: 'allow_csv_export',        label: 'CSV Export',         icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#86efac" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' },
    ],
  },
  {
    label: 'Branding & Advanced',
    features: [
      { key: 'remove_branding',     label: 'Remove Branding',  icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#f472b6" stroke-width="2"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/></svg>' },
      { key: 'allow_custom_domain', label: 'Custom Domain',    icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#e879f9" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/></svg>' },
      { key: 'allow_api_access',    label: 'API Access',       icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#94a3b8" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>' },
      { key: 'allow_fomo_triggers', label: 'FOMO Triggers',    icon: '<svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#fb923c" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>' },
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

function planDotClass(plan) {
  const map = { free: 'bg-slate-400', starter: 'bg-blue-400', growth: 'bg-emerald-400', pro: 'bg-violet-400' }
  return map[(plan || '').toLowerCase()] || 'bg-muted-foreground'
}

function getOverride(key) {
  return overrides.value.find(o => o.feature_name === key) || null
}

function getCardClass(key) {
  const ov = getOverride(key)
  if (!ov) return 'border-border'
  return ov.enabled ? 'border-emerald-200 bg-emerald-50/30' : 'border-red-200 bg-red-50/30'
}

function getSourceClass(key) {
  const ov = getOverride(key)
  if (!ov) return 'text-muted-foreground'
  return ov.enabled ? 'text-emerald-600' : 'text-red-500'
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
      feature_name: featureKey, enabled,
      reason: existing?.reason || '', expires_at: existing?.expires_at || null,
    })
    overrides.value = await api.getTenantFeatureOverrides(selectedTenant.value.id) || []
    overrideCounts.value[selectedTenant.value.id] = overrides.value.length
    flashSave('Saved!')
  } catch (e) {
    flashSave('Error: ' + (e.message || 'failed'))
  } finally { saving.value = false }
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
    await api.createFeatureOverride(selectedTenant.value.id, { feature_name: featureKey, enabled: ov.enabled, reason, expires_at: ov.expires_at })
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
    await api.createFeatureOverride(selectedTenant.value.id, { feature_name: featureKey, enabled: ov.enabled, reason: ov.reason, expires_at: expiryStr || null })
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
