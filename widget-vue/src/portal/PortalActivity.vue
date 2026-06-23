<template>
  <div class="activity-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Visitor Activity</h1>
        <p class="page-sub">See which pages visitors explore and what they click on.</p>
      </div>
      <div class="period-tabs">
        <button
          v-for="p in periods"
          :key="p.value"
          class="period-tab"
          :class="{ active: days === p.value }"
          @click="setPeriod(p.value)"
        >{{ p.label }}</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="sk-row">
        <div class="sk-card" v-for="n in 4" :key="n"></div>
      </div>
      <div class="sk-block"></div>
    </div>

    <template v-else>
      <!-- Summary stats -->
      <div class="stats-row">
        <div class="stat-card" v-for="s in summaryStats" :key="s.label">
          <div class="stat-icon">{{ s.icon }}</div>
          <div class="stat-body">
            <div class="stat-num">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>

      <!-- No data empty state -->
      <div v-if="!pages.length && !loadingPages" class="empty-state">
        <div class="empty-icon">📊</div>
        <p class="empty-title">No activity yet</p>
        <p class="empty-sub">Visitor page activity will appear here once people start browsing your site.</p>
      </div>

      <template v-else>
        <!-- Most visited pages -->
        <div class="section-card">
          <div class="section-header">
            <h2 class="section-title">Most visited pages</h2>
            <span class="section-hint">{{ pages.length }} page{{ pages.length !== 1 ? 's' : '' }} tracked</span>
          </div>
          <div v-if="loadingPages" class="inline-loading">Loading pages…</div>
          <div v-else-if="!pages.length" class="inline-empty">No page visits recorded yet.</div>
          <div v-else class="pages-list">
            <div
              v-for="(p, i) in pages.slice(0, 10)"
              :key="p.page_url"
              class="page-row"
            >
              <span class="page-rank">{{ i + 1 }}</span>
              <div class="page-info">
                <span class="page-url" :title="p.page_url">{{ formatUrl(p.page_url) }}</span>
                <div class="page-bar-wrap">
                  <div
                    class="page-bar"
                    :style="{ width: pageBarWidth(p.total_clicks) + '%' }"
                  ></div>
                </div>
              </div>
              <div class="page-stats">
                <span class="page-clicks">{{ p.total_clicks.toLocaleString() }}</span>
                <span class="page-clicks-label">clicks</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Top interactions -->
        <div class="section-card" v-if="selectedPage">
          <div class="section-header">
            <h2 class="section-title">Top interactions</h2>
            <span class="section-hint">on {{ formatUrl(selectedPage) }}</span>
          </div>
          <div v-if="loadingHeatmap" class="inline-loading">Loading interactions…</div>
          <div v-else-if="!topElements.length" class="inline-empty">No interaction data for this page yet.</div>
          <div v-else class="elements-list">
            <div
              v-for="(el, i) in topElements"
              :key="i"
              class="element-row"
            >
              <div class="el-left">
                <span class="el-rank">{{ i + 1 }}</span>
                <div class="el-info">
                  <span class="el-text">{{ el.text || 'Unnamed element' }}</span>
                  <span class="el-tag">{{ el.tag }}</span>
                </div>
              </div>
              <div class="el-right">
                <div class="el-bar-wrap">
                  <div class="el-bar" :style="{ width: elBarWidth(el.count) + '%' }"></div>
                </div>
                <span class="el-count">{{ el.count }}×</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()

const periods = [
  { label: '24h', value: 1 },
  { label: '7 days', value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
]

const days = ref(7)
const pages = ref([])
const selectedPage = ref('')
const heatmapData = ref({ clusters: [], top_elements: [] })
const analytics = ref({})
const loading = ref(false)
const loadingPages = ref(false)
const loadingHeatmap = ref(false)

const topElements = computed(() => heatmapData.value.top_elements?.slice(0, 8) || [])

const summaryStats = computed(() => {
  const a = analytics.value
  return [
    { icon: '💬', label: 'Chat sessions', value: (a.total_sessions?.value ?? 0).toLocaleString() },
    { icon: '👥', label: 'Unique visitors', value: (a.unique_visitors?.value ?? 0).toLocaleString() },
    { icon: '📄', label: 'Page views', value: (a.analytics_events?.page_views ?? a.total_page_views ?? 0).toLocaleString() },
    { icon: '👆', label: 'Total clicks', value: pages.value.reduce((s, p) => s + (p.total_clicks || 0), 0).toLocaleString() },
  ]
})

function formatUrl(url) {
  if (!url) return ''
  try {
    const u = new URL(url.startsWith('http') ? url : `https://x.com${url}`)
    const path = u.pathname + (u.search || '')
    return path.length > 50 ? path.slice(0, 47) + '…' : path || '/'
  } catch {
    return url.length > 50 ? url.slice(0, 47) + '…' : url
  }
}

function pageBarWidth(clicks) {
  const max = Math.max(1, ...pages.value.map(p => p.total_clicks || 0))
  return Math.max(2, (clicks / max) * 100)
}

function elBarWidth(count) {
  const max = Math.max(1, ...topElements.value.map(e => e.count || 0))
  return Math.max(2, (count / max) * 100)
}

async function load() {
  if (!props.client) return
  loading.value = true
  try {
    const periodKey = days.value === 1 ? 'today' : days.value === 7 ? '7d' : days.value === 30 ? '30d' : '90d'
    const [pagesData, analyticsData] = await Promise.all([
      api.getActivityPages(props.client.id, days.value),
      api.getPortalAnalytics(props.client.id, periodKey),
    ])
    pages.value = pagesData?.pages || []
    analytics.value = analyticsData || {}
    if (pages.value.length) {
      selectedPage.value = pages.value[0].page_url
      loadTopInteractions()
    } else {
      selectedPage.value = ''
    }
  } catch {
    pages.value = []
    analytics.value = {}
  } finally {
    loading.value = false
  }
}

async function loadTopInteractions() {
  if (!props.client || !selectedPage.value) return
  loadingHeatmap.value = true
  try {
    const data = await api.getPageHeatmap(props.client.id, selectedPage.value, days.value)
    heatmapData.value = data || { clusters: [], top_elements: [] }
  } catch {
    heatmapData.value = { clusters: [], top_elements: [] }
  } finally {
    loadingHeatmap.value = false
  }
}

function setPeriod(val) {
  days.value = val
  load()
}

onMounted(load)
watch(() => props.client, load)
</script>

<style scoped>
* { box-sizing: border-box; }

.activity-page {
  padding: 28px 32px;
  font-family: 'Inter', -apple-system, sans-serif;
  max-width: 900px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--cf-text-primary);
  letter-spacing: -.4px;
  margin: 0 0 3px;
}
.page-sub { font-size: 13px; color: var(--cf-text-muted); margin: 0; }

