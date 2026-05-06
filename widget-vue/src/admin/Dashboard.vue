<template>
  <div class="flex flex-col gap-6 p-6">

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Intelligence</h1>
        <p class="text-sm text-muted-foreground mt-1">Platform intelligence &amp; tenant operations</p>
      </div>
      <Button variant="outline" size="sm" @click="loadAll" :disabled="loading">
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        Refresh
      </Button>
    </div>

    <!-- Tabs -->
    <Tabs :default-value="activeTab" @update:model-value="v => activeTab = v">
      <TabsList>
        <TabsTrigger v-for="t in tabs" :key="t.key" :value="t.key">
          {{ t.label }}
          <span v-if="t.key === 'alerts' && alertCount > 0" class="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
            {{ alertCount }}
          </span>
        </TabsTrigger>
      </TabsList>

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center gap-3 py-20 text-muted-foreground">
        <Loader2 class="h-8 w-8 animate-spin text-primary" />
        <p class="text-sm">Loading platform data…</p>
      </div>

      <!-- ═══ OVERVIEW TAB ═══ -->
      <TabsContent v-else value="overview" class="space-y-6 mt-4">

        <!-- Revenue cards -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 xl:grid-cols-7">
          <Card v-for="m in revenueMetrics" :key="m.label" :class="m.cardClass">
            <CardContent class="pt-4 pb-4">
              <p class="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{{ m.label }}</p>
              <p class="text-xl font-bold tracking-tight mt-1" :class="m.valueClass">{{ m.value }}</p>
              <p class="text-xs text-muted-foreground mt-0.5" :class="m.subClass">{{ m.sub }}</p>
            </CardContent>
          </Card>
        </div>

        <!-- Charts row -->
        <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <!-- MRR Trend -->
          <Card class="xl:col-span-2">
            <CardHeader>
              <div class="flex items-center justify-between">
                <CardTitle class="text-sm">MRR Trend</CardTitle>
                <span class="text-xs text-muted-foreground">Last 6 months</span>
              </div>
            </CardHeader>
            <CardContent>
              <svg class="w-full h-28" viewBox="0 0 400 120" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="mrr-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="hsl(var(--primary))" stop-opacity="0.2"/>
                    <stop offset="100%" stop-color="hsl(var(--primary))" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <path :d="mrrAreaPath" fill="url(#mrr-grad)"/>
                <path :d="mrrLinePath" fill="none" stroke="hsl(var(--primary))" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <circle v-for="(p,i) in mrrPoints" :key="i" :cx="p.x" :cy="p.y" r="3.5" fill="hsl(var(--primary))"/>
              </svg>
              <div class="flex justify-between text-[11px] text-muted-foreground mt-2">
                <span v-for="m in revenue.mrr_trend" :key="m.month">{{ m.month.split(' ')[0] }}</span>
              </div>
            </CardContent>
          </Card>

          <!-- Plan Distribution -->
          <Card>
            <CardHeader>
              <div class="flex items-center justify-between">
                <CardTitle class="text-sm">Plan Distribution</CardTitle>
                <span class="text-xs text-muted-foreground">{{ revenue.total_tenants }} tenants</span>
              </div>
            </CardHeader>
            <CardContent>
              <div class="flex items-center gap-4">
                <svg viewBox="0 0 120 120" class="w-28 h-28 shrink-0">
                  <circle cx="60" cy="60" r="48" fill="none" stroke="hsl(var(--muted))" stroke-width="18"/>
                  <circle v-for="(seg,i) in donutSegments" :key="i"
                    cx="60" cy="60" r="48" fill="none"
                    :stroke="seg.color" stroke-width="18"
                    :stroke-dasharray="`${seg.dash} ${seg.gap}`"
                    :stroke-dashoffset="seg.offset"
                    style="transform-origin:center;transform:rotate(-90deg)"
                  />
                  <text x="60" y="56" text-anchor="middle" class="text-lg font-bold fill-foreground" font-size="18" font-weight="700">{{ revenue.active_tenants }}</text>
                  <text x="60" y="70" text-anchor="middle" font-size="9" fill="currentColor" class="fill-muted-foreground">active</text>
                </svg>
                <div class="flex flex-col gap-2">
                  <div v-for="d in revenue.plan_distribution" :key="d.plan" class="flex items-center gap-2 text-xs">
                    <span class="h-2 w-2 rounded-full shrink-0" :style="{ background: d.color }"></span>
                    <span class="text-muted-foreground flex-1">{{ d.plan }}</span>
                    <span class="font-semibold text-foreground">{{ d.count }}</span>
                    <span class="text-emerald-600 text-[10px]">${{ d.mrr.toFixed(0) }}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- Platform stats -->
        <div class="grid grid-cols-3 gap-3 sm:grid-cols-6">
          <Card v-for="s in platformStats" :key="s.label">
            <CardContent class="pt-4 pb-4">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{{ s.label }}</p>
              <p class="text-lg font-bold mt-1">{{ s.value }}</p>
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      <!-- ═══ HEALTH BOARD TAB ═══ -->
      <TabsContent value="health" class="mt-4 space-y-4">
        <div class="flex flex-wrap items-center gap-3">
          <div class="relative">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input v-model="healthSearch" placeholder="Search tenant…" class="pl-8 w-52" />
          </div>
          <div class="flex gap-2 flex-wrap">
            <button
              v-for="r in riskFilters" :key="r.val"
              class="rounded-full px-3 py-1 text-xs font-medium border transition-colors"
              :class="riskFilter === r.val
                ? 'bg-primary text-primary-foreground border-primary'
                : 'border-border text-muted-foreground hover:border-foreground/30'"
              @click="riskFilter = riskFilter === r.val ? 'all' : r.val"
            >
              {{ r.label }} <span class="ml-1 font-bold">{{ riskCount(r.val) }}</span>
            </button>
          </div>
        </div>

        <Card class="overflow-hidden">
          <div class="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead @click="sortBy('company')" class="cursor-pointer">Tenant</TableHead>
                  <TableHead @click="sortBy('plan')" class="cursor-pointer">Plan</TableHead>
                  <TableHead @click="sortBy('sessions_30d')" class="cursor-pointer">Sessions 30d</TableHead>
                  <TableHead @click="sortBy('plan_price')" class="cursor-pointer">MRR</TableHead>
                  <TableHead>Stripe</TableHead>
                  <TableHead @click="sortBy('health_score')" class="cursor-pointer">Health</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="t in filteredTenants" :key="t.tenant_id" class="hover:bg-muted/30">
                  <TableCell>
                    <div class="flex items-center gap-2.5">
                      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground text-xs font-bold">
                        {{ t.company[0]?.toUpperCase() }}
                      </div>
                      <div>
                        <p class="text-sm font-medium text-foreground">{{ t.company }}</p>
                        <p class="text-[11px] text-muted-foreground">{{ t.email }}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge :variant="planVariant(t.plan)">{{ t.plan }}</Badge>
                  </TableCell>
                  <TableCell class="font-medium text-primary">{{ t.sessions_30d }}</TableCell>
                  <TableCell class="font-medium text-emerald-600">${{ t.plan_price.toFixed(0) }}</TableCell>
                  <TableCell>
                    <Badge :variant="stripeVariant(t.stripe_status)">{{ t.stripe_status || 'none' }}</Badge>
                    <span v-if="t.trial_expires_in_days !== null" class="ml-1 text-[10px] font-bold text-amber-600">Trial {{ t.trial_expires_in_days }}d</span>
                  </TableCell>
                  <TableCell>
                    <div class="flex items-center gap-2">
                      <div class="h-1.5 w-20 rounded-full bg-muted overflow-hidden">
                        <div class="h-full rounded-full" :style="{ width: t.health_score+'%', background: healthColor(t.health_score) }"/>
                      </div>
                      <span class="text-xs font-semibold text-muted-foreground">{{ t.health_score }}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge :variant="riskVariant(t.risk)">{{ t.risk.replace(/_/g,' ') }}</Badge>
                  </TableCell>
                  <TableCell>
                    <div class="flex gap-1">
                      <Button variant="ghost" size="icon" title="Impersonate" @click="impersonate(t)"><span>🔑</span></Button>
                      <Button variant="ghost" size="icon" title="Change plan" @click="openPlanModal(t)"><span>⬆️</span></Button>
                      <Button variant="ghost" size="icon" title="Feature overrides" @click="openOverridesModal(t)"><span>🎁</span></Button>
                      <Button variant="ghost" size="icon" title="Extend trial" @click="extendTrial(t)"><span>⏱️</span></Button>
                    </div>
                  </TableCell>
                </TableRow>
                <TableRow v-if="filteredTenants.length === 0">
                  <TableCell colspan="8" class="text-center text-muted-foreground py-8">No tenants match the current filter.</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </Card>
      </TabsContent>

      <!-- ═══ ALERTS TAB ═══ -->
      <TabsContent value="alerts" class="mt-4">
        <div v-if="alerts.length === 0" class="flex flex-col items-center gap-3 py-16 text-muted-foreground">
          <CheckCircle class="h-10 w-10 text-emerald-500" />
          <p class="text-sm">All clear — no lifecycle alerts right now.</p>
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="(a, idx) in alerts" :key="idx"
            class="flex items-center gap-4 rounded-lg border p-4"
            :class="{
              'border-red-200 bg-red-50/50': a.severity === 'critical',
              'border-orange-200 bg-orange-50/50': a.severity === 'warning',
              'border-border': a.severity === 'info',
            }"
          >
            <span class="text-lg shrink-0">
              <span v-if="a.severity==='critical'">🔴</span>
              <span v-else-if="a.severity==='warning'">🟠</span>
              <span v-else>🔵</span>
            </span>
            <div class="flex-1">
              <p class="text-sm font-semibold text-foreground">{{ a.label }}</p>
              <p class="text-xs text-muted-foreground mt-0.5">{{ a.message }}</p>
            </div>
            <Button variant="outline" size="sm" @click="handleAlertAction(a)">
              {{ alertActionLabel(a.action) }}
            </Button>
          </div>
        </div>
      </TabsContent>

      <!-- ═══ AUDIT LOG TAB ═══ -->
      <TabsContent value="audit" class="mt-4 space-y-4">
        <div class="flex gap-3">
          <div class="relative">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input v-model="auditSearch" placeholder="Search by tenant…" class="pl-8 w-52" @input="loadAudit" />
          </div>
          <select
            v-model="auditAction"
            @change="loadAudit"
            class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="">All actions</option>
            <option v-for="ac in auditActions" :key="ac" :value="ac">{{ ac }}</option>
          </select>
        </div>

        <Card class="overflow-hidden">
          <div class="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="a in auditLogs" :key="a.id" class="hover:bg-muted/20">
                  <TableCell class="font-mono text-[11px] text-muted-foreground">{{ fmtDate(a.timestamp) }}</TableCell>
                  <TableCell><Badge variant="secondary">{{ a.actor }}</Badge></TableCell>
                  <TableCell><Badge variant="outline">{{ a.action }}</Badge></TableCell>
                  <TableCell class="text-sm text-muted-foreground">{{ a.target_label }}</TableCell>
                  <TableCell class="text-xs text-muted-foreground">{{ a.notes }}</TableCell>
                </TableRow>
                <TableRow v-if="auditLogs.length === 0">
                  <TableCell colspan="5" class="text-center text-muted-foreground py-8">No audit entries found.</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </Card>

        <div v-if="auditTotal > 50" class="flex items-center justify-center gap-3 text-sm text-muted-foreground">
          <Button variant="outline" size="sm" @click="auditPage--; loadAudit()" :disabled="auditPage <= 1">←</Button>
          <span>Page {{ auditPage }} of {{ Math.ceil(auditTotal / 50) }}</span>
          <Button variant="outline" size="sm" @click="auditPage++; loadAudit()" :disabled="auditPage >= Math.ceil(auditTotal / 50)">→</Button>
        </div>
      </TabsContent>

      <!-- ═══ ANNOUNCEMENTS TAB ═══ -->
      <TabsContent value="announce" class="mt-4">
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card class="lg:col-span-2">
            <CardHeader><CardTitle>New Announcement</CardTitle></CardHeader>
            <CardContent class="space-y-4">
              <div class="space-y-1.5">
                <Label>Title</Label>
                <Input v-model="annForm.title" placeholder="e.g. Scheduled maintenance" />
              </div>
              <div class="space-y-1.5">
                <Label>Message</Label>
                <Textarea v-model="annForm.body" placeholder="Details…" :rows="3" />
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-1.5">
                  <Label>Type</Label>
                  <select v-model="annForm.type" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
                    <option value="info">Info</option>
                    <option value="warning">Warning</option>
                    <option value="feature">New Feature</option>
                    <option value="maintenance">Maintenance</option>
                  </select>
                </div>
                <div class="space-y-1.5">
                  <Label>Target</Label>
                  <select v-model="annForm.target" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
                    <option value="all">All Tenants</option>
                    <option value="free">Free Plan</option>
                    <option value="paid">Paid Plans</option>
                  </select>
                </div>
              </div>
              <div class="space-y-1.5">
                <Label>CTA Button (optional)</Label>
                <Input v-model="annForm.cta_label" placeholder="e.g. Learn more" class="mb-2" />
                <Input v-model="annForm.cta_url" placeholder="https://…" />
              </div>
              <Button class="w-full" @click="createAnnouncement" :disabled="annSaving">
                <Loader2 v-if="annSaving" class="h-4 w-4 animate-spin" />
                {{ annSaving ? 'Sending…' : annSent ? '✓ Sent!' : 'Publish Announcement' }}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>How it works</CardTitle></CardHeader>
            <CardContent>
              <ul class="space-y-3 text-sm text-muted-foreground list-disc list-inside">
                <li>Banners appear in the tenant portal after next login</li>
                <li>Target "Free Plan" to push upgrade prompts only to free users</li>
                <li>Use "Maintenance" type to warn all tenants of downtime</li>
                <li>CTA button links to any URL — use <code class="rounded bg-muted px-1 text-xs text-foreground">/portal/billing</code> for upgrade CTAs</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </TabsContent>
    </Tabs>

    <!-- Plan Change Dialog -->
    <Dialog :open="planModal.open" @close="planModal.open = false">
      <DialogHeader>
        <DialogTitle>Change Plan — {{ planModal.tenant?.company }}</DialogTitle>
      </DialogHeader>
      <div class="px-6 pb-4 space-y-4">
        <div class="space-y-1.5">
          <Label>New Plan</Label>
          <select v-model="planModal.selectedPlanId" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
            <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }} — ${{ p.price_monthly }}/mo</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <Label>Notes</Label>
          <Input v-model="planModal.remarks" placeholder="Reason for change…" />
        </div>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="planModal.open = false">Cancel</Button>
        <Button @click="savePlanChange" :disabled="planModal.saving">
          <Loader2 v-if="planModal.saving" class="h-4 w-4 animate-spin" />
          Confirm Change
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Feature Override Dialog -->
    <Dialog :open="overrideModal.open" @close="overrideModal.open = false">
      <DialogHeader>
        <DialogTitle>Feature Overrides — {{ overrideModal.tenant?.company }}</DialogTitle>
      </DialogHeader>
      <div class="px-6 pb-4 space-y-4">
        <div v-if="overrideModal.loading" class="text-sm text-muted-foreground">Loading…</div>
        <div v-else-if="overrideModal.items.length === 0" class="text-sm text-muted-foreground">No overrides set.</div>
        <div v-else class="space-y-2">
          <div v-for="o in overrideModal.items" :key="o.id" class="flex items-center gap-3 rounded-lg border p-3 text-sm">
            <span class="font-mono text-xs font-medium text-primary flex-1">{{ o.feature_name }}</span>
            <Badge :variant="o.enabled ? 'success' : 'destructive'">{{ o.enabled ? 'ON' : 'OFF' }}</Badge>
            <span class="text-xs text-muted-foreground">{{ o.reason }}</span>
            <Button variant="ghost" size="icon" class="h-6 w-6 text-destructive" @click="deleteOverride(o)">✕</Button>
          </div>
        </div>
        <Separator />
        <div class="space-y-3">
          <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Add Override</p>
          <div class="grid grid-cols-2 gap-3">
            <select v-model="overrideModal.newFeature" class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
              <option value="">Select feature…</option>
              <option v-for="f in allFeatures" :key="f.key" :value="f.key">{{ f.label }}</option>
            </select>
            <select v-model="overrideModal.newEnabled" class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
              <option :value="true">Enable</option>
              <option :value="false">Disable</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <Input v-model="overrideModal.newReason" placeholder="Reason (e.g. VIP deal)" />
            <input type="datetime-local" v-model="overrideModal.newExpiry" class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring" />
          </div>
          <Button @click="saveOverride" :disabled="!overrideModal.newFeature || overrideModal.saving">
            <Loader2 v-if="overrideModal.saving" class="h-4 w-4 animate-spin" />
            Grant Override
          </Button>
        </div>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="overrideModal.open = false">Close</Button>
      </DialogFooter>
    </Dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RefreshCw, Loader2, Search, CheckCircle } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Textarea from '@/components/ui/Textarea.vue'
