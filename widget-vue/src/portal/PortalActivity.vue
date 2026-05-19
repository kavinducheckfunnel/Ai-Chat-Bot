<template>
  <div class="activity-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Activity heatmap</h1>
        <p class="page-sub">See where visitors click on each page of your site.</p>
      </div>
      <div class="header-controls">
        <select class="period-select" v-model.number="days" @change="loadPages">
          <option :value="1">Last 24 hours</option>
          <option :value="7">Last 7 days</option>
          <option :value="30">Last 30 days</option>
          <option :value="90">Last 90 days</option>
        </select>
      </div>
    </div>

    <!-- Page selector -->
    <div class="page-selector-wrap">
      <label class="selector-label">Page</label>
      <select class="page-selector" v-model="selectedPage" @change="loadHeatmap">
        <option v-if="!pages.length" disabled value="">No activity yet — visitors haven't clicked anything</option>
        <option v-for="p in pages" :key="p.page_url" :value="p.page_url">
          {{ p.page_url }} ({{ p.total_clicks }} clicks)
        </option>
      </select>
    </div>

    <div v-if="loading" class="loading-block">Loading activity…</div>

    <div v-else-if="!selectedPage" class="empty-block">
      <svg width="48" height="48" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#334155" stroke-width="1.5"/><path d="M12 8v4M12 16h.01" stroke="#334155" stroke-width="2" stroke-linecap="round"/></svg>
      <p class="empty-title">No page selected</p>
      <p class="empty-sub">Pick a page from the dropdown to see its heatmap.</p>
    </div>

    <div v-else class="heatmap-container">
      <!-- Stats row -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-num">{{ heatmap.total_clicks || 0 }}</div>
          <div class="stat-lbl">Total clicks</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ heatmap.unique_visitors || 0 }}</div>
          <div class="stat-lbl">Unique visitors</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ heatmap.clusters?.length || 0 }}</div>
          <div class="stat-lbl">Hot spots</div>
        </div>
      </div>

      <!-- Heatmap visualization -->
      <div class="heatmap-section">
        <div class="section-head">
          <h2 class="section-title">Click heatmap</h2>
          <div class="legend">
            <span class="legend-item"><span class="legend-dot legend-cta"></span>CTA click</span>
            <span class="legend-item"><span class="legend-dot legend-normal"></span>Regular click</span>
            <span class="legend-item"><span class="legend-dot legend-rage"></span>Rage click</span>
          </div>
        </div>
        <div class="heatmap-canvas" ref="canvasWrap">
          <div v-if="!heatmap.clusters?.length" class="heatmap-empty">
            No clicks recorded on this page yet.
          </div>
          <template v-else>
            <div class="grid-overlay"></div>
            <div
              v-for="(c, i) in heatmap.clusters"
              :key="i"
              class="heat-dot"
              :class="[
                c.is_rage ? 'dot-rage' : c.is_cta ? 'dot-cta' : 'dot-normal'
              ]"
              :style="{
                left: c.x + '%',
                top: Math.min(c.y, 95) + '%',
                width: dotSize(c.count) + 'px',
                height: dotSize(c.count) + 'px',
                opacity: dotOpacity(c.count),
              }"
              :title="(c.text || 'Click') + ' — ' + c.count + ' clicks'"
            >
              <span class="dot-count">{{ c.count }}</span>
              <span v-if="c.text" class="dot-label">{{ c.text.slice(0, 20) }}</span>
            </div>
          </template>
        </div>
      </div>

      <!-- Top elements -->
      <div class="elements-section">
        <h2 class="section-title">Top clicked elements</h2>
        <div v-if="!heatmap.top_elements?.length" class="empty-inline">No element data yet.</div>
        <div v-else class="elements-list">
          <div
            v-for="(el, i) in heatmap.top_elements"
            :key="i"
            class="element-row"
          >
            <span class="el-rank">{{ i + 1 }}</span>
            <span class="el-text">{{ el.text }}</span>
            <span class="el-tag">{{ el.tag }}</span>
            <div class="el-bar-wrap">
              <div class="el-bar" :style="{ width: barWidth(el.count) + '%' }"></div>
            </div>
            <span class="el-count">{{ el.count }}×</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()

const days = ref(7)
const pages = ref([])
const selectedPage = ref('')
const heatmap = ref({ clusters: [], top_elements: [] })
const loading = ref(false)

async function loadPages() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getActivityPages(props.client.id, days.value)
    pages.value = data?.pages || []
    if (pages.value.length && !pages.value.find(p => p.page_url === selectedPage.value)) {
      selectedPage.value = pages.value[0].page_url
      await loadHeatmap()
    } else if (selectedPage.value) {
      await loadHeatmap()
    }
  } catch (e) {
    pages.value = []
  } finally {
    loading.value = false
  }
}

async function loadHeatmap() {
  if (!props.client || !selectedPage.value) return
  loading.value = true
  try {
    const data = await api.getPageHeatmap(props.client.id, selectedPage.value, days.value)
    heatmap.value = data || { clusters: [], top_elements: [] }
  } catch (e) {
    heatmap.value = { clusters: [], top_elements: [] }
  } finally {
    loading.value = false
  }
}

