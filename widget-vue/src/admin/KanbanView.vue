<template>
  <div class="kanban-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Lead Kanban</h1>
        <p class="page-sub">Drag sessions to update their pipeline stage</p>
      </div>
      <button class="refresh-btn" @click="loadData" :disabled="loading">
        <svg width="15" height="15" fill="none" viewBox="0 0 24 24" :class="{ spin: loading }"><path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Refresh
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>Loading sessions...</p>
    </div>

    <div v-else class="kanban-board">
      <div
        v-for="col in columns"
        :key="col.key"
        class="kanban-col"
        @dragover.prevent
        @drop="onDrop($event, col.key)"
        :class="{ 'drag-over': dragOverCol === col.key }"
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
                {{ heatEmoji(session.heat_score) }} {{ session.heat_score }}%
              </span>
              <span v-if="session.takeover_active" class="takeover-pill">Live</span>
            </div>

            <div class="heat-bar-wrap">
              <div class="heat-bar" :style="{ width: session.heat_score + '%', background: heatColor(session.heat_score) }"></div>
            </div>

            <p class="card-client">{{ session.client_name }}</p>
            <p class="card-visitor">{{ session.visitor_id?.slice(0, 14) }}...</p>
            <p v-if="session.lead_email" class="card-email">{{ session.lead_email }}</p>

            <div class="card-footer">
              <span class="card-msgs">{{ session.message_count }} msgs</span>
              <span class="card-time">{{ timeAgo(session.updated_at) }}</span>
            </div>
          </div>

          <div v-if="!columnSessions(col.key).length" class="col-empty">
            Drop sessions here
          </div>
        </div>
      </div>
    </div>

    <!-- Session Detail Modal -->
    <div v-if="selectedSession" class="modal-overlay" @click.self="selectedSession = null">
      <div class="modal">
        <div class="modal-header">
          <div>
            <h3>{{ selectedSession.visitor_id?.slice(0, 20) }}...</h3>
            <p class="modal-sub">{{ selectedSession.client_name }}</p>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <button class="godview-btn" @click="goGodView(selectedSession)">
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>
              God View
            </button>
            <button class="modal-close" @click="selectedSession = null">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
        </div>
        <div class="modal-body">
          <div class="modal-meta-row">
            <div class="meta-chip"><span class="meta-k">Heat</span><span class="meta-v">{{ selectedSession.heat_score }}%</span></div>
            <div class="meta-chip"><span class="meta-k">State</span><span class="meta-v">{{ selectedSession.conversation_state }}</span></div>
            <div class="meta-chip"><span class="meta-k">Messages</span><span class="meta-v">{{ selectedSession.message_count }}</span></div>
          </div>
          <div class="move-section">
            <p class="move-label">Move to stage:</p>
            <div class="move-btns">
              <button v-for="col in columns" :key="col.key" class="move-btn" :class="{ active: selectedSession.kanban_state === col.key }" @click="moveSession(selectedSession, col.key)">
                {{ col.label }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const router = useRouter()
const sessions = ref([])
const loading = ref(false)
const dragSession = ref(null)
const dragOverCol = ref(null)
const selectedSession = ref(null)

const columns = [
  { key: 'NEW', label: 'New', headerClass: 'col-new' },
  { key: 'ENGAGED', label: 'Engaged', headerClass: 'col-engaged' },
  { key: 'HOT_LEAD', label: 'Hot Lead', headerClass: 'col-hot' },
  { key: 'CONVERTED', label: 'Converted', headerClass: 'col-converted' },
  { key: 'LOST', label: 'Lost', headerClass: 'col-lost' },
]

function columnSessions(key) {
  return sessions.value.filter(s => (s.kanban_state || 'NEW') === key)
}

async function loadData() {
  loading.value = true
  try {
    sessions.value = await api.getKanban() || []
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
  if (s.kanban_state === colKey) return
  // Optimistic update
  const idx = sessions.value.findIndex(x => x.session_id === s.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  try {
    await api.updateSession(s.session_id, { kanban_state: colKey })
  } catch {
    // Revert
    if (idx >= 0) sessions.value[idx].kanban_state = s.kanban_state
  }
}

async function moveSession(session, colKey) {
  if (session.kanban_state === colKey) return
  const idx = sessions.value.findIndex(x => x.session_id === session.session_id)
  if (idx >= 0) sessions.value[idx].kanban_state = colKey
  session.kanban_state = colKey
  try {
    await api.updateSession(session.session_id, { kanban_state: colKey })
  } catch {}
}

function openSession(s) {
  selectedSession.value = s
}

function goGodView(s) {
  router.push(`/admin/godview/${s.session_id}`)
}

function heatClass(score) {
  if (score >= 70) return 'hot'
  if (score >= 40) return 'warm'
  return 'cool'
}

function heatEmoji(score) {
  if (score >= 70) return '🔥'
  if (score >= 40) return '🟠'
  return '🔵'
}

function heatColor(score) {
  if (score >= 70) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if (score >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#3B82F6,#06B6D4)'
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
</script>

<style scoped>
.kanban-page { height: 100%; display: flex; flex-direction: column; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #0F172A; letter-spacing: -0.4px; }
.page-sub { font-size: 14px; color: #64748B; margin-top: 4px; }

.refresh-btn {
  display: flex; align-items: center; gap: 6px;
  background: white; border: 1px solid #E2E8F0; border-radius: 8px;
  padding: 8px 14px; font-size: 13px; font-weight: 500; color: #475569;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.refresh-btn:hover { background: #F8FAFC; }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.loading-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px; color: #94A3B8; }
.loader { width: 32px; height: 32px; border: 3px solid #E2E8F0; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.8s linear infinite; }

.kanban-board { display: flex; gap: 14px; flex: 1; overflow-x: auto; padding-bottom: 8px; }

.kanban-col {
  flex: 0 0 240px; background: #F8FAFC; border-radius: 14px;
  border: 2px solid transparent; transition: border-color 0.15s;
  display: flex; flex-direction: column; max-height: 100%;
}
.kanban-col.drag-over { border-color: #6366F1; background: rgba(99,102,241,0.03); }

.col-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 14px; border-radius: 12px 12px 0 0; flex-shrink: 0;
}
.col-new { background: #F1F5F9; }
.col-engaged { background: #EFF6FF; }
.col-hot { background: #FEF2F2; }
.col-converted { background: #F0FDF4; }
.col-lost { background: #F8FAFC; }

.col-title { font-size: 13px; font-weight: 700; color: #334155; }
.col-count { background: white; color: #64748B; font-size: 12px; font-weight: 700; padding: 2px 7px; border-radius: 10px; }

.col-cards { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px; }

.kanban-card {
  background: white; border-radius: 10px; padding: 12px;
  border: 1px solid #F1F5F9; cursor: grab; transition: all 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.kanban-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); transform: translateY(-1px); }
.kanban-card:active { cursor: grabbing; }

.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }

.heat-pill { font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 6px; }
.heat-pill.hot { background: rgba(239,68,68,0.1); color: #DC2626; }
.heat-pill.warm { background: rgba(249,115,22,0.1); color: #EA580C; }
.heat-pill.cool { background: rgba(59,130,246,0.1); color: #2563EB; }

.takeover-pill {
  font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;
  background: rgba(239,68,68,0.1); color: #DC2626;
  animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }

.heat-bar-wrap { background: #F1F5F9; border-radius: 3px; height: 4px; margin-bottom: 10px; overflow: hidden; }
.heat-bar { height: 100%; border-radius: 3px; transition: width 0.5s; }

.card-client { font-size: 12px; font-weight: 600; color: #1E293B; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-visitor { font-size: 11px; color: #94A3B8; font-family: monospace; margin-bottom: 4px; }
.card-email { font-size: 11px; color: #6366F1; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.card-footer { display: flex; justify-content: space-between; margin-top: 8px; padding-top: 8px; border-top: 1px solid #F8FAFC; }
.card-msgs, .card-time { font-size: 10px; color: #CBD5E1; }

.col-empty { color: #CBD5E1; font-size: 12px; text-align: center; padding: 20px 0; border: 2px dashed #E2E8F0; border-radius: 8px; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal { background: white; border-radius: 16px; width: 100%; max-width: 500px; box-shadow: 0 25px 50px rgba(0,0,0,0.15); }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 20px 20px 16px; border-bottom: 1px solid #F1F5F9; }
.modal-header h3 { font-size: 15px; font-weight: 600; color: #0F172A; }
.modal-sub { font-size: 12px; color: #94A3B8; }
.modal-body { padding: 20px; }

.modal-meta-row { display: flex; gap: 10px; margin-bottom: 20px; }
.meta-chip { background: #F8FAFC; border: 1px solid #F1F5F9; border-radius: 8px; padding: 8px 12px; text-align: center; }
.meta-k { display: block; font-size: 10px; color: #94A3B8; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
.meta-v { font-size: 14px; font-weight: 700; color: #0F172A; }

.move-label { font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 10px; }
.move-btns { display: flex; flex-wrap: wrap; gap: 6px; }
.move-btn { background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 7px; padding: 6px 12px; font-size: 12px; font-weight: 500; color: #475569; cursor: pointer; transition: all 0.15s; font-family: inherit; }
.move-btn:hover { background: #E2E8F0; }
.move-btn.active { background: #6366F1; color: white; border-color: #6366F1; }

.modal-close { background: none; border: none; cursor: pointer; padding: 4px; color: #94A3B8; border-radius: 6px; transition: all 0.15s; }
.modal-close:hover { background: #F1F5F9; color: #475569; }

.godview-btn { display: flex; align-items: center; gap: 5px; background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3); color: #6366F1; border-radius: 7px; padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; font-family: inherit; }
.godview-btn:hover { background: #6366F1; color: white; border-color: #6366F1; }
</style>