import Separator from '@/components/ui/Separator.vue'
import Badge from '@/components/ui/Badge.vue'
import Tabs from '@/components/ui/Tabs.vue'
import TabsList from '@/components/ui/TabsList.vue'
import TabsTrigger from '@/components/ui/TabsTrigger.vue'
import TabsContent from '@/components/ui/TabsContent.vue'
import Table from '@/components/ui/Table.vue'
import TableHeader from '@/components/ui/TableHeader.vue'
import TableBody from '@/components/ui/TableBody.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableHead from '@/components/ui/TableHead.vue'
import TableCell from '@/components/ui/TableCell.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DialogHeader from '@/components/ui/DialogHeader.vue'
import DialogTitle from '@/components/ui/DialogTitle.vue'
import DialogFooter from '@/components/ui/DialogFooter.vue'

const api = useAdminApi()
const loading = ref(true)
const activeTab = ref('overview')
const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'health',   label: 'Health Board' },
  { key: 'alerts',   label: 'Alerts' },
  { key: 'audit',    label: 'Audit Log' },
  { key: 'announce', label: 'Announcements' },
]

const revenue  = ref({ mrr:0, arr:0, new_mrr:0, churned_mrr:0, net_mrr_growth:0, arpu:0, active_tenants:0, total_tenants:0, past_due:0, trialing:0, plan_distribution:[], mrr_trend:[] })
const tenants  = ref([])
const alerts   = ref([])
const auditLogs = ref([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditSearch = ref('')
const auditAction = ref('')
const plans = ref([])
const stats = ref({})

const auditActions = ['PLAN_CHANGE','IMPERSONATE_START','FEATURE_OVERRIDE','FEATURE_OVERRIDE_REVOKE','TRIAL_EXTEND','ACCOUNT_SUSPEND','BROADCAST_SEND']

const revenueMetrics = computed(() => [
  { label:'MRR',         value:'$'+fmt(revenue.value.mrr),          sub:'Monthly recurring' },
  { label:'ARR',         value:'$'+fmt(revenue.value.arr),          sub:'Annualised' },
  { label:'New MRR',     value:'+$'+fmt(revenue.value.new_mrr),     sub:'This month', subClass:'text-emerald-600' },
  { label:'Churned MRR', value:'-$'+fmt(revenue.value.churned_mrr), sub:'This month', subClass: revenue.value.churned_mrr > 0 ? 'text-red-500' : '' },
  { label:'ARPU',        value:'$'+fmt(revenue.value.arpu),         sub:'Per active tenant' },
  { label:'Past Due',    value:revenue.value.past_due,              sub:'Payment failures', cardClass: revenue.value.past_due > 0 ? 'border-red-200' : '' },
  { label:'Trialing',    value:revenue.value.trialing,              sub:'Active trials' },
])

function fmt(n) {
  if (!n && n !== 0) return '0'
  if (n >= 1000) return (n/1000).toFixed(1)+'k'
  return Number(n).toFixed(0)
}

const mrrPoints = computed(() => {
  const trend = revenue.value.mrr_trend || []
  if (trend.length < 2) return []
  const vals = trend.map(t => t.mrr)
  const maxV = Math.max(...vals, 1)
  return trend.map((t, i) => ({
    x: (i / (trend.length - 1)) * 380 + 10,
    y: 110 - (t.mrr / maxV) * 100,
  }))
})
const mrrLinePath = computed(() => {
  const pts = mrrPoints.value
  if (!pts.length) return ''
  return pts.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ')
})
const mrrAreaPath = computed(() => {
  const pts = mrrPoints.value
  if (!pts.length) return ''
  const line = pts.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ')
  const last = pts[pts.length - 1], first = pts[0]
  return `${line} L ${last.x} 120 L ${first.x} 120 Z`
})

const donutSegments = computed(() => {
  const dist = revenue.value.plan_distribution || []
  const total = dist.reduce((s, d) => s + d.count, 0) || 1
  const circum = 2 * Math.PI * 48
  let offset = 0
  return dist.map(d => {
    const dash = (d.count / total) * circum
    const seg = { dash, gap: circum - dash, offset: -offset, color: d.color }
    offset += dash
    return seg
  })
})

const platformStats = computed(() => [
  { label:'Total Sessions',  value: stats.value.total_sessions  || 0 },
  { label:'Active Clients',  value: stats.value.total_clients   || 0 },
  { label:'Hot Sessions',    value: stats.value.hot_sessions    || 0 },
  { label:'Active Tenants',  value: revenue.value.active_tenants },
  { label:'Total Tenants',   value: revenue.value.total_tenants },
  { label:'Net MRR Growth',  value: '$'+fmt(revenue.value.net_mrr_growth) },
])

const healthSearch = ref('')
const riskFilter   = ref('all')
const sortKey      = ref('health_score')
const sortAsc      = ref(true)

const riskFilters = [
  { val:'churn_risk',    label:'Churn Risk' },
  { val:'payment_issue', label:'Payment Issue' },
  { val:'at_risk',       label:'At Risk' },
  { val:'healthy',       label:'Healthy' },
]
const riskCount  = (val) => tenants.value.filter(t => t.risk === val).length
const alertCount = computed(() => alerts.value.filter(a => a.severity === 'critical').length)

const filteredTenants = computed(() => {
  let ts = [...tenants.value]
  if (riskFilter.value !== 'all') ts = ts.filter(t => t.risk === riskFilter.value)
  if (healthSearch.value) {
    const q = healthSearch.value.toLowerCase()
    ts = ts.filter(t => t.company.toLowerCase().includes(q) || t.email.toLowerCase().includes(q))
  }
  return ts.sort((a, b) => {
    const av = a[sortKey.value], bv = b[sortKey.value]
    return sortAsc.value ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
  })
})

function sortBy(key) {
  if (sortKey.value === key) sortAsc.value = !sortAsc.value
  else { sortKey.value = key; sortAsc.value = false }
}
function healthColor(s) {
  if (s >= 70) return '#22c55e'
  if (s >= 40) return '#f59e0b'
  return '#ef4444'
}

function planVariant(plan) {
  if (!plan) return 'secondary'
  const p = plan.toLowerCase()
  if (p.includes('enterprise')) return 'destructive'
  if (p.includes('pro')) return 'warning'
  if (p.includes('growth') || p.includes('starter')) return 'secondary'
  return 'outline'
}
function stripeVariant(status) {
  if (!status || status === 'none') return 'secondary'
  if (status === 'active' || status === 'trialing') return 'success'
  if (status === 'past_due') return 'warning'
  return 'destructive'
}
function riskVariant(risk) {
  if (risk === 'healthy') return 'success'
  if (risk === 'at_risk') return 'warning'
  if (risk === 'churn_risk' || risk === 'payment_issue') return 'destructive'
  return 'secondary'
}

async function impersonate(t) {
  if (!confirm(`Impersonate ${t.company}? A 15-min token will be issued and audit-logged.`)) return
  try {
    const res = await api.impersonateTenant(t.tenant_id)
    localStorage.setItem('cf_impersonate_return_token', localStorage.getItem('cf_access_token'))
    localStorage.setItem('cf_impersonate_return_user', localStorage.getItem('cf_user'))
    localStorage.setItem('cf_impersonating', 'true')
    localStorage.setItem('cf_access_token', res.access)
    window.location.href = '/portal/inbox'
  } catch(e) { alert('Impersonation failed: ' + e.message) }
}

async function extendTrial(t) {
  const days = prompt(`Extend trial for ${t.company} by how many days?`, '14')
  if (!days || isNaN(parseInt(days))) return
  try {
    await api.updateTenant(t.tenant_id, { extend_trial_days: parseInt(days) })
    await loadAll()
  } catch(e) { alert('Failed: ' + e.message) }
}

const planModal = ref({ open:false, tenant:null, selectedPlanId:null, remarks:'', saving:false })

function openPlanModal(t) {
  const cur = plans.value.find(p => p.name === t.plan)
  planModal.value = { open:true, tenant:t, selectedPlanId: cur?.id || null, remarks:'', saving:false }
}
async function savePlanChange() {
  if (!planModal.value.selectedPlanId) return
  planModal.value.saving = true
  try {
    await api.assignPlan(planModal.value.tenant.tenant_id, planModal.value.selectedPlanId, planModal.value.remarks)
    planModal.value.open = false
    await loadAll()
  } catch(e) { alert(e.message) } finally { planModal.value.saving = false }
}

const overrideModal = ref({ open:false, tenant:null, items:[], loading:false, saving:false, newFeature:'', newEnabled:true, newReason:'', newExpiry:'' })

const allFeatures = [
  {key:'allow_whatsapp',label:'WhatsApp'},{key:'allow_telegram',label:'Telegram'},
  {key:'allow_messenger',label:'Messenger'},{key:'allow_byok',label:'Custom AI (BYOK)'},
  {key:'allow_hubspot',label:'HubSpot CRM'},{key:'allow_slack',label:'Slack Notifications'},
  {key:'allow_webhooks',label:'Outbound Webhooks'},{key:'allow_god_view',label:'God View / Takeover'},
  {key:'allow_canned_responses',label:'Canned Responses'},{key:'allow_conversation_tags',label:'Conversation Tags'},
  {key:'allow_csv_export',label:'CSV Export'},{key:'allow_voice_input',label:'Voice Input'},
  {key:'allow_image_input',label:'Image Input'},{key:'remove_branding',label:'Remove Branding'},
  {key:'allow_custom_domain',label:'Custom Domain'},{key:'allow_api_access',label:'API Access'},
]

async function openOverridesModal(t) {
  overrideModal.value = { open:true, tenant:t, items:[], loading:true, saving:false, newFeature:'', newEnabled:true, newReason:'', newExpiry:'' }
  try { overrideModal.value.items = await api.getTenantFeatureOverrides(t.tenant_id) }
  catch {} finally { overrideModal.value.loading = false }
}
async function saveOverride() {
  if (!overrideModal.value.newFeature) return
  overrideModal.value.saving = true
  try {
    await api.createFeatureOverride(overrideModal.value.tenant.tenant_id, {
      feature_name: overrideModal.value.newFeature,
      enabled: overrideModal.value.newEnabled,
      reason: overrideModal.value.newReason,
      expires_at: overrideModal.value.newExpiry || null,
    })
    overrideModal.value.items = await api.getTenantFeatureOverrides(overrideModal.value.tenant.tenant_id)
    overrideModal.value.newFeature = ''
    overrideModal.value.newReason  = ''
    overrideModal.value.newExpiry  = ''
  } catch(e) { alert(e.message) } finally { overrideModal.value.saving = false }
}
async function deleteOverride(o) {
  if (!confirm('Remove this override?')) return
  await api.deleteFeatureOverride(overrideModal.value.tenant.tenant_id, o.id)
  overrideModal.value.items = overrideModal.value.items.filter(x => x.id !== o.id)
}

function alertActionLabel(action) {
  return { extend_trial:'Extend Trial', contact:'Contact', send_email:'Send Email', upgrade_plan:'Upgrade Plan' }[action] || action
}
function handleAlertAction(a) {
  const t = tenants.value.find(t => t.tenant_id === a.tenant_id)
  if (a.action === 'extend_trial' && t) extendTrial(t)
  else if (a.action === 'upgrade_plan' && t) openPlanModal(t)
  else alert(`Action: ${a.action} for ${a.label}`)
}

const annForm   = ref({ title:'', body:'', type:'info', target:'all', cta_label:'', cta_url:'' })
const annSaving = ref(false)
const annSent   = ref(false)

async function createAnnouncement() {
  if (!annForm.value.title || !annForm.value.body) return
  annSaving.value = true
  try {
    await api.createAnnouncement(annForm.value)
    annSent.value = true
    annForm.value = { title:'', body:'', type:'info', target:'all', cta_label:'', cta_url:'' }
    setTimeout(() => annSent.value = false, 3000)
  } catch(e) { alert(e.message) } finally { annSaving.value = false }
}

async function loadAudit() {
  try {
    const res = await api.getAuditLog({ page: auditPage.value, search: auditSearch.value, action: auditAction.value })
    auditLogs.value  = res.results || []
    auditTotal.value = res.total   || 0
  } catch {}
}

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-GB', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

async function loadAll() {
  loading.value = true
  try {
    const [rev, health, al, st, pl] = await Promise.all([
      api.getRevenue().catch(() => ({})),
      api.getTenantHealthBoard().catch(() => ({tenants:[]})),
      api.getLifecycleAlerts().catch(() => ({alerts:[]})),
      api.getStats().catch(() => ({})),
      api.getPlans().catch(() => []),
    ])
    revenue.value = { mrr:0, arr:0, new_mrr:0, churned_mrr:0, net_mrr_growth:0, arpu:0, active_tenants:0, total_tenants:0, past_due:0, trialing:0, plan_distribution:[], mrr_trend:[], ...rev }
    tenants.value = health.tenants || []
    alerts.value  = al.alerts     || []
    stats.value   = st            || {}
    plans.value   = Array.isArray(pl) ? pl : []
    await loadAudit()
  } finally { loading.value = false }
}

onMounted(loadAll)
</script>
