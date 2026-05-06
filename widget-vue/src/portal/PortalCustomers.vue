<template>
  <div class="flex flex-col gap-6 p-6 max-w-6xl">

    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Customers</h1>
        <p class="text-sm text-muted-foreground mt-1">Leads and contacts from your chatbot</p>
      </div>
      <Button variant="outline" @click="exportCSV" :disabled="exporting" class="gap-2">
        <Download class="h-4 w-4" />
        {{ exporting ? 'Exporting…' : 'Export CSV' }}
      </Button>
    </div>

    <!-- Tabs -->
    <div class="border-b border-border">
      <div class="flex gap-1">
        <button
          v-for="tab in tabs" :key="tab.value"
          class="flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
          :class="activeTab === tab.value
            ? 'border-primary text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
          <span
            v-if="tab.count !== undefined"
            class="inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold"
            :class="tab.value === 'hot' && tab.count > 0 ? 'bg-red-100 text-red-600' : 'bg-muted text-muted-foreground'"
          >
            {{ tab.count }}
          </span>
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 items-center">
      <div class="relative flex-1">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          v-model="search"
          type="text"
          placeholder="Search by email or state…"
          class="w-full rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
      <select
        v-model="sortBy"
        class="rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      >
        <option value="-heat_score">Hottest first</option>
        <option value="-created_at">Newest first</option>
        <option value="created_at">Oldest first</option>
      </select>
    </div>

    <!-- Table -->
    <Card>
      <CardContent class="p-0">
        <!-- Loading skeleton -->
        <div v-if="loading" class="space-y-0">
          <div v-for="n in 6" :key="n" class="flex items-center gap-4 px-5 py-3.5 border-b border-border last:border-0 animate-pulse">
            <div class="h-8 w-8 rounded-full bg-muted shrink-0"></div>
            <div class="flex-1 space-y-1.5">
              <div class="h-3.5 w-40 rounded bg-muted"></div>
              <div class="h-2.5 w-24 rounded bg-muted"></div>
            </div>
            <div class="h-5 w-16 rounded-full bg-muted"></div>
            <div class="h-3 w-24 rounded bg-muted"></div>
            <div class="h-3 w-8 rounded bg-muted"></div>
            <div class="h-3 w-20 rounded bg-muted"></div>
          </div>
        </div>

        <!-- Table -->
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-border">
              <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Visitor</th>
              <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">State</th>
              <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Heat</th>
              <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Messages</th>
              <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Seen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="filtered.length === 0">
              <td colspan="5" class="px-5 py-12 text-center text-sm text-muted-foreground">No leads match your filters</td>
            </tr>
            <tr
              v-for="lead in filtered"
              :key="lead.session_id"
              class="border-b border-border last:border-0 cursor-pointer hover:bg-muted/40 transition-colors"
              @click="openSession(lead)"
            >
              <!-- Visitor -->
              <td class="px-5 py-3.5">
                <div class="flex items-center gap-3">
                  <div
                    class="h-8 w-8 rounded-full shrink-0 flex items-center justify-center text-[11px] font-bold text-white"
                    :style="{ background: heatColor(lead.heat_score) }"
                  >
                    {{ lead.lead_email ? lead.lead_email[0].toUpperCase() : '#' }}
                  </div>
                  <div>
                    <p class="font-medium text-foreground text-sm">{{ lead.lead_email || 'Anonymous' }}</p>
                    <p v-if="lead.lead_phone" class="text-xs text-muted-foreground mt-0.5">{{ lead.lead_phone }}</p>
                  </div>
                </div>
              </td>
              <!-- State -->
              <td class="px-5 py-3.5">
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide" :class="kanbanBadgeClass(lead.kanban_state)">
                  {{ lead.kanban_state || 'NEW' }}
                </span>
              </td>
              <!-- Heat -->
              <td class="px-5 py-3.5">
                <div class="flex items-center gap-2">
                  <div class="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                    <div class="h-full rounded-full" :style="{ width: (lead.heat_score || 0) + '%', background: heatColor(lead.heat_score) }"></div>
                  </div>
                  <span class="text-xs text-muted-foreground font-mono w-8">{{ Math.round(lead.heat_score || 0) }}%</span>
                </div>
              </td>
              <!-- Messages -->
              <td class="px-5 py-3.5 font-mono text-muted-foreground text-sm">{{ lead.message_count || 0 }}</td>
              <!-- Seen -->
              <td class="px-5 py-3.5 text-xs text-muted-foreground">{{ formatDate(lead.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>

    <!-- Chat History Modal -->
    <div v-if="selectedSession" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" @click.self="selectedSession = null">
      <div class="bg-background border border-border rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-xl">
        <!-- Modal header -->
        <div class="flex items-start justify-between px-5 py-4 border-b border-border">
          <div>
            <h3 class="text-base font-semibold text-foreground">Chat History</h3>
            <p class="text-xs text-muted-foreground font-mono mt-0.5">
              {{ selectedSession.lead_email || selectedSession.visitor_id?.slice(0, 28) || 'Anonymous' }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <span
              class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold"
              :class="heatBadgeClass(selectedSession.heat_score)"
            >
              {{ Math.round(selectedSession.heat_score || 0) }}% heat
            </span>
            <button class="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors" @click="selectedSession = null">
              <X class="h-4 w-4" />
            </button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="loadingSession" class="flex justify-center items-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
        </div>

        <!-- Messages -->
        <div v-else class="flex flex-col gap-3 overflow-y-auto px-5 py-4">
          <div
            v-for="(msg, i) in sessionDetail?.chat_history || []"
            :key="i"
            class="flex flex-col max-w-[88%]"
            :class="msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'"
          >
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
              {{ msg.role === 'user' ? 'Visitor' : 'AI' }}
            </span>
            <p
              class="text-sm leading-relaxed px-3.5 py-2.5 rounded-xl m-0"
              :class="msg.role === 'user'
                ? 'bg-primary text-primary-foreground rounded-br-sm'
                : 'bg-muted text-foreground rounded-bl-sm'"
            >
              {{ msg.message || msg.content }}
            </p>
          </div>
          <p v-if="!sessionDetail?.chat_history?.length" class="text-sm text-muted-foreground text-center py-6">No messages yet.</p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Download, Search, X, Loader2 } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

const props = defineProps({ client: Object })
const api = useAdminApi()

const leads = ref([])
const loading = ref(true)
const activeTab = ref('all')
const search = ref('')
const sortBy = ref('-heat_score')
const exporting = ref(false)
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)

const hotLeads = computed(() => leads.value.filter(l => l.heat_score >= 75 || l.kanban_state === 'HOT_LEAD'))

const tabs = computed(() => [
  { value: 'all', label: 'All leads', count: leads.value.length },
  { value: 'hot', label: 'Hot leads', count: hotLeads.value.length },
  { value: 'converted', label: 'Converted' },
])

const filtered = computed(() => {
  let list = leads.value
  if (activeTab.value === 'hot') list = hotLeads.value
  if (activeTab.value === 'converted') list = list.filter(l => l.kanban_state === 'CONVERTED')
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(l => (l.lead_email || '').toLowerCase().includes(q) || (l.kanban_state || '').toLowerCase().includes(q))
  }
  if (sortBy.value === '-heat_score') list = [...list].sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0))
  if (sortBy.value === '-created_at') list = [...list].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  if (sortBy.value === 'created_at') list = [...list].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
  return list
})

