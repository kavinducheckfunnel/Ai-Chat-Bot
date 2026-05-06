<template>
  <div class="flex flex-col gap-6 p-6 h-full">

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Lead Management</h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ loading ? 'Loading…' : `${totalCount} captured lead${totalCount !== 1 ? 's' : ''}` }}
          <span v-if="hasFilters" class="ml-2 inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">filtered</span>
        </p>
      </div>
      <Button @click="doExport" :disabled="exporting || !leads.length" size="sm">
        <Download class="h-4 w-4" />
        {{ exporting ? 'Exporting…' : 'Export CSV' }}
      </Button>
    </div>

    <!-- Filter bar -->
    <Card>
      <CardContent class="pt-4 pb-4">
        <div class="flex flex-wrap items-end gap-4">
          <div class="flex flex-col gap-1.5">
            <Label class="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Client</Label>
            <select
              v-model="filters.client_id"
              @change="loadLeads"
              class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring min-w-[140px]"
            >
              <option value="">All Clients</option>
              <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="flex flex-col gap-1.5">
            <Label class="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">From</Label>
            <input
              type="date"
              v-model="filters.date_from"
              @change="loadLeads"
              class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label class="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">To</Label>
            <input
              type="date"
              v-model="filters.date_to"
              @change="loadLeads"
              class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label class="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Min Heat</Label>
            <div class="relative">
              <input
                type="number"
                min="0"
                max="100"
                placeholder="0"
                v-model.number="filters.min_heat"
                @change="loadLeads"
                class="h-9 w-20 rounded-md border border-input bg-background pl-3 pr-7 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <span class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground pointer-events-none">%</span>
            </div>
          </div>
          <Button v-if="hasFilters" variant="outline" size="sm" @click="clearFilters" class="text-destructive border-destructive/30 hover:bg-destructive/10">
            <X class="h-3.5 w-3.5" />
            Clear
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Stats strip -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Card>
        <CardContent class="pt-5 pb-5 flex flex-col items-center gap-1">
          <span class="text-2xl font-bold tracking-tight">{{ totalCount }}</span>
          <span class="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Total Leads</span>
        </CardContent>
      </Card>
      <Card class="border-red-200 bg-red-50/50 dark:bg-red-950/20">
        <CardContent class="pt-5 pb-5 flex flex-col items-center gap-1">
          <span class="text-2xl font-bold tracking-tight text-red-600">{{ hotCount }}</span>
          <span class="text-[11px] font-semibold uppercase tracking-wider text-red-400">Hot (70+)</span>
        </CardContent>
      </Card>
      <Card class="border-orange-200 bg-orange-50/50 dark:bg-orange-950/20">
        <CardContent class="pt-5 pb-5 flex flex-col items-center gap-1">
          <span class="text-2xl font-bold tracking-tight text-orange-600">{{ warmCount }}</span>
          <span class="text-[11px] font-semibold uppercase tracking-wider text-orange-400">Warm (40–69)</span>
        </CardContent>
      </Card>
      <Card class="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
        <CardContent class="pt-5 pb-5 flex flex-col items-center gap-1">
          <span class="text-2xl font-bold tracking-tight text-blue-600">{{ coldCount }}</span>
          <span class="text-[11px] font-semibold uppercase tracking-wider text-blue-400">Cold (&lt;40)</span>
        </CardContent>
      </Card>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center gap-3 py-20 text-muted-foreground">
      <Loader2 class="h-8 w-8 animate-spin text-primary" />
      <p class="text-sm">Loading leads…</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!leads.length" class="flex flex-col items-center gap-3 py-20">
      <div class="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <Users class="h-8 w-8 text-muted-foreground" />
      </div>
      <p class="text-base font-semibold text-foreground">No leads captured yet</p>
      <p class="text-sm text-muted-foreground text-center max-w-sm">
        {{ hasFilters ? 'Try adjusting your filters.' : 'Leads appear here when visitors share their email or phone in chat.' }}
      </p>
    </div>

    <!-- Table -->
    <Card v-else class="flex-1 overflow-hidden">
      <div class="overflow-auto h-full">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Contact</TableHead>
              <TableHead>Heat</TableHead>
              <TableHead>Stage</TableHead>
              <TableHead>Client</TableHead>
              <TableHead>Captured</TableHead>
              <TableHead class="text-right"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="lead in leads" :key="lead.session_id" class="hover:bg-muted/30">

              <!-- Contact -->
              <TableCell class="min-w-[180px]">
                <div v-if="lead.lead_email" class="flex items-center gap-1.5 text-sm font-medium text-foreground">
                  <Mail class="h-3 w-3 text-muted-foreground shrink-0" />
                  {{ lead.lead_email }}
                </div>
                <div v-if="lead.lead_phone" class="flex items-center gap-1.5 text-xs text-muted-foreground mt-1">
                  <Phone class="h-3 w-3 shrink-0" />
                  {{ lead.lead_phone }}
                </div>
              </TableCell>

              <!-- Heat -->
              <TableCell>
                <span
                  class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold"
                  :class="{
                    'bg-red-100 text-red-700': lead.heat_score >= 70,
                    'bg-orange-100 text-orange-700': lead.heat_score >= 40 && lead.heat_score < 70,
                    'bg-blue-100 text-blue-700': lead.heat_score < 40,
                  }"
                >
                  {{ heatEmoji(lead.heat_score) }} {{ lead.heat_score }}%
                </span>
                <div class="mt-1.5 h-1 w-20 rounded-full bg-muted overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :style="{ width: lead.heat_score + '%', background: heatGradient(lead.heat_score) }"
                  />
                </div>
              </TableCell>

              <!-- Stage -->
              <TableCell>
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold"
                  :class="{
                    'bg-muted text-muted-foreground': lead.kanban_state === 'NEW',
                    'bg-blue-100 text-blue-700': lead.kanban_state === 'ENGAGED',
                    'bg-red-100 text-red-700': lead.kanban_state === 'HOT_LEAD',
                    'bg-green-100 text-green-700': lead.kanban_state === 'CONVERTED',
                    'bg-muted text-muted-foreground/60': lead.kanban_state === 'LOST',
                  }"
                >
                  {{ stageLabel(lead.kanban_state) }}
                </span>
              </TableCell>

              <!-- Client -->
              <TableCell class="text-sm font-medium text-foreground whitespace-nowrap">
                {{ lead.client_name }}
              </TableCell>

              <!-- Captured -->
              <TableCell class="min-w-[120px]">
                <span class="block text-sm text-foreground">{{ timeAgo(lead.created_at) }}</span>
                <span class="block text-[11px] text-muted-foreground mt-0.5">{{ formatDate(lead.created_at) }}</span>
              </TableCell>

              <!-- Actions -->
              <TableCell class="text-right">
                <Button variant="outline" size="sm" @click="viewChat(lead.session_id)">
                  <Eye class="h-3.5 w-3.5" />
                  View Chat
                </Button>
              </TableCell>

            </TableRow>
          </TableBody>
        </Table>
      </div>
    </Card>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Download, X, Loader2, Users, Mail, Phone, Eye } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import Table from '@/components/ui/Table.vue'
