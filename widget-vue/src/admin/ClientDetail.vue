<template>
  <div class="admin-container">
    <Sidebar />
    <main class="admin-main">
      <header class="admin-header">
        <div class="header-with-action">
          <h1>{{ client.name }}</h1>
          <div class="header-badges">
            <span class="badge">{{ client.platform }}</span>
            <span :class="['status-dot', client.is_active ? 'active' : 'inactive']"></span>
          </div>
        </div>
        <p>Analytics and configuration for <code>{{ client.domain_url }}</code></p>
      </header>

      <div class="detail-tabs">
        <button v-for="tab in tabs" :key="tab" @click="activeTab = tab" :class="{ active: activeTab === tab }">
          {{ tab }}
        </button>
      </div>

      <section v-if="activeTab === 'Overview'" class="tab-content">
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Pages Ingested</h3>
            <div class="number">{{ client.total_pages_ingested }}</div>
            <p>Vector database chunks</p>
          </div>
          <div class="stat-card">
            <h3>Avg. Intent Score</h3>
            <div class="number">{{ (analytics.avg_intent * 100).toFixed(0) }}%</div>
            <p>Customer buying signal</p>
          </div>
        </div>

        <div class="charts-grid secondary">
          <div class="chart-card">
            <h3>Individual Funnel</h3>
            <div class="funnel-container">
              <div v-for="state in ['RESEARCH', 'EVALUATION', 'OBJECTION', 'READY_TO_BUY']" :key="state" class="funnel-step">
                <div class="step-label">{{ state }}</div>
                <div class="step-bar" :style="{ width: getFunnelWidth(state), background: client.chatbot_color }">
                   {{ analytics.funnel[state] || 0 }}
                </div>
              </div>
            </div>
          </div>
          <div class="chart-card">
            <h3>Recent Activity</h3>
            <div class="bar-chart mini">
              <div v-for="(val, i) in analytics.sessions_trend" :key="i" class="bar-wrap">
                <div class="bar" :style="{ height: (val * 5) + 'px', background: client.chatbot_color }"></div>
              </div>
            </div>
            <p class="chart-footer">Sessions per day (last 7 days)</p>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'Settings'" class="tab-content">
        <div class="card settings-card">
          <h3>Chatbot Branding</h3>
          <form @submit.prevent="updateBranding">
            <div class="form-grid">
              <div class="form-group">
                <label>Chatbot Display Name</label>
                <input v-model="client.chatbot_name" placeholder="e.g. Sales Assistant" />
              </div>
              <div class="form-group">
                <label>Theme Color (Hex)</label>
                <div class="color-picker-wrap">
                  <input type="color" v-model="client.chatbot_color" class="color-preview" />
                  <input v-model="client.chatbot_color" placeholder="#3B82F6" />
                </div>
              </div>
              <div class="form-group full-width">
                <label>Logo URL (Appears in header)</label>
                <input v-model="client.chatbot_logo_url" placeholder="https://..." />
              </div>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </form>
        </div>
      </section>

      <section v-if="activeTab === 'Shortcode'" class="tab-content">
        <div class="card shortcode-card">
          <h3>Embed Shortcode</h3>
          <p>Paste this inside your website's <code>&lt;body&gt;</code> or <code>&lt;head&gt;</code> tag:</p>
          <pre><code>{{ generateShortcode() }}</code></pre>
          <button class="btn-secondary" @click="copyShortcode">Copy to Clipboard</button>
        </div>
      </section>

      <section v-if="activeTab === 'Chat History'" class="tab-content">
        <div class="session-list">
          <div v-if="sessions.length === 0" class="empty-state">No chat sessions found for this client.</div>
          <div v-for="session in sessions" :key="session.session_id" class="session-item" @click="openSession(session.session_id)">
            <div class="session-info">
              <strong>Visitor {{ session.visitor_id.slice(0,8) }}</strong>
              <span>{{ session.message_count }} messages | {{ session.state }}</span>
            </div>
            <div class="session-meta">
              <span class="intent-label" :style="{ background: getIntentColor(session.intent_score) }">
                Intent: {{ (session.intent_score * 100).toFixed(0) }}%
              </span>
              <span class="time">{{ formatDate(session.updated_at) }}</span>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Chat History Modal -->
    <div v-if="selectedSession" class="modal-overlay" @click.self="selectedSession = null">
      <div class="modal chat-modal">
        <div class="modal-header">
           <h2>Conversation History</h2>
           <button @click="selectedSession = null" class="close-btn">&times;</button>
        </div>
        <div class="chat-history-view" :style="{ '--primary': client.chatbot_color || '#3B82F6' }">
          <div v-for="(msg, i) in conversation" :key="i" :class="['chat-bubble-wrap', msg.role]">
             <div class="bubble">
                <p>{{ msg.message }}</p>
                <span class="bubble-time">{{ formatTime(msg.timestamp) }}</span>
             </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './Sidebar.vue'

const route = useRoute()
const client = ref({})
const sessions = ref([])
const analytics = ref({ funnel: {}, sessions_trend: [], avg_intent: 0 })
const activeTab = ref('Overview')
const tabs = ['Overview', 'Chat History', 'Settings', 'Shortcode']
const selectedSession = ref(null)
const conversation = ref([])
const saving = ref(false)

