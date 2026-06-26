<template>
  <div class="referrals-page">
    <div class="rf-header">
      <div>
        <h1 class="rf-title">Referrals</h1>
        <p class="rf-sub">Products and pages your chatbot sent visitors to — track which links the AI drives traffic to.</p>
      </div>
      <div class="rf-actions">
        <PortalDateFilter v-model="period" @change="onDateChange" />
        <button class="rf-export" :disabled="!links.length" @click="exportCSV">⬇ Export CSV</button>
      </div>
    </div>

    <!-- Summary -->
    <div class="rf-summary">
      <div class="rf-sum-card">
        <div class="rf-sum-num">{{ totalClicks }}</div>
        <div class="rf-sum-lbl">total link clicks</div>
      </div>
      <div class="rf-sum-card">
        <div class="rf-sum-num">{{ links.length }}</div>
        <div class="rf-sum-lbl">products referred</div>
      </div>
      <div class="rf-sum-card">
        <div class="rf-sum-num">{{ uniqueTotal }}</div>
        <div class="rf-sum-lbl">unique visitors referred</div>
      </div>
    </div>

    <!-- Table -->
    <div class="rf-card">
      <div v-if="loading" class="rf-empty">Loading…</div>
      <table v-else-if="links.length" class="rf-table">
        <thead>
          <tr><th>Product / Link</th><th class="num">Clicks</th><th class="num">Unique visitors</th></tr>
        </thead>
        <tbody>
          <tr v-for="(l, i) in links" :key="i">
            <td>
              <a :href="l.url" target="_blank" rel="noopener" class="rf-link">{{ l.link_text || l.url }}</a>
              <div class="rf-url">{{ l.url }}</div>
            </td>
            <td class="num"><strong>{{ l.clicks }}</strong></td>
            <td class="num">{{ l.unique_sessions }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="rf-empty">
        <div class="rf-empty-icon">🔗</div>
        <p class="rf-empty-title">No referrals yet</p>
        <p class="rf-empty-sub">
          When your chatbot recommends a product and a visitor clicks the link,
          it shows up here with click and unique-visitor counts — so you can see
          exactly what the AI is driving traffic to.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, inject, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'
import PortalDateFilter from './PortalDateFilter.vue'

const api = useAdminApi()
const client = inject('portalClient', ref(null))

const period = ref('30d')
const dateRange = ref({ period: '30d', dateFrom: null, dateTo: null })
const loading = ref(false)
const links = ref([])
const totalClicks = ref(0)

const uniqueTotal = computed(() =>
  links.value.reduce((sum, l) => sum + (l.unique_sessions || 0), 0)
)

async function load() {
  const c = client.value
  if (!c || !c.id) return
  loading.value = true
  try {
    const dr = dateRange.value
    const data = await api.getClientLinkClicks(c.id, { period: dr.period, dateFrom: dr.dateFrom, dateTo: dr.dateTo })
    links.value = (data && Array.isArray(data.links)) ? data.links : []
    totalClicks.value = (data && data.total_clicks) || 0
  } catch {
    links.value = []
    totalClicks.value = 0
  } finally {
    loading.value = false
  }
}
function onDateChange(p) { dateRange.value = p; load() }
function exportCSV() {
  if (!links.value.length) return
  const head = ['Product / Link', 'URL', 'Clicks', 'Unique visitors']
  const esc = (v) => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`
  const csv = [head.map(esc).join(',')]
    .concat(links.value.map(l => [l.link_text || '', l.url || '', l.clicks ?? 0, l.unique_sessions ?? 0].map(esc).join(',')))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `chatbot_referrals_${period.value}.csv`
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

onMounted(load)
onActivated(load)
// The client is resolved asynchronously by PortalLayout — load once it arrives.
watch(client, (c) => { if (c && c.id) load() })
</script>

<style scoped>
.referrals-page { padding: 32px 36px; max-width: 1000px; }
.rf-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 22px; }
.rf-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.4px; margin: 0 0 4px; }
.rf-sub { font-size: 13px; color: var(--cf-text-muted); margin: 0; line-height: 1.5; max-width: 560px; }
.rf-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rf-period { display: flex; gap: 3px; background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-subtle); border-radius: 9px; padding: 3px; }
.rf-period-btn { padding: 6px 13px; background: none; border: none; border-radius: 6px; font-size: 12px; font-weight: 500; color: var(--cf-text-muted); cursor: pointer; white-space: nowrap; }
.rf-period-btn.active { background: rgba(99,102,241,0.15); color: #a5b4fc; }
.rf-export { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.25); border-radius: 9px; font-size: 12px; font-weight: 500; color: #a5b4fc; cursor: pointer; }
.rf-export:hover:not(:disabled) { background: rgba(99,102,241,0.2); }
.rf-export:disabled { opacity: 0.5; cursor: not-allowed; }

.rf-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 18px; }
.rf-sum-card { background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-subtle); border-radius: 14px; padding: 18px 20px; }
.rf-sum-num { font-size: 28px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -0.5px; }
.rf-sum-lbl { font-size: 12px; color: var(--cf-text-muted); margin-top: 4px; }

.rf-card { background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-subtle); border-radius: 14px; padding: 6px; overflow-x: auto; }
.rf-table { width: 100%; min-width: 520px; border-collapse: collapse; }
.rf-table th { text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--cf-text-muted); padding: 12px 14px; border-bottom: 1px solid var(--cf-border-subtle); white-space: nowrap; }
.rf-table th.num, .rf-table td.num { text-align: right; }
.rf-table td { padding: 12px 14px; font-size: 13px; color: var(--cf-text-secondary); border-bottom: 1px solid var(--cf-border-subtle); vertical-align: top; }
.rf-table tr:last-child td { border-bottom: none; }
.rf-link { color: #a5b4fc; text-decoration: none; font-weight: 500; word-break: break-word; }
.rf-link:hover { text-decoration: underline; }
.rf-url { font-size: 11px; color: var(--cf-text-muted); margin-top: 2px; word-break: break-all; max-width: 480px; }
.rf-empty { text-align: center; padding: 52px 20px; color: var(--cf-text-muted); }
.rf-empty-icon { font-size: 34px; margin-bottom: 12px; }
.rf-empty-title { font-size: 15px; font-weight: 600; color: var(--cf-text-secondary); margin: 0 0 6px; }
.rf-empty-sub { font-size: 13px; max-width: 440px; margin: 0 auto; line-height: 1.55; }

@media (max-width: 720px) { .rf-summary { grid-template-columns: 1fr; } .referrals-page { padding: 24px 18px; } }
</style>
