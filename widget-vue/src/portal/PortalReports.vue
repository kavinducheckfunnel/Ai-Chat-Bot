<template>
  <div class="flex flex-col gap-5 p-6 max-w-6xl">

    <!-- Header -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Reports</h1>
        <p class="text-sm text-muted-foreground mt-1">Performance overview for your chatbot</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- Period tabs -->
        <div class="flex rounded-lg border border-border overflow-hidden">
          <button
            v-for="p in periods" :key="p.val"
            class="px-3.5 py-1.5 text-xs font-medium transition-colors"
            :class="period === p.val ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'"
            @click="period = p.val; load()"
          >{{ p.label }}</button>
        </div>
        <!-- Export -->
        <Button variant="outline" size="sm" @click="exportCSV" :disabled="exporting" class="gap-2">
          <Loader2 v-if="exporting" class="h-3.5 w-3.5 animate-spin" />
          <Download v-else class="h-3.5 w-3.5" />
          Export CSV
        </Button>
      </div>
    </div>

    <!-- Tab navigation -->
    <div class="border-b border-border">
      <div class="flex gap-1">
        <button
          v-for="t in tabs" :key="t.key"
          class="flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
          :class="[
            activeTab === t.key ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
            t.locked && 'opacity-50 cursor-not-allowed hover:text-muted-foreground'
          ]"
          @click="t.locked ? showUpgrade(t.requiredPlan) : (activeTab = t.key)"
        >
          {{ t.label }}
          <Lock v-if="t.locked" class="h-3 w-3" />
        </button>
      </div>
    </div>

    <!-- Upgrade banner -->
    <div v-if="upgradeMsg" class="flex items-center gap-3 rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-700">
      <Star class="h-4 w-4 shrink-0 text-violet-500" />
      {{ upgradeMsg }}
      <RouterLink to="/portal/billing" class="ml-1 font-semibold underline">Upgrade plan →</RouterLink>
      <button class="ml-auto text-violet-400 hover:text-violet-600" @click="upgradeMsg = ''">
        <X class="h-4 w-4" />
      </button>
    </div>

    <!-- ═══ OVERVIEW TAB ═══ -->
    <template v-if="activeTab === 'overview'">

      <!-- Hero metric cards -->
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <template v-if="!loading">
          <Card v-for="m in heroMetrics" :key="m.key">
            <CardContent class="pt-5 pb-5">
              <div class="flex items-start gap-3">
                <div class="h-9 w-9 rounded-lg flex items-center justify-center shrink-0" :class="m.iconBg">
                  <component :is="m.icon" class="h-4.5 w-4.5" :class="m.iconColor" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-2xl font-bold tracking-tight text-foreground leading-none">{{ m.value }}</p>
                  <p class="text-xs text-muted-foreground mt-1.5">{{ m.label }}</p>
                </div>
              </div>
              <p class="mt-3 text-xs" :class="deltaClass(m.delta, m.invertDelta)">
                {{ formatDelta(m.delta) }} <span class="text-muted-foreground">vs prev period</span>
              </p>
            </CardContent>
          </Card>
        </template>
        <template v-else>
          <Card v-for="n in 4" :key="n">
            <CardContent class="pt-5 pb-5 animate-pulse space-y-3">
              <div class="flex gap-3">
                <div class="h-9 w-9 rounded-lg bg-muted shrink-0"></div>
                <div class="flex-1 space-y-2">
                  <div class="h-5 w-16 rounded bg-muted"></div>
                  <div class="h-3 w-24 rounded bg-muted"></div>
                </div>
              </div>
            </CardContent>
          </Card>
        </template>
      </div>

      <!-- Advanced metrics locked -->
      <div v-if="!canSeeCharts" class="flex items-center gap-4 rounded-xl border border-dashed border-violet-200 bg-violet-50/50 px-5 py-4">
        <Lock class="h-5 w-5 text-violet-400 shrink-0" />
        <div>
          <p class="text-sm font-semibold text-foreground">Advanced metrics locked</p>
          <p class="text-xs text-muted-foreground mt-0.5">Avg duration, missed chats, daily trends and more.
            <RouterLink to="/portal/billing" class="font-medium text-primary underline">Upgrade to Growth →</RouterLink>
          </p>
        </div>
      </div>

      <!-- Secondary metrics row -->
      <template v-else>
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <template v-if="!loading">
            <Card v-for="m in secondaryMetrics" :key="m.label">
              <CardContent class="pt-4 pb-4">
                <p class="text-xs text-muted-foreground font-medium">{{ m.label }}</p>
                <p class="text-xl font-bold text-foreground mt-1.5 tracking-tight">{{ m.value }}</p>
                <p class="text-xs mt-1" :class="deltaClass(m.delta, m.invertDelta)">{{ formatDelta(m.delta) }} vs prev</p>
              </CardContent>
            </Card>
          </template>
          <template v-else>
            <Card v-for="n in 4" :key="n">
              <CardContent class="pt-4 pb-4 animate-pulse space-y-2">
                <div class="h-3 w-24 rounded bg-muted"></div>
                <div class="h-5 w-16 rounded bg-muted"></div>
              </CardContent>
            </Card>
          </template>
        </div>

        <!-- Daily trend chart -->
        <Card v-if="!loading && analytics.daily_trend?.length">
          <CardContent class="pt-5 pb-5">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-semibold">Daily chats</h3>
              <span class="text-xs text-muted-foreground">{{ val('total_sessions') }} total</span>
            </div>
            <svg :viewBox="`0 0 ${cW} ${cH}`" preserveAspectRatio="none" class="w-full h-20 overflow-visible">
              <line v-for="y in gridYs" :key="y" :x1="pad" :y1="y" :x2="cW - pad" :y2="y" stroke="hsl(var(--border))" stroke-width="1"/>
              <defs>
                <linearGradient id="rptGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="hsl(var(--primary))" stop-opacity="0.25"/>
                  <stop offset="100%" stop-color="hsl(var(--primary))" stop-opacity="0"/>
                </linearGradient>
              </defs>
              <polygon v-if="chartPoints.length" :points="areaPolygon" fill="url(#rptGrad)"/>
              <polyline v-if="chartPoints.length" :points="chartPoints" fill="none" stroke="hsl(var(--primary))" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
              <circle v-for="(pt, i) in chartDots" :key="i" :cx="pt.x" :cy="pt.y" r="3" fill="hsl(var(--primary))"/>
            </svg>
            <div class="flex justify-between mt-1.5 px-1">
              <span v-for="(d, i) in chartLabelDates" :key="i" class="text-[10px] text-muted-foreground">{{ d }}</span>
            </div>
          </CardContent>
        </Card>

        <!-- Funnel + states -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <!-- Lead funnel -->
          <Card>
            <CardContent class="pt-5 pb-5">
              <h3 class="text-sm font-semibold mb-4">Lead funnel</h3>
              <div v-if="!loading" class="space-y-3">
                <div v-for="stage in funnel" :key="stage.key">
                  <div class="flex items-center justify-between mb-1.5">
                    <span class="text-xs text-muted-foreground">{{ stage.label }}</span>
                    <span class="text-sm font-bold" :style="{ color: stage.color }">{{ stage.count }}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div class="h-full rounded-full transition-all" :style="{ width: stageWidth(stage.count) + '%', background: stage.color }"></div>
                  </div>
                </div>
              </div>
              <div v-else class="space-y-3 animate-pulse">
                <div v-for="n in 4" :key="n" class="h-7 rounded bg-muted"></div>
              </div>
            </CardContent>
          </Card>

          <!-- Conversation states -->
          <Card>
            <CardContent class="pt-5 pb-5">
              <h3 class="text-sm font-semibold mb-4">Conversation states</h3>
              <div v-if="!loading" class="space-y-2.5">
                <div v-for="s in conversationStates" :key="s.label" class="flex items-center gap-3">
                  <div class="h-2 w-2 rounded-full shrink-0" :style="{ background: s.color }"></div>
                  <span class="flex-1 text-sm text-muted-foreground">{{ s.label }}</span>
                  <span class="text-sm font-semibold text-foreground">{{ s.count }}</span>
                </div>
              </div>
              <div v-else class="space-y-2.5 animate-pulse">
                <div v-for="n in 5" :key="n" class="h-5 rounded bg-muted"></div>
              </div>
            </CardContent>
          </Card>
        </div>
      </template>

    </template>

    <!-- ═══ CHATS TAB ═══ -->
    <template v-if="activeTab === 'chats' && canSeeChatsTab">

      <!-- Breakdown cards -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <template v-if="!loading">
          <Card class="border-blue-200 bg-blue-50/30">
            <CardContent class="pt-5 pb-5">
              <p class="text-xs font-semibold uppercase tracking-wide text-blue-500 mb-3">Automated (AI)</p>
              <p class="text-4xl font-bold tracking-tight text-foreground">{{ val('ai_handled') }}</p>
              <p class="text-xs text-muted-foreground mt-1.5"><span class="font-semibold text-foreground">{{ aiPct }}%</span> of total chats</p>
              <p class="text-xs mt-2" :class="deltaClass(delta('ai_handled'))">{{ formatDelta(delta('ai_handled')) }} vs prev period</p>
            </CardContent>
          </Card>
          <Card class="border-amber-200 bg-amber-50/30">
            <CardContent class="pt-5 pb-5">
              <p class="text-xs font-semibold uppercase tracking-wide text-amber-500 mb-3">Manual (God View)</p>
              <p class="text-4xl font-bold tracking-tight text-foreground">{{ val('manual_handled') }}</p>
              <p class="text-xs text-muted-foreground mt-1.5"><span class="font-semibold text-foreground">{{ manualPct }}%</span> of total chats</p>
              <p class="text-xs mt-2" :class="deltaClass(delta('manual_handled'))">{{ formatDelta(delta('manual_handled')) }} vs prev period</p>
            </CardContent>
          </Card>
          <Card class="border-red-200 bg-red-50/30">
            <CardContent class="pt-5 pb-5">
              <p class="text-xs font-semibold uppercase tracking-wide text-red-500 mb-3">Missed</p>
              <p class="text-4xl font-bold tracking-tight text-foreground">{{ val('missed_chats') }}</p>
              <p class="text-xs text-muted-foreground mt-1.5"><span class="font-semibold text-foreground">{{ missedPct }}%</span> of total chats</p>
              <p class="text-xs mt-2" :class="deltaClass(delta('missed_chats'), true)">{{ formatDelta(delta('missed_chats')) }} vs prev period</p>
            </CardContent>
          </Card>
        </template>
        <template v-else>
          <Card v-for="n in 3" :key="n">
            <CardContent class="pt-5 pb-5 animate-pulse space-y-3">
              <div class="h-3 w-20 rounded bg-muted"></div>
              <div class="h-8 w-12 rounded bg-muted"></div>
            </CardContent>
          </Card>
        </template>
      </div>

      <!-- AI Resolution rate -->
      <Card v-if="!loading">
        <CardContent class="pt-5 pb-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold">AI resolution rate</h3>
            <span class="text-xl font-bold text-primary">{{ val('ai_resolution_rate') }}%</span>
          </div>
          <div class="h-2 rounded-full bg-muted overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r from-primary to-primary/60 transition-all" :style="{ width: val('ai_resolution_rate') + '%' }"></div>
          </div>
          <p class="text-xs text-muted-foreground mt-2.5">{{ val('ai_handled') }} of {{ val('total_sessions') }} chats handled entirely by AI without human intervention.</p>
        </CardContent>
      </Card>

      <!-- Duration -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2" v-if="!loading">
        <Card>
          <CardContent class="pt-5 pb-5">
            <h3 class="text-sm font-semibold text-muted-foreground mb-2">Avg chat duration</h3>
            <p class="text-3xl font-bold tracking-tight text-foreground">{{ fmtDuration(val('avg_duration_seconds')) }}</p>
            <p class="text-xs mt-2" :class="deltaClass(delta('avg_duration_seconds'))">{{ formatDelta(delta('avg_duration_seconds')) }}s vs prev period</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="pt-5 pb-5">
            <h3 class="text-sm font-semibold text-muted-foreground mb-2">Total chat time</h3>
            <p class="text-3xl font-bold tracking-tight text-foreground">{{ fmtDuration(val('total_duration_seconds')) }}</p>
            <p class="text-xs text-muted-foreground mt-2">vs prev {{ fmtDuration(prev('total_duration_seconds')) }}</p>
          </CardContent>
        </Card>
      </div>

      <!-- N/A placeholders -->
      <Card v-if="!loading">
        <CardContent class="pt-5 pb-5">
          <h3 class="text-sm font-semibold mb-4">Additional metrics</h3>
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div v-for="m in naMetrics" :key="m.label" class="rounded-lg border border-border bg-muted/30 p-3.5">
              <p class="text-xs text-muted-foreground font-medium">{{ m.label }}</p>
              <p class="text-xl font-bold text-muted-foreground/50 mt-1">N/A</p>
              <p class="text-[10px] text-muted-foreground/50 mt-1 leading-tight">{{ m.hint }}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Recent sessions -->
      <Card>
        <CardContent class="p-0">
          <div class="px-5 py-4 border-b border-border">
            <h3 class="text-sm font-semibold">Recent activity</h3>
          </div>
          <div v-if="loading" class="space-y-0 animate-pulse">
            <div v-for="n in 5" :key="n" class="px-5 py-3 border-b border-border last:border-0">
              <div class="h-4 w-full rounded bg-muted"></div>
            </div>
          </div>
          <table v-else-if="recentSessions.length" class="w-full text-sm">
            <thead>
              <tr class="border-b border-border">
                <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Visitor</th>
                <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Type</th>
                <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">State</th>
                <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Heat</th>
                <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Msgs</th>
                <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in recentSessions" :key="s.session_id" class="border-b border-border last:border-0 hover:bg-muted/40 transition-colors">
                <td class="px-5 py-3 text-foreground font-medium">{{ s.lead_email || 'Visitor #' + String(s.session_id).slice(0, 6) }}</td>
                <td class="px-5 py-3">
                  <span class="inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold uppercase" :class="s.taken_over_by ? 'bg-amber-100 text-amber-600' : 'bg-blue-100 text-blue-600'">
                    {{ s.taken_over_by ? 'Manual' : 'AI' }}
                  </span>
                </td>
                <td class="px-5 py-3">
                  <span class="inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold uppercase" :class="kanbanBadgeClass(s.kanban_state)">{{ s.kanban_state || 'NEW' }}</span>
                </td>
                <td class="px-5 py-3">
                  <div class="flex items-center gap-2">
                    <div class="w-12 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div class="h-full rounded-full" :style="{ width: (s.heat_score || 0) + '%', background: heatColor(s.heat_score) }"></div>
                    </div>
                    <span class="text-xs text-muted-foreground font-mono">{{ Math.round(s.heat_score || 0) }}%</span>
                  </div>
                </td>
                <td class="px-5 py-3 font-mono text-muted-foreground">{{ s.message_count || 0 }}</td>
                <td class="px-5 py-3 text-xs text-muted-foreground">{{ formatDate(s.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="text-sm text-muted-foreground text-center py-8">No sessions yet.</p>
        </CardContent>
      </Card>

    </template>

    <!-- ═══ ENGAGEMENT TAB ═══ -->
    <template v-if="activeTab === 'engagement' && canSeeEngagementTab">

      <!-- Buyer signal averages -->
      <Card v-if="!loading">
        <CardContent class="pt-5 pb-5">
          <h3 class="text-sm font-semibold mb-4">Buyer signal averages</h3>
          <div class="space-y-4">
            <div v-for="sig in signals" :key="sig.label" class="flex items-center gap-4">
              <span class="text-sm text-muted-foreground w-36 shrink-0">{{ sig.label }}</span>
              <div class="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                <div class="h-full rounded-full transition-all" :style="{ width: sig.value + '%', background: sig.color }"></div>
              </div>
              <span class="text-sm font-semibold w-10 text-right" :style="{ color: sig.color }">{{ sig.value }}%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Heat dist + Kanban -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2" v-if="!loading">
        <!-- Heat distribution -->
        <Card>
          <CardContent class="pt-5 pb-5">
            <h3 class="text-sm font-semibold mb-4">Heat distribution</h3>
            <div class="flex h-12 rounded-lg overflow-hidden gap-0.5 mb-4">
              <div class="flex flex-col items-center justify-center min-w-8 transition-all bg-red-100" :style="{ flex: heatDist.hot }">
                <span class="text-sm font-bold text-red-600">{{ heatDist.hot }}</span>
                <span class="text-[9px] text-red-400 uppercase tracking-wide">Hot</span>
              </div>
              <div class="flex flex-col items-center justify-center min-w-8 transition-all bg-amber-100" :style="{ flex: heatDist.warm }">
                <span class="text-sm font-bold text-amber-600">{{ heatDist.warm }}</span>
                <span class="text-[9px] text-amber-400 uppercase tracking-wide">Warm</span>
              </div>
              <div class="flex flex-col items-center justify-center min-w-8 transition-all bg-primary/10" :style="{ flex: Math.max(heatDist.cold, 0.1) }">
                <span class="text-sm font-bold text-primary">{{ heatDist.cold }}</span>
                <span class="text-[9px] text-primary/60 uppercase tracking-wide">Cold</span>
              </div>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs text-muted-foreground">Avg heat score</span>
              <span class="text-lg font-bold" :style="{ color: heatColor(analytics.avg_heat_score) }">{{ analytics.avg_heat_score }}%</span>
            </div>
          </CardContent>
        </Card>

        <!-- Kanban pipeline -->
        <Card>
          <CardContent class="pt-5 pb-5">
            <h3 class="text-sm font-semibold mb-4">Kanban pipeline</h3>
            <div class="space-y-2.5">
              <div v-for="kb in kanbanBreakdown" :key="kb.key" class="flex items-center gap-3">
                <div class="h-2 w-2 rounded-full shrink-0" :style="{ background: kb.color }"></div>
                <span class="text-xs text-muted-foreground w-16 shrink-0">{{ kb.label }}</span>
                <div class="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div class="h-full rounded-full transition-all" :style="{ width: kanbanWidth(kb.count) + '%', background: kb.color }"></div>
                </div>
                <span class="text-sm font-semibold text-foreground w-7 text-right">{{ kb.count }}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- Engagement events -->
      <Card v-if="!loading">
        <CardContent class="pt-5 pb-5">
          <h3 class="text-sm font-semibold mb-4">Engagement events</h3>
          <div class="grid grid-cols-3 gap-4">
            <div v-for="ev in engagementEvents" :key="ev.label" class="flex flex-col items-center text-center rounded-lg border border-border bg-muted/30 p-4">
              <div class="h-9 w-9 rounded-lg flex items-center justify-center mb-2.5" :class="ev.bgClass">
                <component :is="ev.icon" class="h-4 w-4" :class="ev.colorClass" />
              </div>
              <p class="text-2xl font-bold tracking-tight text-foreground">{{ ev.value }}</p>
              <p class="text-xs text-muted-foreground mt-1">{{ ev.label }}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Big numbers: Leads + Hot -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2" v-if="!loading">
        <Card>
          <CardContent class="pt-5 pb-5">
            <h3 class="text-sm font-semibold text-muted-foreground mb-2">Leads captured</h3>
            <p class="text-5xl font-bold tracking-tight text-foreground">{{ val('leads_captured') }}</p>
            <p class="text-sm mt-2" :class="deltaClass(delta('leads_captured'))">{{ formatDelta(delta('leads_captured')) }} vs prev period</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="pt-5 pb-5">
            <h3 class="text-sm font-semibold text-muted-foreground mb-2">Hot leads</h3>
            <p class="text-5xl font-bold tracking-tight text-red-500">{{ val('hot_sessions') }}</p>
            <p class="text-sm mt-2" :class="deltaClass(delta('hot_sessions'))">{{ formatDelta(delta('hot_sessions')) }} vs prev period</p>
          </CardContent>
        </Card>
      </div>

    </template>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, h } from 'vue'
import { Download, Lock, Star, X, Loader2, MessageSquare, Users, Zap, TrendingUp, Eye, DoorOpen, Tag } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

const props = defineProps({ client: Object })
const api = useAdminApi()

const loading = ref(true)
const exporting = ref(false)
const period = ref('30d')
const activeTab = ref('overview')
const analytics = ref({})
const recentSessions = ref([])
const upgradeMsg = ref('')
const metricLimit = ref(-1)

// ── Feature gating ─────────────────────────────────────────────────────────────
const canSeeCharts = computed(() => metricLimit.value < 0 || metricLimit.value >= 7)
const canSeeChatsTab = computed(() => metricLimit.value < 0 || metricLimit.value >= 7)
const canSeeEngagementTab = computed(() => metricLimit.value < 0)

function showUpgrade(plan) {
  upgradeMsg.value = `This section requires the ${plan} plan or higher.`
}

// ── Periods ────────────────────────────────────────────────────────────────────
const periods = computed(() => {
  const all = [
    { val: 'today', label: 'Today' },
    { val: '7d', label: '7d' },
    { val: '30d', label: '30d' },
    { val: '90d', label: '90d' },
  ]
  return canSeeCharts.value ? all : all.slice(0, 3)
})

const tabs = computed(() => [
  { key: 'overview',   label: 'Overview',   locked: false },
  { key: 'chats',      label: 'Chats',      locked: !canSeeChatsTab.value,      requiredPlan: 'Growth' },
  { key: 'engagement', label: 'Engagement', locked: !canSeeEngagementTab.value,  requiredPlan: 'Pro' },
])

// ── Metric helpers ─────────────────────────────────────────────────────────────
function val(key) {
  const m = analytics.value[key]
  if (m && typeof m === 'object' && 'value' in m) return m.value
  return m ?? 0
}
function delta(key) {
  const m = analytics.value[key]
  if (m && typeof m === 'object' && 'delta' in m) return m.delta
  return 0
}
function prev(key) {
  const m = analytics.value[key]
  if (m && typeof m === 'object' && 'previous' in m) return m.previous
  return 0
}

function formatDelta(d) {
  if (d === 0 || d == null) return '—'
  return d > 0 ? `+${d}` : `${d}`
}
function formatDeltaFloat(d) {
  if (d === 0 || d == null) return '—'
  return d > 0 ? `+${d.toFixed(1)}` : `${d.toFixed(1)}`
}
function deltaClass(d, invert = false) {
  if (d === 0 || d == null) return 'text-muted-foreground'
  const positive = d > 0
  const good = invert ? !positive : positive
  return good ? 'text-emerald-600 font-medium' : 'text-red-500 font-medium'
}

function fmtDuration(seconds) {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

// ── SVG chart ──────────────────────────────────────────────────────────────────
const cW = 600
const cH = 100
const pad = 12

const chartDots = computed(() => {
  const trend = analytics.value.daily_trend || []
  if (trend.length < 2) return []
  const maxCount = Math.max(...trend.map(d => d.count), 1)
  return trend.map((d, i) => ({
    x: pad + (i / (trend.length - 1)) * (cW - 2 * pad),
    y: pad + (1 - d.count / maxCount) * (cH - 2 * pad),
  }))
})

const chartPoints = computed(() => chartDots.value.map(p => `${p.x},${p.y}`).join(' '))

const areaPolygon = computed(() => {
  const pts = chartDots.value
  if (!pts.length) return ''
  const first = pts[0]
  const last = pts[pts.length - 1]
  return [...pts.map(p => `${p.x},${p.y}`), `${last.x},${cH - pad}`, `${first.x},${cH - pad}`].join(' ')
})

const gridYs = computed(() => [pad, pad + (cH - 2 * pad) / 2, cH - pad])

const chartLabelDates = computed(() => {
  const trend = analytics.value.daily_trend || []
  if (!trend.length) return []
  const step = Math.max(1, Math.floor(trend.length / 6))
  return trend.filter((_, i) => i % step === 0 || i === trend.length - 1).map(d => d.date)
})

// ── Funnel / states ────────────────────────────────────────────────────────────
const funnel = computed(() => {
  const kb = analytics.value.kanban_breakdown || {}
  return [
    { key: 'new',       label: 'New',       count: kb.NEW || 0,       color: '#64748b' },
    { key: 'engaged',   label: 'Engaged',   count: kb.ENGAGED || 0,   color: '#6366f1' },
    { key: 'hot',       label: 'Hot lead',  count: kb.HOT_LEAD || 0,  color: '#f59e0b' },
    { key: 'converted', label: 'Converted', count: kb.CONVERTED || 0, color: '#22c55e' },
  ]
})

function stageWidth(count) {
  const max = Math.max(...funnel.value.map(s => s.count), 1)
  return Math.round((count / max) * 100)
}

const conversationStates = computed(() => {
  const f = analytics.value.funnel || {}
  return [
    { label: 'Research',     count: f.RESEARCH     || 0, color: '#64748b' },
    { label: 'Evaluation',   count: f.EVALUATION   || 0, color: '#6366f1' },
    { label: 'Objection',    count: f.OBJECTION    || 0, color: '#f59e0b' },
    { label: 'Recovery',     count: f.RECOVERY     || 0, color: '#ef4444' },
    { label: 'Ready to buy', count: f.READY_TO_BUY || 0, color: '#22c55e' },
  ]
})

// ── Hero metrics ───────────────────────────────────────────────────────────────
const heroMetrics = computed(() => [
  { key: 'total_sessions',     label: 'Total chats',        value: val('total_sessions'),            delta: delta('total_sessions'),     icon: MessageSquare, iconBg: 'bg-primary/10',    iconColor: 'text-primary',    invertDelta: false },
  { key: 'unique_visitors',    label: 'Unique visitors',    value: val('unique_visitors'),           delta: delta('unique_visitors'),    icon: Users,         iconBg: 'bg-emerald-100',   iconColor: 'text-emerald-600', invertDelta: false },
  { key: 'ai_resolution_rate', label: 'AI resolution rate', value: val('ai_resolution_rate') + '%', delta: delta('ai_resolution_rate'), icon: Zap,           iconBg: 'bg-amber-100',     iconColor: 'text-amber-600',   invertDelta: false },
  { key: 'leads_captured',     label: 'Leads captured',     value: val('leads_captured'),            delta: delta('leads_captured'),     icon: TrendingUp,    iconBg: 'bg-violet-100',    iconColor: 'text-violet-600',  invertDelta: false },
])

const secondaryMetrics = computed(() => [
  { label: 'Avg chat duration', value: fmtDuration(val('avg_duration_seconds')), delta: delta('avg_duration_seconds'), invertDelta: false },
  { label: 'Total chat time',   value: fmtDuration(val('total_duration_seconds')), delta: delta('total_duration_seconds'), invertDelta: false },
  { label: 'Missed chats',      value: val('missed_chats'),       delta: delta('missed_chats'),      invertDelta: true },
  { label: 'AI resolution rate',value: val('ai_resolution_rate') + '%', delta: delta('ai_resolution_rate'), invertDelta: false },
])

// ── Chats tab ──────────────────────────────────────────────────────────────────
const total = computed(() => val('total_sessions') || 1)
const aiPct = computed(() => Math.round(val('ai_handled') / total.value * 100))
const manualPct = computed(() => Math.round(val('manual_handled') / total.value * 100))
const missedPct = computed(() => Math.round(val('missed_chats') / total.value * 100))

const naMetrics = [
  { label: 'CSAT score',          hint: 'Requires customer survey integration' },
  { label: 'First response time', hint: 'Agent timing not yet tracked' },
  { label: 'Queued customers',    hint: 'Queue system not configured' },
  { label: 'Chats per hour (AI)', hint: 'Hourly rate breakdown coming soon' },
]

// ── Engagement tab ─────────────────────────────────────────────────────────────
const signals = computed(() => [
  { label: 'Purchase intent', value: analytics.value.avg_intent  || 0, color: '#6366f1' },
  { label: 'Budget signal',   value: analytics.value.avg_budget  || 0, color: '#22c55e' },
  { label: 'Urgency signal',  value: analytics.value.avg_urgency || 0, color: '#f59e0b' },
])

const heatDist = computed(() => analytics.value.heat_distribution || { hot: 0, warm: 0, cold: 0 })

const kanbanBreakdown = computed(() => {
  const kb = analytics.value.kanban_breakdown || {}
  return [
    { key: 'NEW',       label: 'New',       count: kb.NEW       || 0, color: '#64748b' },
    { key: 'ENGAGED',   label: 'Engaged',   count: kb.ENGAGED   || 0, color: '#6366f1' },
    { key: 'HOT_LEAD',  label: 'Hot lead',  count: kb.HOT_LEAD  || 0, color: '#f59e0b' },
    { key: 'CONVERTED', label: 'Converted', count: kb.CONVERTED || 0, color: '#22c55e' },
    { key: 'LOST',      label: 'Lost',      count: kb.LOST      || 0, color: '#ef4444' },
  ]
})

function kanbanWidth(count) {
  const max = Math.max(...kanbanBreakdown.value.map(k => k.count), 1)
  return Math.round((count / max) * 100)
}

const engagementEvents = computed(() => {
  const ev = analytics.value.analytics_events || {}
  return [
    { label: 'Page views',           value: ev.page_views          || 0, icon: Eye,      bgClass: 'bg-primary/10',    colorClass: 'text-primary' },
    { label: 'Exit intent fired',    value: ev.exit_intent_count   || 0, icon: DoorOpen, bgClass: 'bg-red-100',       colorClass: 'text-red-500' },
    { label: 'Pricing page visits',  value: ev.pricing_page_visits || 0, icon: Tag,      bgClass: 'bg-amber-100',     colorClass: 'text-amber-600' },
  ]
})

// ── Common helpers ─────────────────────────────────────────────────────────────
function heatColor(score) {
  if (!score) return 'hsl(var(--muted-foreground))'
  if (score > 70) return '#ef4444'
  if (score > 40) return '#f59e0b'
  return '#6366f1'
}

function kanbanBadgeClass(state) {
  if (state === 'HOT_LEAD') return 'bg-red-100 text-red-600'
  if (state === 'CONVERTED') return 'bg-emerald-100 text-emerald-600'
  if (state === 'ENGAGED') return 'bg-blue-100 text-blue-600'
  return 'bg-muted text-muted-foreground'
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString()
}

// ── Data loading ───────────────────────────────────────────────────────────────
async function load() {
  if (!props.client) return
  loading.value = true
  try {
    const [a, sessions, sub] = await Promise.all([
      api.getPortalAnalytics(props.client.id, period.value),
      api.getPortalSessions(props.client.id, { limit: 20 }),
      api.getSubscription().catch(() => null),
    ])
    analytics.value = a || {}
    recentSessions.value = Array.isArray(sessions) ? sessions : (sessions?.results || [])
    if (sub?.plan?.max_dashboard_metrics != null) {
      metricLimit.value = sub.plan.max_dashboard_metrics
    }
  } catch {} finally {
    loading.value = false
  }
}

async function exportCSV() {
  if (!props.client) return
  exporting.value = true
  try {
    await api.exportAnalyticsCSV(props.client.id, period.value)
  } catch (e) {
    alert('Export failed: ' + (e.message || 'Unknown error'))
  } finally {
    exporting.value = false
  }
}

onMounted(load)
watch(() => props.client, load)
</script>