const fetchClient = async () => {
    const res = await fetch(`http://localhost:8000/api/admin/clients/${route.params.id}/`)
    client.value = await res.json()
}

const fetchSessions = async () => {
    const res = await fetch(`http://localhost:8000/api/admin/clients/${route.params.id}/sessions/`)
    sessions.value = await res.json()
}

const fetchAnalytics = async () => {
    const res = await fetch(`http://localhost:8000/api/admin/clients/${route.params.id}/analytics/`)
    analytics.value = await res.json()
}

const getFunnelWidth = (state) => {
  const count = analytics.value.funnel[state] || 0
  const total = sessions.value.length || 1
  return Math.max(10, (count / total) * 100) + '%'
}

const updateBranding = async () => {
    saving.value = true
    try {
        const res = await fetch(`http://localhost:8000/api/admin/clients/${route.params.id}/`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chatbot_name: client.value.chatbot_name,
                chatbot_color: client.value.chatbot_color,
                chatbot_logo_url: client.value.chatbot_logo_url
            })
        })
        if (res.ok) {
            alert("Settings saved successfully!")
        }
    } catch (e) {
        console.error("Save failed", e)
    } finally {
        saving.value = false
    }
}

const openSession = async (sid) => {
    const res = await fetch(`http://localhost:8000/api/admin/sessions/${sid}/`)
    const data = await res.json()
    conversation.value = data.chat_history
    selectedSession.value = sid
}

const generateShortcode = () => {
  return `<!-- Checkfunnel AI Chatbot Widget -->
<div id="cf-app-root"></div>
<script 
  src="http://localhost:5174/assets/index.js" 
  data-client-id="${client.value.id}" 
  async>
<\/script>`
}

const copyShortcode = () => {
  navigator.clipboard.writeText(generateShortcode())
  alert("Shortcode copied!")
}

const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleDateString() + ' ' + new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const formatTime = (ts) => {
    if (!ts) return ''
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const getIntentColor = (score) => {
    if (score > 0.7) return '#dcfce7' // Green
    if (score > 0.4) return '#fef9c3' // Yellow
    return '#f1f5f9' // Grey
}

onMounted(() => {
    fetchClient()
    fetchSessions()
    fetchAnalytics()
})
</script>

<style scoped>
.admin-container { display: flex; min-height: 100vh; background: #f8fafc; font-family: 'Inter', sans-serif; }
.admin-main { flex: 1; padding: 40px; }
.header-with-action { display: flex; align-items: center; gap: 20px; }
.header-badges { display: flex; align-items: center; gap: 10px; }
.detail-tabs { display: flex; gap: 24px; margin: 32px 0; border-bottom: 2px solid #e2e8f0; }
.detail-tabs button { background: none; border: none; padding: 12px 4px; font-weight: 600; color: #64748b; cursor: pointer; position: relative; }
.detail-tabs button.active { color: #2563eb; }
.detail-tabs button.active::after { content: ''; position: absolute; bottom: -2px; left: 0; right: 0; height: 2px; background: #2563eb; }
.status-text.DONE { color: #10b981; }
.status-text.RUNNING { color: #3b82f6; }
.status-text.FAILED { color: #ef4444; }
.card { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
pre { background: #1e293b; color: #f8fafc; padding: 20px; border-radius: 8px; font-size: 0.875rem; overflow-x: auto; margin: 16px 0; }
.session-list { display: grid; gap: 12px; }
.session-item { background: white; padding: 16px 24px; border-radius: 12px; border: 1px solid #e2e8f0; cursor: pointer; display: flex; justify-content: space-between; transition: 0.2s; align-items: center; }
.session-item:hover { border-color: #2563eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
.session-info { display: flex; flex-direction: column; gap: 4px; }
.session-meta { text-align: right; display: flex; flex-direction: column; gap: 4px; }
.intent-label { padding: 4px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; color: #1e293b; }

/* Settings Form */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.full-width { grid-column: span 2; }
.form-group label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 0.875rem; color: #475569; }
.form-group input { width: 100%; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; }
.color-picker-wrap { display: flex; gap: 8px; align-items: center; }
.color-preview { width: 44px; height: 44px; padding: 0; border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer; }
.form-actions { display: flex; justify-content: flex-end; }

/* Chat Modal Enhancement */
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.close-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #64748b; }
.chat-history-view { max-height: 500px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; padding: 20px 0; background: #fdfdfd; }
.chat-bubble-wrap { display: flex; flex-direction: column; max-width: 85%; }
.chat-bubble-wrap.user { align-self: flex-end; }
.chat-bubble-wrap.ai { align-self: flex-start; }
.bubble { padding: 12px 16px; border-radius: 16px; position: relative; font-size: 0.95rem; line-height: 1.5; }
.user .bubble { background: var(--primary); color: white; border-bottom-right-radius: 4px; }
.ai .bubble { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 4px; }
.bubble-time { font-size: 0.65rem; opacity: 0.6; margin-top: 4px; display: block; text-align: right; }
.ai .bubble-time { text-align: left; }
</style>

