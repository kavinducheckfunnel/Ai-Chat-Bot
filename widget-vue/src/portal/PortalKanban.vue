<template>
  <div class="kanban-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Pipeline</h1>
        <p class="page-sub">Drag sessions to update their stage</p>
      </div>
      <button class="refresh-btn" @click="loadData" :disabled="loading">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" :class="{ spin: loading }">
          <path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Refresh
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>Loading pipeline...</p>
    </div>

    <div v-else class="kanban-board">
      <div
        v-for="col in columns"
        :key="col.key"
        class="kanban-col"
        :class="{ 'drag-over': dragOverCol === col.key }"
        @dragover.prevent
        @drop="onDrop($event, col.key)"
        @dragenter="dragOverCol = col.key"
        @dragleave="dragOverCol = null"
      >
        <div class="col-header" :class="col.headerClass">
          <span class="col-title">{{ col.label }}</span>
          <span class="col-count">{{ columnSessions(col.key).length }}</span>
        </div>

        <div class="col-cards">
          <div
            v-for="session in columnSessions(col.key)"
            :key="session.session_id"
            class="kanban-card"
            draggable="true"
            @dragstart="onDragStart($event, session)"
            @dragend="dragOverCol = null"
            @click="openSession(session)"
          >
            <div class="card-top">
              <span class="heat-pill" :class="heatClass(session.heat_score)">
                {{ heatEmoji(session.heat_score) }} {{ Math.round(session.heat_score || 0) }}%
              </span>
            </div>

            <div class="heat-bar-wrap">
              <div class="heat-bar" :style="{ width: (session.heat_score || 0) + '%', background: heatGradient(session.heat_score) }"></div>
            </div>

            <p class="card-visitor">{{ session.lead_email || (session.visitor_id || 'Anonymous').slice(0, 16) + '...' }}</p>
            <p v-if="session.lead_phone" class="card-phone">{{ session.lead_phone }}</p>

            <div class="card-footer">
              <span class="card-msgs">{{ session.message_count || 0 }} msgs</span>
              <span class="card-time">{{ timeAgo(session.updated_at || session.created_at) }}</span>
            </div>
          </div>

          <div v-if="!columnSessions(col.key).length" class="col-empty">
            Drop sessions here
          </div>
        </div>
      </div>
    </div>

    <!-- Session detail modal -->
    <div v-if="selectedSession" class="modal-overlay" @click.self="selectedSession = null">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">{{ selectedSession.lead_email || (selectedSession.visitor_id || '').slice(0, 22) + '...' }}</h3>
            <p class="modal-sub">{{ selectedSession.conversation_state }}</p>
          </div>
          <button class="modal-close" @click="selectedSession = null">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="modal-meta-row">
            <div class="meta-chip">
              <span class="meta-k">Heat</span>
              <span class="meta-v" :class="heatClass(selectedSession.heat_score)">{{ Math.round(selectedSession.heat_score || 0) }}%</span>
            </div>
            <div class="meta-chip">
              <span class="meta-k">Stage</span>
              <span class="meta-v">{{ selectedSession.kanban_state || 'NEW' }}</span>
            </div>
            <div class="meta-chip">
              <span class="meta-k">Messages</span>
              <span class="meta-v">{{ selectedSession.message_count || 0 }}</span>
            </div>
          </div>
          <div class="move-section">
            <p class="move-label">Move to stage:</p>
            <div class="move-btns">
              <button
                v-for="col in columns"
                :key="col.key"
                class="move-btn"
                :class="{ active: (selectedSession.kanban_state || 'NEW') === col.key }"
                @click="moveSession(selectedSession, col.key)"
              >
                {{ col.label }}
              </button>
            </div>
          </div>

          <div v-if="loadingSession" class="chat-loading">
            <div class="loader"></div>
          </div>
          <div v-else-if="sessionDetail?.chat_history?.length" class="chat-preview">
            <p class="chat-preview-title">Recent Messages</p>
            <div class="chat-history">
              <div
                v-for="(msg, i) in sessionDetail.chat_history.slice(-6)"
                :key="i"
                class="chat-msg"
                :class="msg.role === 'user' ? 'user-msg' : 'ai-msg'"
              >
                <span class="msg-role">{{ msg.role === 'user' ? 'Visitor' : 'AI' }}</span>
                <p class="msg-text">{{ msg.message || msg.content }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()
const sessions = ref([])
const loading = ref(false)
const dragSession = ref(null)
const dragOverCol = ref(null)
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)

