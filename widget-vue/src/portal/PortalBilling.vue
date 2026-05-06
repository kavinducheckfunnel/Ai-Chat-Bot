<template>
  <div class="flex flex-col gap-6 p-6 max-w-5xl">

    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Billing</h1>
      <p class="text-sm text-muted-foreground mt-1">Manage your subscription and usage.</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="n in 3" :key="n" class="animate-pulse rounded-xl border border-border p-5 space-y-3">
        <div class="h-4 w-48 rounded bg-muted"></div>
        <div class="h-3 w-32 rounded bg-muted"></div>
      </div>
    </div>

    <template v-else>

      <!-- Current plan banner -->
      <Card :class="sub.stripe_subscription_status === 'past_due' ? 'border-amber-300' : sub.stripe_subscription_status === 'canceled' ? 'border-red-300' : 'border-primary/20'">
        <CardContent class="pt-5 pb-5">
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <Badge :variant="sub.stripe_subscription_status === 'past_due' ? 'warning' : sub.stripe_subscription_status === 'canceled' ? 'destructive' : 'success'" class="mb-3">
                {{ statusLabel }}
              </Badge>
              <h2 class="text-xl font-bold text-foreground">{{ sub.plan?.name || 'No plan' }}</h2>
              <p v-if="sub.plan" class="text-sm text-muted-foreground mt-0.5">
                ${{ billingInterval === 'annual' ? annualMonthly(sub.plan) : sub.plan.price_monthly }}/mo
                <span v-if="billingInterval === 'annual'" class="ml-2 text-emerald-600 font-medium">billed annually · save 15%</span>
              </p>
              <p v-else class="text-sm text-muted-foreground">Free tier</p>
              <div v-if="sub.trial_ends_at" class="mt-2 flex items-center gap-1.5 text-xs text-violet-600">
                <Clock class="h-3.5 w-3.5" />
                Trial ends {{ formatDate(sub.trial_ends_at) }}
              </div>
            </div>
            <Button v-if="sub.stripe_subscription_id" variant="outline" @click="openPortal" :disabled="portalLoading">
              <Loader2 v-if="portalLoading" class="h-4 w-4 animate-spin" />
              Manage billing
            </Button>
          </div>
        </CardContent>
      </Card>

      <!-- Usage bars -->
      <div v-if="sub.usage && sub.plan">
        <h3 class="text-sm font-semibold mb-3">Usage this month</h3>
        <div class="grid grid-cols-2 gap-3">
          <Card v-for="res in usageResources" :key="res.key">
            <CardContent class="pt-4 pb-4">
              <div class="flex justify-between text-sm mb-2">
                <span class="text-muted-foreground">{{ res.label }}</span>
                <span class="font-semibold text-foreground">
                  {{ res.used.toLocaleString() }}{{ res.limit >= 0 ? ' / ' + res.limit.toLocaleString() : ' / ∞' }}
                </span>
              </div>
              <div class="h-1.5 rounded-full bg-muted overflow-hidden">
                <div class="h-full rounded-full transition-all" :style="{ width: res.pct + '%', background: res.pct > 90 ? '#ef4444' : res.pct > 75 ? '#f59e0b' : 'hsl(var(--primary))' }"></div>
              </div>
              <p v-if="res.pct > 80" class="text-[11px] mt-1.5" :class="res.pct >= 100 ? 'text-destructive' : 'text-amber-600'">
                {{ res.pct >= 100 ? 'Limit reached' : `${res.pct}% used — approaching limit` }}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <!-- Alerts -->
      <div v-if="sub.stripe_subscription_status === 'past_due'" class="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
        <AlertCircle class="h-4 w-4 shrink-0" />
        Your last payment failed. Please update your payment method to avoid interruptions.
        <button class="ml-auto font-medium underline" @click="openPortal">Update payment</button>
      </div>
      <div v-if="sub.stripe_subscription_status === 'canceled'" class="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        <AlertCircle class="h-4 w-4 shrink-0" />
        Your subscription has been canceled. Upgrade to restore full access.
      </div>

      <!-- Billing interval toggle + Plan grid -->
      <div>
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold">Choose a plan</h3>
          <div class="flex rounded-lg border border-border overflow-hidden">
            <button class="px-4 py-1.5 text-sm font-medium transition-colors" :class="billingInterval === 'monthly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'" @click="billingInterval = 'monthly'">Monthly</button>
            <button class="px-4 py-1.5 text-sm font-medium transition-colors" :class="billingInterval === 'annual' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'" @click="billingInterval = 'annual'">
              Annual <span class="ml-1 text-[10px] font-bold rounded bg-emerald-100 text-emerald-700 px-1">-15%</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <Card
            v-for="plan in plans" :key="plan.id"
            class="relative flex flex-col transition-all"
            :class="{ 'border-primary ring-1 ring-primary': isCurrentPlan(plan), 'border-primary/40 shadow-sm': plan.name === 'Growth' && !isCurrentPlan(plan) }"
          >
            <div v-if="plan.name === 'Growth'" class="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-[10px] font-bold text-primary-foreground">Most popular</div>
            <CardContent class="pt-5 pb-4 flex-1">
              <p class="text-sm font-bold text-foreground">{{ plan.name }}</p>
              <div class="mt-2 flex items-baseline gap-0.5">
                <span class="text-2xl font-bold text-foreground">${{ billingInterval === 'annual' ? annualMonthly(plan) : plan.price_monthly }}</span>
                <span class="text-sm text-muted-foreground">/mo</span>
              </div>
              <p v-if="billingInterval === 'annual' && plan.price_monthly > 0" class="text-xs text-muted-foreground mt-0.5">billed ${{ annualTotal(plan) }}/yr</p>
              <ul class="mt-4 space-y-1.5">
                <li class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />{{ formatLimit(plan.max_messages_per_month) }} AI messages/mo</li>
                <li class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />Up to {{ plan.max_clients }} chatbot{{ plan.max_clients !== 1 ? 's' : '' }}</li>
                <li class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />{{ formatLimit(plan.max_sessions_per_month) }} sessions/mo</li>
                <li v-if="plan.allow_whatsapp || plan.allow_messenger || plan.allow_telegram" class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />Social channels</li>
                <li v-if="plan.allow_hubspot" class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />HubSpot CRM sync</li>
                <li v-if="plan.allow_byok" class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />Bring your own AI (BYOK)</li>
                <li v-if="plan.allow_advanced_reports" class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />Advanced analytics</li>
                <li v-if="plan.remove_branding" class="flex items-center gap-2 text-xs text-muted-foreground"><Check class="h-3 w-3 text-emerald-500 shrink-0" />Remove branding</li>
              </ul>
            </CardContent>
            <div class="px-5 pb-5">
              <Button
                class="w-full"
                :variant="isCurrentPlan(plan) ? 'outline' : 'default'"
                :disabled="isCurrentPlan(plan) || !activePriceId(plan) || checkoutLoading === plan.id"
                @click="checkout(plan)"
              >
                <Loader2 v-if="checkoutLoading === plan.id" class="h-4 w-4 animate-spin" />
                <span v-else-if="isCurrentPlan(plan)">Current plan</span>
                <span v-else-if="!activePriceId(plan)">Coming soon</span>
                <span v-else-if="isDowngrade(plan)">Downgrade</span>
                <span v-else>Upgrade →</span>
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <p v-if="error" class="text-sm text-destructive">{{ error }}</p>

      <!-- FAQ -->
      <div>
        <h3 class="text-sm font-semibold mb-3">FAQ</h3>
        <div class="divide-y divide-border rounded-lg border border-border overflow-hidden">
          <div v-for="q in faqs" :key="q.q" class="bg-background">
            <button class="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-medium text-foreground hover:bg-muted/50" @click="q.open = !q.open">
              {{ q.q }}
              <ChevronDown class="h-4 w-4 text-muted-foreground transition-transform shrink-0" :class="{ 'rotate-180': q.open }" />
            </button>
            <div v-if="q.open" class="border-t border-border px-5 pb-4 pt-3 text-sm text-muted-foreground">{{ q.a }}</div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Loader2, Clock, AlertCircle, Check, ChevronDown } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'