import TableHeader from '@/components/ui/TableHeader.vue'
import TableBody from '@/components/ui/TableBody.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableHead from '@/components/ui/TableHead.vue'
import TableCell from '@/components/ui/TableCell.vue'

const api = useAdminApi()
const router = useRouter()

const leads = ref([])
const clients = ref([])
const loading = ref(false)
const exporting = ref(false)

const filters = ref({
  client_id: '',
  date_from: '',
  date_to: '',
  min_heat: '',
})

const totalCount = computed(() => leads.value.length)
const hotCount   = computed(() => leads.value.filter(l => l.heat_score >= 70).length)
const warmCount  = computed(() => leads.value.filter(l => l.heat_score >= 40 && l.heat_score < 70).length)
const coldCount  = computed(() => leads.value.filter(l => l.heat_score < 40).length)

const hasFilters = computed(() =>
  filters.value.client_id || filters.value.date_from || filters.value.date_to || filters.value.min_heat !== ''
)

async function loadLeads() {
  loading.value = true
  try {
    const params = {
      client_id: filters.value.client_id || undefined,
      date_from: filters.value.date_from || undefined,
      date_to:   filters.value.date_to   || undefined,
      min_heat:  filters.value.min_heat !== '' ? filters.value.min_heat : undefined,
    }
    const res = await api.getLeads(params)
    leads.value = res?.leads || []
  } catch (e) {
    console.error('Failed to load leads:', e)
    leads.value = []
  } finally {
    loading.value = false
  }
}

async function loadClients() {
  try {
    const data = await api.getClients()
    clients.value = data || []
  } catch {}
}

function clearFilters() {
  filters.value = { client_id: '', date_from: '', date_to: '', min_heat: '' }
  loadLeads()
}

async function doExport() {
  exporting.value = true
  try {
    const params = {
      client_id: filters.value.client_id || undefined,
      date_from: filters.value.date_from || undefined,
      date_to:   filters.value.date_to   || undefined,
      min_heat:  filters.value.min_heat !== '' ? filters.value.min_heat : undefined,
    }
    await api.exportLeadsCSV(params)
  } catch (e) {
    console.error('Export failed:', e)
  } finally {
    exporting.value = false
  }
}

function viewChat(sessionId) {
  router.push(`/admin/godview/${sessionId}`)
}

function heatEmoji(score) {
  if (score >= 70) return '🔥'
  if (score >= 40) return '🟠'
  return '🔵'
}

function heatGradient(score) {
  if (score >= 70) return 'linear-gradient(90deg,#EF4444,#F97316)'
  if (score >= 40) return 'linear-gradient(90deg,#F97316,#EAB308)'
  return 'linear-gradient(90deg,#3B82F6,#06B6D4)'
}

const STAGE_MAP = {
  NEW:       'New',
  ENGAGED:   'Engaged',
  HOT_LEAD:  'Hot Lead',
  CONVERTED: 'Converted',
  LOST:      'Lost',
}

function stageLabel(k) { return STAGE_MAP[k] ?? k }

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(() => {
  loadClients()
  loadLeads()
})
</script>
