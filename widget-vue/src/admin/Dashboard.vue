<template>
  <div class="admin-container">
    <Sidebar />
    <main class="admin-main">
      <header class="admin-header">
        <h1>Platform Overview</h1>
        <p>Live health of your AI Chatbot SaaS</p>
      </header>
      
      <div v-if="loading" class="loading">Loading stats...</div>
      
      <div v-else class="dashboard-content">
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Total Clients</h3>
            <div class="number">{{ stats.total_clients }}</div>
            <p>Across all platforms</p>
          </div>
          <div class="stat-card">
            <h3>Total Sessions</h3>
            <div class="number">{{ stats.total_sessions }}</div>
            <p>Customer interactions</p>
          </div>
          <div class="stat-card">
            <h3>Active Conversations</h3>
            <div class="number">{{ stats.active_sessions }}</div>
            <p>With 1+ messages</p>
          </div>
          <div class="stat-card highlight">
            <h3>Est. Revenue</h3>
            <div class="number">${{ stats.revenue_estimate }}</div>
            <p>Based on $49/mo/client</p>
          </div>
        </div>

        <div class="charts-grid">
          <div class="chart-card">
            <h3>Daily Session Trend</h3>
            <div class="bar-chart">
              <div v-for="(val, i) in stats.daily_trend" :key="i" class="bar-wrap">
                <div class="bar" :style="{ height: (val * 2) + 'px' }">
                  <span class="bar-val">{{ val }}</span>
                </div>
                <span class="bar-label">Day {{ i+1 }}</span>
              </div>
            </div>
          </div>

          <div class="chart-card">
            <h3>Conversion Funnel</h3>
            <div class="funnel-container">
              <div v-for="state in ['RESEARCH', 'EVALUATION', 'OBJECTION', 'READY_TO_BUY']" :key="state" class="funnel-step">
                <div class="step-label">{{ state }}</div>
                <div class="step-bar" :style="{ width: getFunnelWidth(state) }">
                   {{ stats.funnel[state] || 0 }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from './Sidebar.vue'

const stats = ref({
  total_clients: 0,
  total_sessions: 0,
  active_sessions: 0,
  revenue_estimate: 0,
  funnel: {},
  daily_trend: []
})
const loading = ref(true)

const getFunnelWidth = (state) => {
  const count = stats.value.funnel[state] || 0
  if (stats.value.total_sessions === 0) return '10%'
  return Math.max(10, (count / stats.value.total_sessions) * 100) + '%'
}

onMounted(async () => {
  try {
    const res = await fetch('http://localhost:8000/api/admin/stats/')
    stats.value = await res.json()
  } catch (e) {
    console.error("Failed to fetch stats", e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.admin-container {
  display: flex;
  min-height: 100vh;
  background: #f8fafc;
  color: #1e293b;
  font-family: 'Inter', sans-serif;
}
.admin-main {
  flex: 1;
  padding: 40px;
}
.admin-header {
  margin-bottom: 40px;
}
.admin-header h1 {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 8px;
}
.admin-header p {
  color: #64748b;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}
.stat-card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.stat-card h3 {
  font-size: 0.875rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}
.stat-card .number {
  font-size: 2.25rem;
  font-weight: 700;
  margin-bottom: 8px;
}
.stat-card p {
  font-size: 0.875rem;
  color: #94a3b8;
}
.stat-card.highlight {
  background: #2563eb;
  color: white;
}
.stat-card.highlight h3, .stat-card.highlight p {
  color: rgba(255,255,255,0.8);
}

/* Charts */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
.chart-card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.chart-card h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 24px;
  color: #0f172a;
}
.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  height: 120px;
  padding-bottom: 24px;
}
.bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.bar {
  width: 100%;
  background: #bfdbfe;
  border-radius: 4px 4px 0 0;
  position: relative;
  transition: all 0.3s;
  min-height: 4px;
}
.bar:hover { background: #3b82f6; }
.bar-val {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.65rem;
  font-weight: 700;
  color: #64748b;
}
.bar-label {
  font-size: 0.65rem;
  color: #94a3b8;
  white-space: nowrap;
}

.funnel-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.funnel-step {
  display: flex;
  align-items: center;
  gap: 16px;
}
.step-label {
  width: 100px;
  font-size: 0.65rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
}
.step-bar {
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  padding: 8px 12px;
  font-size: 0.875rem;
  font-weight: 700;
  color: #1e3a8a;
  border-radius: 0 4px 4px 0;
}
</style>

