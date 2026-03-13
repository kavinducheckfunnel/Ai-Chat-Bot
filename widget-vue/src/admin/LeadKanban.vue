<template>
  <AdminLayout>
    <div>
      <div class="page-header">
        <div>
          <h1>Lead Kanban</h1>
          <p>Drag sessions between stages or click to open God View</p>
        </div>
        <button @click="loadKanban" class="refresh-btn">↻ Refresh</button>
      </div>

      <div class="kanban-board">
        <div
          v-for="state in STATES"
          :key="state.key"
          class="kanban-col"
          @dragover.prevent
          @drop="onDrop($event, state.key)"
        >
          <div class="col-header">
            <span class="col-icon">{{ state.icon }}</span>
            <span>{{ state.label }}</span>
            <span class="col-count">{{ (board[state.key] || []).length }}</span>
          </div>
          <div class="col-cards">
            <div
              v-for="s in board[state.key]"
              :key="s.session_id"
              class="kanban-card"
              draggable="true"
              @dragstart="onDragStart($event, s)"
              @click="goToGodView(s.session_id)"
            >
              <div class="kc-header">
                <span class="kc-visitor">{{ s.visitor_id?.slice(0, 8) }}...</span>
                <span class="kc-heat" :class="heatClass(s.heat_score)">🔥 {{ s.heat_score }}</span>
              </div>
              <div class="kc-heat-bar">
                <div :style="{ width: s.heat_score + '%' }" :class="heatClass(s.heat_score)"></div>
              </div>
              <p class="kc-last-msg">{{ s.last_message }}</p>
              <div class="kc-footer">
                <span>{{ s.message_count }} msgs</span>
                <span v-if="s.takeover_active" class="takeover-dot">👤</span>
                <span class="kc-client">{{ s.client_name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AdminLayout from './AdminLayout.vue'
import { useAdminApi } from '../composables/useAdminApi.js'

const router = useRouter()
const { getKanban, patchSession } = useAdminApi()

const STATES = [
  { key: 'RESEARCH', label: 'Research', icon: '🔍' },
  { key: 'EVALUATION', label: 'Evaluating', icon: '⚖️' },
  { key: 'OBJECTION', label: 'Objection', icon: '🤔' },
  { key: 'RECOVERY', label: 'Recovery', icon: '🔄' },
  { key: 'READY_TO_BUY', label: 'Ready to Buy', icon: '🛒' },
]

const board = ref({})
let draggedSession = null

function heatClass(score) {
  if (score >= 70) return 'hot'
  if (score >= 40) return 'warm'
  return 'cool'
}

function goToGodView(sessionId) {
  router.push(`/admin/god-view/${sessionId}`)
}

function onDragStart(event, session) {
  draggedSession = session
  event.dataTransfer.effectAllowed = 'move'
}

async function onDrop(event, targetState) {
  if (!draggedSession) return
  const fromState = draggedSession.conversation_state
  if (fromState === targetState) return

  // Optimistically move card
  board.value[fromState] = board.value[fromState].filter(s => s.session_id !== draggedSession.session_id)
  draggedSession.conversation_state = targetState
  board.value[targetState] = [draggedSession, ...(board.value[targetState] || [])]

  // Persist to API
  await patchSession(draggedSession.session_id, { conversation_state: targetState })
  draggedSession = null
}

async function loadKanban() {
  try {
    board.value = await getKanban()
  } catch (e) {
    console.error('Failed to load kanban', e)
  }
}

onMounted(loadKanban)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; }
.page-header h1 { font-size: 1.875rem; font-weight: 700; }
.page-header p { color: #64748b; margin-top: 4px; }
.refresh-btn { background: #f1f5f9; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: 500; transition: background 0.2s; }
.refresh-btn:hover { background: #e2e8f0; }

.kanban-board { display: flex; gap: 16px; overflow-x: auto; padding-bottom: 16px; align-items: flex-start; }
.kanban-col { flex: 0 0 240px; background: #f8fafc; border-radius: 12px; overflow: hidden; }
.col-header {
  display: flex; align-items: center; gap: 8px; padding: 14px 16px;
  background: white; border-bottom: 2px solid #f1f5f9; font-weight: 600; font-size: 0.9375rem;
}
.col-icon { font-size: 1.1rem; }
.col-count { margin-left: auto; background: #f1f5f9; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 700; color: #64748b; }
.col-cards { padding: 12px; display: flex; flex-direction: column; gap: 10px; min-height: 120px; }

.kanban-card {
  background: white; border-radius: 10px; padding: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.07); cursor: grab; transition: all 0.15s;
  border-left: 3px solid #e2e8f0;
}
.kanban-card:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.kanban-card:active { cursor: grabbing; }

.kc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.kc-visitor { font-family: monospace; font-size: 0.8125rem; color: #64748b; }
.kc-heat { font-size: 0.8125rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
.kc-heat.hot { background: #fee2e2; color: #991b1b; }
.kc-heat.warm { background: #fef3c7; color: #92400e; }
.kc-heat.cool { background: #dbeafe; color: #1e40af; }

.kc-heat-bar { background: #f1f5f9; border-radius: 3px; height: 4px; margin-bottom: 8px; overflow: hidden; }
.kc-heat-bar div { height: 100%; border-radius: 3px; }
.kc-heat-bar div.hot { background: #ef4444; }
.kc-heat-bar div.warm { background: #f59e0b; }
.kc-heat-bar div.cool { background: #3b82f6; }

.kc-last-msg { font-size: 0.8125rem; color: #64748b; line-height: 1.4; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kc-footer { display: flex; align-items: center; gap: 6px; font-size: 0.75rem; color: #94a3b8; }
.takeover-dot { font-size: 0.875rem; }
.kc-client { margin-left: auto; }
</style>
