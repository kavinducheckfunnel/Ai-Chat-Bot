<template>
  <div class="visitors-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Visitors</h1>
        <p class="page-sub">One row per real person — across all their sessions.</p>
      </div>
      <div class="header-controls">
        <input class="search-input" v-model="search" placeholder="Search email or ID…" @keydown.enter="loadVisitors" />
        <select class="period-select" v-model.number="days" @change="loadVisitors">
          <option :value="1">Last 24h</option>
          <option :value="7">Last 7 days</option>
          <option :value="30">Last 30 days</option>
          <option :value="0">All time</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading-block">Loading visitors…</div>

    <div v-else-if="!selectedVisitor" class="visitors-grid">
      <div v-if="!visitors.length" class="empty-block">
        <svg width="40" height="40" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" stroke="#334155" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p class="empty-title">No visitors yet</p>
        <p class="empty-sub">Visitors will appear after they browse your site with the chat widget installed.</p>
      </div>

      <div
        v-for="v in visitors"
        :key="v.visitor_uid"
        class="visitor-card"
        @click="selectVisitor(v)"
      >
        <div class="visitor-head">
          <div class="visitor-avatar" :style="{ background: heatColor(v.heat_score) }">
            {{ initials(v) }}
          </div>
          <div class="visitor-meta">
            <div class="visitor-name">
              {{ v.lead_email || ('Visitor ' + v.visitor_uid.slice(0, 8)) }}
              <span v-if="v.country_code" class="flag">{{ countryFlag(v.country_code) }}</span>
            </div>
            <div class="visitor-sub">{{ formatLastSeen(v.last_seen) }}</div>
          </div>
          <div class="heat-pill" :style="{ background: heatColor(v.heat_score) }">{{ Math.round(v.heat_score) }}%</div>
        </div>

        <div class="visitor-stats">
          <div class="stat-item"><span class="stat-num">{{ v.total_sessions }}</span><span class="stat-lbl">sessions</span></div>
          <div class="stat-item"><span class="stat-num">{{ v.total_messages }}</span><span class="stat-lbl">messages</span></div>
          <div class="stat-item"><span class="stat-num">{{ v.total_page_views }}</span><span class="stat-lbl">page views</span></div>
          <div class="stat-item"><span class="stat-num">{{ formatTime(v.total_time_seconds) }}</span><span class="stat-lbl">total time</span></div>
        </div>

        <div v-if="v.top_interest_title" class="top-interest">
          🎯 Most interested in: <strong>{{ v.top_interest_title }}</strong>
        </div>

        <div class="visitor-tags">
          <span v-if="v.device" class="visitor-tag">{{ v.device }}{{ v.os ? ' · ' + v.os : '' }}</span>
          <span v-if="v.city || v.country" class="visitor-tag">{{ [v.city, v.country].filter(Boolean).join(', ') }}</span>
        </div>
      </div>
    </div>

    <!-- Detail view -->
    <div v-else class="visitor-detail">
      <button class="back-btn" @click="selectedVisitor = null">← Back to all visitors</button>

      <div class="detail-head">
        <div class="visitor-avatar large" :style="{ background: heatColor(detail.heat_score || 0) }">
          {{ initials(detail) }}
        </div>
        <div>
          <h2 class="detail-name">{{ detail.lead_email || 'Visitor ' + detail.visitor_uid.slice(0, 8) }}</h2>
          <p class="detail-sub">First seen {{ formatDate(detail.first_seen) }} · Last seen {{ formatLastSeen(detail.last_seen) }}</p>
        </div>
      </div>

      <div class="detail-stats-row">
        <div class="detail-stat-card">
          <div class="stat-num large">{{ detail.sessions?.length || 0 }}</div>
          <div class="stat-lbl">Sessions</div>
        </div>
        <div class="detail-stat-card">
          <div class="stat-num large">{{ Math.round((detail.intent_ema || 0) * 100) }}%</div>
          <div class="stat-lbl">Intent</div>
        </div>
        <div class="detail-stat-card">
          <div class="stat-num large">{{ Math.round((detail.budget_ema || 0) * 100) }}%</div>
          <div class="stat-lbl">Budget</div>
        </div>
        <div class="detail-stat-card">
          <div class="stat-num large">{{ Math.round((detail.urgency_ema || 0) * 100) }}%</div>
          <div class="stat-lbl">Urgency</div>
        </div>
      </div>

      <!-- Sessions list -->
      <div class="detail-section">
        <h3 class="section-title">All sessions ({{ detail.sessions?.length || 0 }})</h3>
        <div class="sessions-list">
          <div v-for="s in detail.sessions" :key="s.session_id" class="session-row">
            <div class="sess-id">{{ s.session_id.slice(0, 8) }}…</div>
            <div class="sess-info">
              {{ s.message_count }} messages · {{ s.page_count }} pages · {{ s.kanban_state }}
            </div>
            <div class="sess-time">{{ formatDate(s.created_at) }}</div>
            <div class="sess-heat" :style="{ background: heatColor(s.heat_score) }">{{ Math.round(s.heat_score) }}%</div>
          </div>
        </div>
      </div>

      <!-- Unified timeline -->
      <div class="detail-section">
        <h3 class="section-title">Activity timeline ({{ detail.timeline?.length || 0 }})</h3>
        <div class="timeline-scroll">
          <div v-for="(ev, i) in (detail.timeline || []).slice().reverse()" :key="i" class="timeline-event">
            <span class="ev-icon">{{ eventIcon(ev.event_type) }}</span>
            <div class="ev-body">
              <div class="ev-label">{{ eventLabel(ev) }}</div>
              <div class="ev-meta">{{ formatLastSeen(ev.created_at) }}<span v-if="ev.page_url"> · {{ ev.page_url }}</span></div>
            </div>
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