const columns = [
  { key: 'NEW',       label: 'New',       headerClass: 'col-new' },
  { key: 'ENGAGED',   label: 'Engaged',   headerClass: 'col-engaged' },
  { key: 'HOT_LEAD',  label: 'Hot Lead',  headerClass: 'col-hot' },
  { key: 'CONVERTED', label: 'Converted', headerClass: 'col-converted' },
  { key: 'LOST',      label: 'Lost',      headerClass: 'col-lost' },
]

function columnSessions(key) {
  return sessions.value.filter(s => (s.kanban_state || 'NEW') === key)
}

async function loadData() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { limit: 200 })
    sessions.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function onDragStart(e, session) {
  dragSession.value = session
  e.dataTransfer.effectAllowed = 'move'
}

async function onDrop(e, colKey) {
  dragOverCol.value = null
  if (!dragSession.value) return
  const s = dragSession.value
  dragSession.value = null
  if ((s.kanban_state || 'NEW') === colKey) return
  const idx = sessions.value.findIndex(x => x.session_id === s.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  try {
    await api.updateSession(s.session_id, { kanban_state: colKey })
  } catch {
    if (idx >= 0) sessions.value[idx].kanban_state = s.kanban_state
  }
}

async function moveSession(session, colKey) {
  if ((session.kanban_state || 'NEW') === colKey) return
  const idx = sessions.value.findIndex(x => x.session_id === session.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  session.kanban_state = colKey
  try {
    await api.updateSession(session.session_id, { kanban_state: colKey })
  } catch {}
}

async function openSession(session) {
  selectedSession.value = session
  sessionDetail.value = null
  loadingSession.value = true
  try {
    sessionDetail.value = await api.getSession(session.session_id)
  } catch {}
  loadingSession.value = false
}

function heatClass(score) {
  if ((score || 0) >= 75) return 'hot'
  if ((score || 0) >= 40) return 'warm'
  return 'cool'
}

function heatEmoji(score) {
  if ((score || 0) >= 75) return '🔥'
  if ((score || 0) >= 40) return '🟠'
  return '🔵'
}

function heatGradient(score) {
  if ((score || 0) >= 75) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if ((score || 0) >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#6366F1,#8B5CF6)'
}

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

onMounted(loadData)
watch(() => props.client, loadData)
</script>

<style scoped>
* { box-sizing: border-box; }

.kanban-page {
  padding: 28px 32px;
  font-family: 'Inter', -apple-system, sans-serif;
  height: 100%; display: flex; flex-direction: column;
}

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.4px; }
.page-sub { font-size: 13px; color: #475569; margin-top: 3px; }

.refresh-btn {
  display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
  border-radius: 8px; padding: 7px 13px;
  font-size: 13px; font-weight: 500; color: #94a3b8;
  cursor: pointer; transition: all 0.12s; font-family: inherit;
}
.refresh-btn:hover { background: rgba(255,255,255,0.09); color: #f1f5f9; }
.refresh-btn:disabled { opacity: 0.5; }
.spin { animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.loading-state { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 60px; color: #334155; }
.loader { width: 28px; height: 28px; border: 2px solid rgba(255,255,255,0.08); border-top-color: #6366f1; border-radius: 50%; animation: spin 0.7s linear infinite; }

.kanban-board { display: flex; gap: 12px; flex: 1; overflow-x: auto; padding-bottom: 8px; }

.kanban-col {
  flex: 0 0 220px; background: #111111; border-radius: 12px;
  border: 2px solid transparent; transition: border-color 0.15s;
  display: flex; flex-direction: column; max-height: calc(100vh - 180px);
}
.kanban-col.drag-over { border-color: #6366f1; background: rgba(99,102,241,0.04); }

.col-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 13px; border-radius: 10px 10px 0 0; flex-shrink: 0;
}
.col-new       { background: rgba(100,116,139,0.12); }
.col-engaged   { background: rgba(59,130,246,0.12); }
.col-hot       { background: rgba(239,68,68,0.12); }
.col-converted { background: rgba(34,197,94,0.12); }
.col-lost      { background: rgba(100,116,139,0.08); }

.col-title { font-size: 12px; font-weight: 700; color: #94a3b8; }
.col-count {
  background: rgba(255,255,255,0.06); color: #64748b;
  font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 8px;
}

.col-cards { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 7px; }

.kanban-card {
  background: #161616; border-radius: 10px; padding: 11px;
  border: 1px solid rgba(255,255,255,0.06); cursor: grab; transition: all 0.12s;
}
.kanban-card:hover { border-color: rgba(255,255,255,0.12); transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
.kanban-card:active { cursor: grabbing; }

.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; }

.heat-pill { font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 5px; }
.heat-pill.hot  { background: rgba(239,68,68,0.12); color: #f87171; }
.heat-pill.warm { background: rgba(249,115,22,0.12); color: #fb923c; }
.heat-pill.cool { background: rgba(99,102,241,0.12); color: #a5b4fc; }

.heat-bar-wrap { background: rgba(255,255,255,0.05); border-radius: 2px; height: 4px; margin-bottom: 9px; overflow: hidden; }
.heat-bar { height: 100%; border-radius: 2px; transition: width 0.5s; }

.card-visitor { font-size: 12px; font-weight: 500; color: #94a3b8; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-phone   { font-size: 11px; color: #475569; margin-bottom: 4px; }

.card-footer { display: flex; justify-content: space-between; margin-top: 8px; padding-top: 7px; border-top: 1px solid rgba(255,255,255,0.04); }
.card-msgs, .card-time { font-size: 10px; color: #334155; }

.col-empty { color: #334155; font-size: 11px; text-align: center; padding: 18px 0; border: 2px dashed rgba(255,255,255,0.06); border-radius: 7px; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(6px); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal { background: #161616; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; width: 100%; max-width: 520px; max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 25px 60px rgba(0,0,0,0.6); }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 18px 20px 14px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.modal-title { font-size: 15px; font-weight: 600; color: #f1f5f9; }
.modal-sub { font-size: 11px; color: #475569; margin-top: 3px; }
.modal-close { background: none; border: none; cursor: pointer; padding: 4px; color: #475569; border-radius: 6px; transition: all 0.12s; }
.modal-close:hover { background: rgba(255,255,255,0.06); color: #94a3b8; }

.modal-body { padding: 18px 20px; overflow-y: auto; }

.modal-meta-row { display: flex; gap: 8px; margin-bottom: 18px; }
.meta-chip { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 8px 12px; text-align: center; flex: 1; }
.meta-k { display: block; font-size: 9px; color: #334155; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 3px; }
.meta-v { font-size: 14px; font-weight: 700; color: #f1f5f9; }
.meta-v.hot  { color: #f87171; }
.meta-v.warm { color: #fb923c; }
.meta-v.cool { color: #a5b4fc; }

.move-label { font-size: 11px; font-weight: 600; color: #475569; margin-bottom: 8px; }
.move-btns { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 18px; }
.move-btn {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 7px; padding: 5px 11px; font-size: 12px; font-weight: 500;
  color: #64748b; cursor: pointer; transition: all 0.12s; font-family: inherit;
}
.move-btn:hover { background: rgba(255,255,255,0.08); color: #94a3b8; }
.move-btn.active { background: rgba(99,102,241,0.2); color: #a5b4fc; border-color: rgba(99,102,241,0.4); }

.chat-loading { display: flex; justify-content: center; padding: 24px; }

.chat-preview-title { font-size: 11px; font-weight: 600; color: #334155; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px; }
.chat-history { display: flex; flex-direction: column; gap: 8px; }
.chat-msg { max-width: 88%; }
.user-msg { align-self: flex-end; }
.ai-msg  { align-self: flex-start; }
.msg-role { font-size: 9px; font-weight: 600; color: #334155; margin-bottom: 3px; display: block; text-transform: uppercase; letter-spacing: 0.05em; }
.user-msg .msg-role { text-align: right; }
.msg-text { font-size: 12px; line-height: 1.5; padding: 8px 12px; border-radius: 10px; margin: 0; }
.user-msg .msg-text { background: rgba(99,102,241,0.15); color: #c7d2fe; border-bottom-right-radius: 3px; }
.ai-msg  .msg-text { background: #1e293b; color: #94a3b8; border: 1px solid rgba(255,255,255,0.05); border-bottom-left-radius: 3px; }
</style>