async function loadLeads() {
  if (!props.client) return
  loading.value = true
  try {
    const data = await api.getPortalSessions(props.client.id, { limit: 200 })
    leads.value = Array.isArray(data) ? data : (data?.results || [])
  } catch {} finally {
    loading.value = false
  }
}

async function exportCSV() {
  if (!props.client) return
  exporting.value = true
  try {
    await api.exportLeadsCSV({ client_id: props.client.id })
  } catch {} finally {
    exporting.value = false
  }
}

async function openSession(lead) {
  selectedSession.value = lead
  sessionDetail.value = null
  loadingSession.value = true
  try {
    sessionDetail.value = await api.getSession(lead.session_id)
  } catch {}
  loadingSession.value = false
}

function heatColor(score) {
  if (!score) return 'hsl(var(--muted-foreground))'
  if (score >= 75) return '#ef4444'
  if (score >= 40) return '#f59e0b'
  return 'hsl(var(--primary))'
}

function heatBadgeClass(score) {
  if (score >= 75) return 'bg-red-100 text-red-600'
  if (score >= 40) return 'bg-amber-100 text-amber-600'
  return 'bg-primary/10 text-primary'
}

function kanbanBadgeClass(state) {
  if (state === 'HOT_LEAD') return 'bg-red-100 text-red-600'
  if (state === 'CONVERTED') return 'bg-emerald-100 text-emerald-600'
  if (state === 'ENGAGED') return 'bg-blue-100 text-blue-600'
  if (state === 'LOST') return 'bg-muted text-muted-foreground'
  return 'bg-slate-100 text-slate-500'
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString()
}

onMounted(loadLeads)
watch(() => props.client, loadLeads)
</script>