const visitors = ref([])
const loading = ref(false)
const search = ref('')
const days = ref(7)
const selectedVisitor = ref(null)
const detail = ref({})

async function loadVisitors() {
  if (!props.client) return
  loading.value = true
  try {
    const params = {}
    if (days.value > 0) params.days = days.value
    if (search.value.trim()) params.q = search.value.trim()
    const data = await api.getClientVisitors(props.client.id, params)
    visitors.value = data?.visitors || []
  } finally {
    loading.value = false
  }
}

async function selectVisitor(v) {
  loading.value = true
  selectedVisitor.value = v
  try {
    const data = await api.getVisitorDetail(v.visitor_uid, props.client.id)
    detail.value = data || {}
  } catch {
    detail.value = {}
  } finally {
    loading.value = false
  }
}

function initials(v) {
  if (v.lead_email) return v.lead_email[0].toUpperCase()
  if (v.lead_name) return v.lead_name[0].toUpperCase()
  return (v.visitor_uid || '?')[0].toUpperCase()
}

function heatColor(score) {
  if (!score) return '#475569'
  if (score > 70) return '#ef4444'
  if (score > 40) return '#f59e0b'
  return '#6366f1'
}

function countryFlag(code) {
  if (!code || code.length !== 2) return ''
  return [...code.toUpperCase()].map(c => String.fromCodePoint(c.codePointAt(0) + 127397)).join('')
}

function formatTime(secs) {
  if (!secs) return '0s'
  const m = Math.floor(secs / 60)
  const s = secs % 60
  if (m === 0) return `${s}s`
  if (m < 60) return `${m}m`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}

function formatLastSeen(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const diff = Date.now() - d.getTime()
    if (diff < 60000) return 'just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    if (diff < 7 * 86400000) return `${Math.floor(diff / 86400000)}d ago`
    return d.toLocaleDateString()
  } catch { return iso.slice(0, 10) }
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })
  } catch { return iso.slice(0, 16) }
}

function eventIcon(t) {
  const map = {
    click: '👆', cta_click: '⭐', add_to_cart: '🛒', rage_click: '😤',
    form_focus: '✍️', form_abandoned: '⏸', copy: '📋',
    page_view: '📄', pricing_visit: '💰', exit_intent: '🚪',
    chat_user: '💬', chat_ai: '🤖',
  }
  return map[t] || '•'
}

function eventLabel(ev) {
  const p = ev.payload || {}
  switch (ev.event_type) {
    case 'click':       return `Clicked "${(p.text || 'element').slice(0, 60)}"`
    case 'cta_click':   return `CTA click: "${(p.text || '').slice(0, 60)}"`
    case 'add_to_cart': return `🛒 Added to cart: "${(p.text || 'item').slice(0, 60)}"`
    case 'rage_click':  return 'Rage-clicked (frustration)'
    case 'form_focus':  return 'Started filling a form'
    case 'form_abandoned': return 'Abandoned a form'
    case 'copy':        return `Copied: "${(p.value || p.text || '').slice(0, 40)}"`
    case 'page_view':   return `Viewed ${p.page_title || ev.page_url || '(page)'}` +
                               (p.duration_seconds ? ` (${formatTime(p.duration_seconds)})` : '')
    case 'pricing_visit': return 'Viewed pricing page'
    case 'exit_intent': return 'Tried to leave the site'
    case 'chat_user':   return `Said: "${(p.message || '').slice(0, 80)}"`
    case 'chat_ai':     return `AI replied: "${(p.message || '').slice(0, 80)}"`
    default:            return ev.event_type
  }
}

onMounted(loadVisitors)
watch(() => props.client, loadVisitors)
</script>