// Dot rendering helpers
const maxCount = () => Math.max(1, ...(heatmap.value.clusters || []).map(c => c.count))
function dotSize(count) {
  const m = maxCount()
  return Math.max(18, Math.min(80, 18 + (count / m) * 62))
}
function dotOpacity(count) {
  const m = maxCount()
  return 0.45 + (count / m) * 0.5
}
function barWidth(count) {
  const m = Math.max(1, ...(heatmap.value.top_elements || []).map(e => e.count))
  return (count / m) * 100
}

onMounted(loadPages)
watch(() => props.client, loadPages)
</script>

<style scoped>
* { box-sizing: border-box; }

.activity-page {
  padding: 28px 32px;
  font-family: 'Inter', -apple-system, sans-serif;
}
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 24px;
}
.page-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -.4px; }
.page-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 3px; }

.period-select, .page-selector {
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-default);
  color: var(--cf-text-primary);
  border-radius: 8px; padding: 8px 12px;
  font-size: 13px; font-family: inherit;
  cursor: pointer; outline: none;
}

.page-selector-wrap {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 20px;
}
.selector-label {
  font-size: 12px; font-weight: 600; color: var(--cf-text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.page-selector {
  flex: 1; max-width: 520px;
}

.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
.stat-card {
  background: var(--cf-bg-card);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px; padding: 16px;
}
.stat-num { font-size: 24px; font-weight: 700; color: var(--cf-text-primary); }
.stat-lbl { font-size: 12px; color: var(--cf-text-muted); margin-top: 4px; }

.section-title { font-size: 15px; font-weight: 600; color: var(--cf-text-primary); margin-bottom: 12px; }
.section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.legend { display: flex; gap: 14px; font-size: 11px; color: var(--cf-text-muted); }
.legend-item { display: flex; align-items: center; gap: 5px; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.legend-cta { background: #f59e0b; }
.legend-normal { background: #6366f1; }
.legend-rage { background: #ef4444; }

.heatmap-section {
  background: var(--cf-bg-card);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px; padding: 16px; margin-bottom: 24px;
}
.heatmap-canvas {
  position: relative; width: 100%; height: 560px;
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 8px;
  overflow: hidden;
}
.grid-overlay {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(148,163,184,0.10) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148,163,184,0.10) 1px, transparent 1px);
  background-size: 10% 10%;
  pointer-events: none;
}
.heat-dot {
  position: absolute;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  color: #fff; font-weight: 700;
  cursor: pointer;
  transition: transform .15s;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.heat-dot:hover { transform: translate(-50%, -50%) scale(1.15); z-index: 10; }
.dot-normal { background: radial-gradient(circle, #6366f1 0%, #4338ca 100%); }
.dot-cta { background: radial-gradient(circle, #f59e0b 0%, #d97706 100%); }
.dot-rage { background: radial-gradient(circle, #ef4444 0%, #b91c1c 100%); }
.dot-count { font-size: 11px; line-height: 1; }
.dot-label {
  position: absolute; top: calc(100% + 4px); left: 50%;
  transform: translateX(-50%);
  font-size: 10px; color: var(--cf-text-secondary);
  background: var(--cf-bg-card);
  padding: 2px 6px; border-radius: 4px;
  white-space: nowrap;
  border: 1px solid var(--cf-border-subtle);
  opacity: 0; pointer-events: none;
  transition: opacity .15s;
}
.heat-dot:hover .dot-label { opacity: 1; }
.heatmap-empty {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: var(--cf-text-muted); font-size: 13px;
}

.elements-section {
  background: var(--cf-bg-card);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px; padding: 16px;
}
.elements-list { display: flex; flex-direction: column; gap: 6px; }
.element-row {
  display: grid;
  grid-template-columns: 24px 1fr auto 120px 50px;
  gap: 10px;
  align-items: center;
  padding: 8px 12px;
  background: var(--cf-bg-input);
  border-radius: 8px;
  font-size: 13px;
}
.el-rank { color: var(--cf-text-muted); font-weight: 600; font-size: 12px; }
.el-text { color: var(--cf-text-primary); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.el-tag {
  background: rgba(99,102,241,0.15); color: #a5b4fc;
  font-size: 10px; padding: 2px 7px; border-radius: 5px;
  text-transform: uppercase; font-weight: 600;
}
.el-bar-wrap {
  height: 6px; background: var(--cf-bg-card);
  border-radius: 4px; overflow: hidden;
}
.el-bar { height: 100%; background: linear-gradient(90deg, #6366f1, #a855f7); }
.el-count { font-weight: 700; color: var(--cf-text-primary); text-align: right; }

.loading-block, .empty-block {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 80px 20px; text-align: center;
  background: var(--cf-bg-card);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
}
.empty-title { font-size: 14px; font-weight: 600; color: var(--cf-text-secondary); margin-top: 12px; }
.empty-sub { font-size: 12px; color: var(--cf-text-muted); margin-top: 4px; }
.empty-inline { padding: 16px; text-align: center; color: var(--cf-text-muted); font-size: 13px; }

@media (max-width: 768px) {
  .activity-page { padding: 20px 16px; }
  .page-header { flex-direction: column; gap: 12px; }
  .stats-row { grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .stat-num { font-size: 18px; }
  .heatmap-canvas { height: 380px; }
  .element-row { grid-template-columns: 20px 1fr 60px; gap: 6px; font-size: 12px; }
  .el-tag, .el-bar-wrap { display: none; }
}
</style>
