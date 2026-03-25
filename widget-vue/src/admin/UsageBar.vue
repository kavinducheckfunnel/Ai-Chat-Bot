<template>
  <div v-if="quota" class="usage-bar">
    <p class="usage-title">{{ quota.plan_name || 'Free Plan' }}</p>

    <!-- Sessions -->
    <div class="usage-row">
      <div class="usage-labels">
        <span class="usage-label">Sessions</span>
        <span class="usage-count">{{ quota.sessions_this_month }}<template v-if="quota.max_sessions"> / {{ quota.max_sessions }}</template></span>
      </div>
      <div class="bar-track">
        <div
          class="bar-fill"
          :class="sessionColour"
          :style="{ width: sessionPct + '%' }"
        />
      </div>
    </div>

    <!-- Clients -->
    <div class="usage-row">
      <div class="usage-labels">
        <span class="usage-label">Chatbots</span>
        <span class="usage-count">{{ quota.client_count }}<template v-if="quota.max_clients"> / {{ quota.max_clients }}</template></span>
      </div>
      <div class="bar-track">
        <div
          class="bar-fill"
          :class="clientColour"
          :style="{ width: clientPct + '%' }"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const quota = ref(null)

onMounted(async () => {
  try {
    const me = await api.getMe()
    if (me?.quota) quota.value = me.quota
  } catch {}
})

function pct(used, max) {
  if (!max) return 0
  return Math.min(Math.round((used / max) * 100), 100)
}

function colour(p) {
  if (p >= 80) return 'red'
  if (p >= 60) return 'amber'
  return 'green'
}

const sessionPct = computed(() => pct(quota.value?.sessions_this_month, quota.value?.max_sessions))
const clientPct  = computed(() => pct(quota.value?.client_count, quota.value?.max_clients))
const sessionColour = computed(() => colour(sessionPct.value))
const clientColour  = computed(() => colour(clientPct.value))
</script>

<style scoped>
.usage-bar {
  margin: 0 0 12px 0;
  padding: 10px 12px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 9px;
}

.usage-title {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #475569;
  margin: 0 0 8px 0;
}

.usage-row {
  margin-bottom: 7px;
}
.usage-row:last-child { margin-bottom: 0; }

.usage-labels {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 3px;
}

.usage-label {
  font-size: 11px;
  color: #64748B;
}

.usage-count {
  font-size: 10px;
  color: #94A3B8;
  font-variant-numeric: tabular-nums;
}

.bar-track {
  height: 4px;
  background: rgba(255,255,255,0.08);
  border-radius: 99px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.4s ease;
}

.bar-fill.green { background: #22C55E; }
.bar-fill.amber { background: #F59E0B; }
.bar-fill.red   { background: #EF4444; }
</style>