<style scoped>
.visitors-page { padding: 28px 32px; font-family: 'Inter', -apple-system, sans-serif; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; gap: 16px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); letter-spacing: -.4px; }
.page-sub { font-size: 13px; color: var(--cf-text-muted); margin-top: 3px; }
.header-controls { display: flex; gap: 8px; }
.search-input, .period-select {
  background: var(--cf-bg-input); border: 1px solid var(--cf-border-default);
  color: var(--cf-text-primary); border-radius: 8px; padding: 8px 12px;
  font-size: 13px; font-family: inherit; outline: none;
}
.search-input { width: 220px; }

.visitors-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px;
}
.visitor-card {
  background: var(--cf-bg-card); border: 1px solid var(--cf-border-subtle);
  border-radius: 12px; padding: 16px; cursor: pointer;
  transition: border-color 0.15s, transform 0.1s;
}
.visitor-card:hover { border-color: rgba(99,102,241,0.5); transform: translateY(-1px); }

.visitor-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.visitor-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; color: #fff; flex-shrink: 0; font-size: 14px;
}
.visitor-avatar.large { width: 52px; height: 52px; font-size: 18px; }
.visitor-meta { flex: 1; min-width: 0; }
.visitor-name { font-weight: 600; color: var(--cf-text-primary); font-size: 14px; display: flex; align-items: center; gap: 6px; }
.visitor-sub { font-size: 12px; color: var(--cf-text-muted); margin-top: 2px; }
.flag { font-size: 14px; }
.heat-pill { padding: 3px 9px; border-radius: 9px; font-size: 11px; font-weight: 700; color: #fff; }

.visitor-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 10px 0; border-top: 1px solid var(--cf-border-subtle); }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-num { font-weight: 700; color: var(--cf-text-primary); font-size: 15px; }
.stat-num.large { font-size: 24px; }
.stat-lbl { font-size: 10px; color: var(--cf-text-muted); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.4px; }

.top-interest { font-size: 12px; color: var(--cf-text-secondary); padding: 8px 0; }
.visitor-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }
.visitor-tag { font-size: 10px; background: var(--cf-bg-input); border-radius: 5px; padding: 2px 7px; color: var(--cf-text-muted); }

/* Detail view */
.back-btn {
  background: none; border: none; color: var(--cf-text-secondary);
  font-size: 13px; cursor: pointer; margin-bottom: 16px; padding: 6px 0;
}
.back-btn:hover { color: var(--cf-text-primary); }
.detail-head { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.detail-name { font-size: 20px; font-weight: 700; color: var(--cf-text-primary); }
.detail-sub { font-size: 12px; color: var(--cf-text-muted); margin-top: 2px; }
.detail-stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.detail-stat-card { background: var(--cf-bg-card); border: 1px solid var(--cf-border-subtle); border-radius: 10px; padding: 14px; text-align: center; }
.detail-section { background: var(--cf-bg-card); border: 1px solid var(--cf-border-subtle); border-radius: 12px; padding: 16px; margin-bottom: 16px; }
.section-title { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); margin-bottom: 12px; }
.sessions-list { display: flex; flex-direction: column; gap: 6px; }
.session-row {
  display: grid; grid-template-columns: 100px 1fr auto 50px; gap: 10px; align-items: center;
  padding: 8px 10px; background: var(--cf-bg-input); border-radius: 7px; font-size: 12px;
}
.sess-id { font-family: monospace; color: var(--cf-text-muted); }
.sess-info { color: var(--cf-text-secondary); }
.sess-time { color: var(--cf-text-muted); font-size: 11px; }
.sess-heat { padding: 2px 7px; border-radius: 6px; color: #fff; font-weight: 700; font-size: 10px; text-align: center; }

.timeline-scroll { max-height: 500px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.timeline-event {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 7px 10px; background: var(--cf-bg-input); border-radius: 7px; font-size: 12px;
}
.ev-icon { font-size: 13px; flex-shrink: 0; width: 18px; text-align: center; }
.ev-body { flex: 1; min-width: 0; }
.ev-label { color: var(--cf-text-secondary); line-height: 1.4; }
.ev-meta { color: var(--cf-text-muted); font-size: 10px; margin-top: 2px; }

.loading-block, .empty-block {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 80px 20px; text-align: center;
  background: var(--cf-bg-card); border: 1px solid var(--cf-border-subtle); border-radius: 12px;
}
.empty-title { font-size: 14px; font-weight: 600; color: var(--cf-text-secondary); margin-top: 12px; }
.empty-sub { font-size: 12px; color: var(--cf-text-muted); margin-top: 4px; }

@media (max-width: 768px) {
  .visitors-page { padding: 20px 16px; }
  .page-header { flex-direction: column; gap: 12px; }
  .search-input { width: 100%; }
  .visitors-grid { grid-template-columns: 1fr; }
  .detail-stats-row { grid-template-columns: repeat(2, 1fr); }
  .session-row { grid-template-columns: 1fr 50px; }
  .sess-id, .sess-time { display: none; }
}
</style>