const api = useAdminApi()
const loading = ref(true)
const portalLoading = ref(false)
const checkoutLoading = ref(null)
const error = ref('')
const sub = ref({})
const plans = ref([])
const billingInterval = ref('monthly')

function annualMonthly(plan) { return (parseFloat(plan.price_monthly) * 0.85).toFixed(0) }
function annualTotal(plan) { return (parseFloat(plan.price_monthly) * 0.85 * 12).toFixed(0) }
function activePriceId(plan) { return billingInterval.value === 'annual' ? plan.stripe_price_id_annual : plan.stripe_price_id }
function isCurrentPlan(plan) { return sub.value.plan?.id === plan.id }
function isDowngrade(plan) { return sub.value.plan && parseFloat(plan.price_monthly) < parseFloat(sub.value.plan.price_monthly) }
function formatLimit(n) { return n < 0 ? 'Unlimited' : n.toLocaleString() }
function formatDate(iso) { return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) }

const statusLabel = computed(() => {
  if (sub.value.trial_ends_at && new Date(sub.value.trial_ends_at) > new Date()) return 'Trial'
  const s = sub.value.stripe_subscription_status
  if (!s || s === 'active') return 'Active'
  if (s === 'past_due') return 'Past due'
  if (s === 'canceled') return 'Canceled'
  if (s === 'trialing') return 'Trial'
  return s
})

