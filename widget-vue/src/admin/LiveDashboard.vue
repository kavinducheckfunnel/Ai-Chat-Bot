<template>
  <AdminLayout>
    <div>
      <div class="page-header">
        <div>
          <h1>Live Sessions</h1>
          <p>Real-time visitor heat scores — sorted by intent</p>
        </div>
        <div class="ws-status" :class="wsConnected ? 'online' : 'offline'">
          {{ wsConnected ? 'Live' : 'Connecting...' }}
        </div>
      </div>

      <div class="sessions-grid">
        <div v-if="!sessions.length" class="empty-state">
          No active sessions in the last 30 minutes.
        </div>
        <div
          v-for="s in sessions"
          :key="s.session_id"
          class="session-card"
          :class="heatClass(s.heat_score)"
          @click="goToGodView(s.session_id)"
        >
          <div class="card-header">
            <div class="visitor-id">{{ s.visitor_id?.slice(0, 8) }}...</div>
            <div class="heat-badge" :class="heatClass(s.heat_score)">
              🔥 {{ s.heat_score }}
            </div>
          </div>
          <div class="heat-bar-wrap">
            <div class="heat-bar" :style="{ width: s.heat_score + '%' }" :class="heatClass(s.heat_score)"></div>
          </div>
          <div class="card-meta">
            <span class="state-badge">{{ s.conversation_state }}</span>
            <span class="msg-count">{{ s.message_count }} msgs</span>
          </div>
          <div class="ema-row">
            <div class="ema-item">
              <span>Intent</span>
              <div class="ema-bar"><div :style="{ width: (s.intent_ema * 100) + '%' }"></div></div>
            </div>
            <div class="ema-item">
              <span>Budget</span>
              <div class="ema-bar"><div :style="{ width: (s.budget_ema * 100) + '%' }"></div></div>
            </div>
            <div class="ema-item">
              <span>Urgency</span>
              <div class="ema-bar"><div :style="{ width: (s.urgency_ema * 100) + '%' }"></div></div>
            </div>
          </div>
          <div class="card-footer">
            <span v-if="s.takeover_active" class="takeover-badge">👤 Taken Over</span>
            <span class="client-name">{{ s.client_name || 'Unknown' }}</span>
          </div>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import AdminLayout from './AdminLayout.vue'
import { useAdminApi } from '../composables/useAdminApi.js'

const router = useRouter()
const { getToken, API_BASE } = useAdminApi()

const sessions = ref([])
const wsConnected = ref(false)
let socket = null

function heatClass(score) {
  if (score >= 70) return 'hot'
  if (score >= 40) return 'warm'
  return 'cool'
}

function goToGodView(sessionId) {
  router.push(`/admin/god-view/${sessionId}`)
}

function upsertSession(data) {
  const idx = sessions.value.findIndex(s => s.session_id === data.session_id)
  if (idx >= 0) {
    sessions.value[idx] = { ...sessions.value[idx], ...data }
  } else {
    sessions.value.push(data)
  }
  sessions.value.sort((a, b) => b.heat_score - a.heat_score)
}

function connectDashboard() {
  const wsBase = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://')
  const token = getToken()
  socket = new WebSocket(`${wsBase}/ws/admin/dashboard/?token=${token}`)

  socket.onopen = () => { wsConnected.value = true }
  socket.onclose = () => {
    wsConnected.value = false
    setTimeout(connectDashboard, 3000)
  }
  socket.onerror = () => { wsConnected.value = false }

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'snapshot') {
      sessions.value = data.sessions || []
      sessions.value.sort((a, b) => b.heat_score - a.heat_score)
    } else if (data.type === 'session_update') {
      upsertSession(data)
    }
  }
}

onMounted(connectDashboard)
onUnmounted(() => { socket?.close() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; }
.page-header h1 { font-size: 1.875rem; font-weight: 700; }
.page-header p { color: #64748b; margin-top: 4px; }
.ws-status { padding: 6px 16px; border-radius: 20px; font-size: 0.8125rem; font-weight: 600; }
.ws-status.online { background: #dcfce7; color: #166534; }
.ws-status.offline { background: #fee2e2; color: #991b1b; }

.sessions-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
.empty-state { grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 60px; }

.session-card {
  background: white; border-radius: 12px; padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  cursor: pointer; transition: all 0.2s;
  border-left: 4px solid #e2e8f0;
}
.session-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.session-card.hot { border-left-color: #ef4444; }
.session-card.warm { border-left-color: #f59e0b; }
.session-card.cool { border-left-color: #3b82f6; }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.visitor-id { font-family: monospace; font-size: 0.875rem; color: #64748b; }
.heat-badge { font-size: 0.875rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; }
.heat-badge.hot { background: #fee2e2; color: #991b1b; }
.heat-badge.warm { background: #fef3c7; color: #92400e; }
.heat-badge.cool { background: #dbeafe; color: #1e40af; }

.heat-bar-wrap { background: #f1f5f9; border-radius: 4px; height: 6px; margin-bottom: 12px; overflow: hidden; }
.heat-bar { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.heat-bar.hot { background: #ef4444; }
.heat-bar.warm { background: #f59e0b; }
.heat-bar.cool { background: #3b82f6; }

.card-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.state-badge { font-size: 0.75rem; font-weight: 600; padding: 2px 8px; background: #f1f5f9; border-radius: 4px; color: #475569; }
.msg-count { font-size: 0.75rem; color: #94a3b8; }

.ema-row { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.ema-item { display: flex; align-items: center; gap: 8px; }
.ema-item span { font-size: 0.6875rem; color: #94a3b8; width: 44px; flex-shrink: 0; }
.ema-bar { flex: 1; background: #f1f5f9; border-radius: 3px; height: 4px; overflow: hidden; }
.ema-bar div { height: 100%; background: #6366f1; border-radius: 3px; transition: width 0.5s; }

.card-footer { display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; }
.takeover-badge { background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.client-name { color: #94a3b8; }
</style>