.period-tabs {
  display: flex;
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-default);
  border-radius: 10px;
  padding: 3px;
  gap: 2px;
  flex-shrink: 0;
}
.period-tab {
  background: none;
  border: none;
  border-radius: 7px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--cf-text-muted);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.period-tab.active {
  background: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
}
.period-tab:hover:not(.active) { color: var(--cf-text-secondary); }

/* Stats */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-icon { font-size: 22px; flex-shrink: 0; }
.stat-num { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); line-height: 1; }
.stat-label { font-size: 11px; color: var(--cf-text-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }

/* Section cards */
.section-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 16px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--cf-text-primary);
  margin: 0;
}
.section-hint {
  font-size: 12px;
  color: var(--cf-text-muted);
}

/* Pages list */
.pages-list { display: flex; flex-direction: column; gap: 8px; }
.page-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--cf-bg-input);
  border-radius: 10px;
  transition: background 0.1s;
}
.page-row:hover { background: rgba(99, 102, 241, 0.06); }
.page-rank {
  width: 22px;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--cf-text-muted);
  text-align: center;
}
.page-info { flex: 1; min-width: 0; }
.page-url {
  display: block;
  font-size: 13px;
  color: var(--cf-text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}
.page-bar-wrap {
  height: 5px;
  background: var(--cf-bg-surface-raised);
  border-radius: 4px;
  overflow: hidden;
}
.page-bar {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  border-radius: 4px;
  transition: width 0.4s;
}
.page-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  min-width: 50px;
}
.page-clicks {
  font-size: 15px;
  font-weight: 700;
  color: var(--cf-text-primary);
  line-height: 1;
}
.page-clicks-label {
  font-size: 10px;
  color: var(--cf-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 2px;
}

/* Elements list */
.elements-list { display: flex; flex-direction: column; gap: 6px; }
.element-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--cf-bg-input);
  border-radius: 10px;
}
.el-left { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.el-rank {
  width: 22px;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--cf-text-muted);
  text-align: center;
}
.el-info { min-width: 0; }
.el-text {
  display: block;
  font-size: 13px;
  color: var(--cf-text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.el-tag {
  display: inline-block;
  margin-top: 2px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  font-weight: 600;
}
.el-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  width: 140px;
}
.el-bar-wrap {
  flex: 1;
  height: 5px;
  background: var(--cf-bg-surface-raised);
  border-radius: 4px;
  overflow: hidden;
}
.el-bar {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  border-radius: 4px;
  transition: width 0.4s;
}
.el-count {
  font-size: 13px;
  font-weight: 700;
  color: var(--cf-text-primary);
  white-space: nowrap;
}

/* Loading skeleton */
.loading-state { display: flex; flex-direction: column; gap: 16px; }
.sk-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.sk-card {
  height: 76px;
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}
.sk-block {
  height: 220px;
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 20px;
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  text-align: center;
}
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-title { font-size: 15px; font-weight: 600; color: var(--cf-text-secondary); margin: 0 0 6px; }
.empty-sub { font-size: 13px; color: var(--cf-text-muted); margin: 0; max-width: 340px; }

.inline-loading, .inline-empty {
  padding: 24px;
  text-align: center;
  color: var(--cf-text-muted);
  font-size: 13px;
}

@media (max-width: 768px) {
  .activity-page { padding: 20px 16px; }
  .page-header { flex-direction: column; gap: 12px; }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .sk-row { grid-template-columns: repeat(2, 1fr); }
  .period-tabs { align-self: flex-start; }
}
</style>