const usageResources = computed(() => {
  const u = sub.value.usage || {}
  function pct(used, limit) { if (limit < 0 || !limit) return 0; return Math.min(Math.round((used / limit) * 100), 100) }
  return [
    { key: 'messages', label: 'AI Messages',    used: u.messages?.used || 0, limit: u.messages?.limit ?? -1, pct: pct(u.messages?.used || 0, u.messages?.limit ?? -1) },
    { key: 'sessions', label: 'Chat Sessions',  used: u.sessions?.used || 0, limit: u.sessions?.limit ?? -1, pct: pct(u.sessions?.used || 0, u.sessions?.limit ?? -1) },
    { key: 'images',   label: 'Image Uploads',  used: u.images?.used || 0,   limit: u.images?.limit ?? -1,   pct: pct(u.images?.used || 0,   u.images?.limit ?? -1) },
    { key: 'voice',    label: 'Voice Commands',  used: u.voice?.used || 0,    limit: u.voice?.limit ?? -1,    pct: pct(u.voice?.used || 0,    u.voice?.limit ?? -1) },
  ].filter(r => r.limit !== 0)
})

const faqs = ref([
  { q: 'Can I cancel anytime?', a: 'Yes — cancel from the Manage billing portal. Your access continues until the end of the billing period.', open: false },
  { q: 'What happens if I exceed my message limit?', a: 'The chatbot will display a polite notice that it has reached its limit for the month. Upgrade your plan to restore access immediately.', open: false },
  { q: 'What is the annual plan discount?', a: 'Annual plans are billed upfront at 15% off the monthly rate. You can switch between monthly and annual at any time.', open: false },
  { q: 'Can I change plans mid-month?', a: 'Yes. Upgrades are pro-rated and take effect immediately. Downgrades apply at the start of the next billing cycle.', open: false },
  { q: 'Is my payment information secure?', a: 'All payments are handled by Stripe — we never store your card details.', open: false },
])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [subData, planData] = await Promise.all([api.getSubscription(), api.getPublicPlans()])
    sub.value = subData
    plans.value = planData
    if (subData.billing_interval) billingInterval.value = subData.billing_interval
  } catch (e) { error.value = e.message || 'Failed to load billing info.' } finally { loading.value = false }
}

async function checkout(plan) {
  error.value = ''
  checkoutLoading.value = plan.id
  const priceId = activePriceId(plan)
  if (!priceId) { error.value = 'This plan is not available yet.'; checkoutLoading.value = null; return }
  try {
    const { url } = await api.createCheckoutSession(plan.id)
    window.location.href = url
  } catch (e) { error.value = e.message || 'Could not start checkout. Please try again.'; checkoutLoading.value = null }
}

async function openPortal() {
  error.value = ''
  portalLoading.value = true
  try {
    const { url } = await api.createPortalSession()
    window.location.href = url
  } catch (e) { error.value = e.message || 'Could not open billing portal.' } finally { portalLoading.value = false }
}

onMounted(load)
</script>
