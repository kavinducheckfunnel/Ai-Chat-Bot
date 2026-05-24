<template>
  <div class="billing-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Billing</h1>
        <p class="page-sub">Manage your subscription and usage.</p>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="skeleton-wrap">
      <div class="sk-card" v-for="n in 3" :key="n"><div class="sk-line w60"></div><div class="sk-line w40"></div></div>
    </div>

    <template v-else>

      <!-- ── Current plan banner ──────────────────────────────────────────── -->
      <div class="current-plan-card" :class="statusClass">
        <div class="cp-left">
          <div class="cp-badge" :class="statusClass">{{ statusLabel }}</div>
          <h2 class="cp-plan-name">{{ sub.plan?.name || 'No plan' }}</h2>
          <p class="cp-price" v-if="sub.plan">
            ${{ billingInterval === 'annual' ? annualMonthly(sub.plan) : sub.plan.price_monthly }}<span>/mo</span>
            <span v-if="billingInterval === 'annual'" class="annual-tag">billed annually · save 15%</span>
          </p>
          <p class="cp-price" v-else>Free</p>

          <!-- Trial banner -->
          <div v-if="sub.trial_ends_at" class="trial-notice">
            <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#a78bfa" stroke-width="2"/><path d="M12 8v4l2.5 2.5" stroke="#a78bfa" stroke-width="2" stroke-linecap="round"/></svg>
            Trial ends {{ formatDate(sub.trial_ends_at) }}
          </div>
        </div>
        <div class="cp-right">
          <button v-if="sub.stripe_subscription_id" class="btn-portal" @click="openPortal" :disabled="portalLoading">
            <span v-if="portalLoading" class="spinner"></span>
            <span v-else>Manage billing</span>
          </button>
        </div>
      </div>

      <!-- ── Usage bars ──────────────────────────────────────────────────── -->
      <div class="usage-section" v-if="sub.usage && sub.plan">
        <h3 class="section-heading">Usage this month</h3>
        <div class="usage-grid">
          <div class="usage-card" v-for="res in usageResources" :key="res.key">
            <div class="usage-label">
              <span>{{ res.label }}</span>
              <span class="usage-nums">
                {{ res.used.toLocaleString() }}
                <span v-if="res.limit >= 0"> / {{ res.limit.toLocaleString() }}</span>
                <span v-else> / ∞</span>
              </span>
            </div>
            <div class="usage-bar">
              <div
                class="usage-fill"
                :style="{ width: res.pct + '%', background: res.pct > 90 ? '#ef4444' : res.pct > 75 ? '#f59e0b' : '#6366f1' }"
              ></div>
            </div>
            <span v-if="res.pct > 80" class="usage-warn">
              {{ res.pct >= 100 ? 'Limit reached' : `${res.pct}% used — approaching limit` }}
            </span>
          </div>
        </div>
      </div>

      <!-- ── F7: Top up credits (one-time add-on purchases) ─────────── -->
      <div class="addon-section" v-if="addonOptions && sub.plan">
        <h3 class="section-heading">Need more this month? Top up credits</h3>
        <p class="section-sub">
          Run out of monthly quota before your next renewal? Buy one-time credits at the rates below.
          Credits stack on top of your plan and never expire.
        </p>
        <div class="addon-grid">
          <div class="addon-card" v-for="kind in addonKinds" :key="kind.key">
            <div class="addon-card-header">
              <span class="addon-icon">{{ kind.icon }}</span>
              <span class="addon-label">{{ kind.label }}</span>
            </div>
            <div class="addon-price-line">${{ addonOptions.prices[kind.key] }}<span>/{{ kind.unit }}</span></div>
            <div class="addon-bundles">
              <button
                v-for="bundle in addonOptions.bundles[kind.key]"
                :key="bundle"
                class="addon-bundle-btn"
                :disabled="addonLoading === `${kind.key}_${bundle}`"
                @click="buyAddOn(kind.key, bundle)"
              >
                <span v-if="addonLoading === `${kind.key}_${bundle}`" class="spinner"></span>
                <span v-else>+{{ bundle.toLocaleString() }} · ${{ addonTotal(kind.key, bundle) }}</span>
              </button>
            </div>
          </div>
        </div>
        <p v-if="addonError" class="addon-error">{{ addonError }}</p>
      </div>

      <!-- ── Invoices section ────────────────────────────────────────── -->
      <div class="invoices-section">
        <div class="invoices-header">
          <div>
            <h3 class="section-heading" style="margin:0">Invoices</h3>
            <p class="section-sub-mini">Monthly invoices are emailed automatically on the 1st. Download anytime as PDF (Cmd/Ctrl + P → Save as PDF).</p>
          </div>
          <button class="btn-test-invoice" @click="sendTestInvoice" :disabled="testInvoiceSending">
            <span v-if="testInvoiceSending" class="spinner"></span>
            <span v-else>📧 Send me a test invoice</span>
          </button>
        </div>
        <p v-if="testInvoiceStatus" :class="['test-invoice-msg', testInvoiceOk ? 'ok' : 'err']">{{ testInvoiceStatus }}</p>
        <div v-if="!invoices.length && !invoicesLoading" class="invoices-empty">
          No invoices yet. Your first one will be emailed and shown here on the 1st of the next month.
        </div>
        <div v-else-if="invoicesLoading" class="invoices-empty">Loading invoices…</div>
        <div v-else class="invoice-list">
          <div v-for="inv in invoices" :key="inv.id" class="invoice-row">
            <div class="invoice-left">
              <div class="invoice-number">{{ inv.invoice_number }}</div>
              <div class="invoice-period">{{ formatInvoicePeriod(inv.period_start) }}</div>
            </div>
            <div class="invoice-center">
              <span class="invoice-status" :class="`inv-${inv.status}`">{{ inv.status }}</span>
              <span class="invoice-total">${{ inv.total_usd }} USD</span>
            </div>
            <a class="btn-invoice-view" :href="invoiceUrl(inv)" target="_blank" rel="noopener">
              View / Download →
            </a>
          </div>
        </div>
      </div>

      <!-- Past due / canceled warning -->
      <div v-if="sub.stripe_subscription_status === 'past_due'" class="alert-banner warn">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#f59e0b" stroke-width="2"/><line x1="12" y1="8" x2="12" y2="12" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="16" x2="12.01" y2="16" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/></svg>
        Your last payment failed. Please update your payment method to avoid interruptions.
        <button class="btn-link" @click="openPortal">Update payment</button>
      </div>
      <div v-if="sub.stripe_subscription_status === 'canceled'" class="alert-banner danger">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="2"/><path d="M15 9l-6 6M9 9l6 6" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/></svg>
        Your subscription has been canceled. Upgrade to restore full access.
      </div>

      <!-- ── Billing interval toggle ─────────────────────────────────────── -->
      <div class="interval-toggle-wrap">
        <h3 class="section-heading" style="margin:0">Choose a plan</h3>
        <div class="interval-toggle">
          <button :class="{ active: billingInterval === 'monthly' }" @click="billingInterval = 'monthly'">Monthly</button>
          <button :class="{ active: billingInterval === 'annual' }" @click="billingInterval = 'annual'">
            Annual <span class="save-badge">Save 15%</span>
          </button>
        </div>
      </div>

      <!-- ── Plan cards ──────────────────────────────────────────────────── -->
      <div class="plans-grid">
        <div
          v-for="plan in plans"
          :key="plan.id"
          class="plan-card"
          :class="{ current: isCurrentPlan(plan), popular: plan.name === 'Growth' }"
        >
          <div class="plan-popular-badge" v-if="plan.name === 'Growth'">Most popular</div>
          <div class="plan-header">
            <span class="plan-name">{{ plan.name }}</span>
            <div class="plan-price" v-if="plan.price_monthly != null && plan.price_monthly >= 0">
              <span class="plan-amount">${{ billingInterval === 'annual' ? annualMonthly(plan) : formatPrice(plan.price_monthly) }}</span>
              <span class="plan-period">/mo</span>
            </div>
            <div class="plan-price" v-else>
              <span class="plan-amount plan-amount-custom">Custom</span>
            </div>
            <span v-if="billingInterval === 'annual' && plan.price_monthly > 0" class="plan-annual-note">billed ${{ annualTotal(plan) }}/yr</span>
          </div>
          <ul class="plan-features">
            <li>
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              {{ formatLimit(plan.max_messages_per_month) }} AI messages/mo
            </li>
            <li>
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Up to {{ plan.max_clients }} chatbot{{ plan.max_clients !== 1 ? 's' : '' }}
            </li>
            <li>
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              {{ formatLimit(plan.max_sessions_per_month) }} sessions/mo
            </li>
            <li v-if="plan.allow_whatsapp || plan.allow_messenger || plan.allow_telegram">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Social channels (WhatsApp / Messenger / Telegram)
            </li>
            <li v-if="plan.allow_hubspot">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              HubSpot CRM sync
            </li>
            <li v-if="plan.allow_byok">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Bring your own AI key (BYOK)
            </li>
            <li v-if="plan.allow_advanced_reports">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Advanced analytics
            </li>
            <li v-if="plan.remove_branding">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Remove branding
            </li>
          </ul>
          <button
            class="plan-btn"
            :class="{
              'plan-btn-current': isCurrentPlan(plan),
              'plan-btn-upgrade': !isCurrentPlan(plan) && activePriceId(plan),
              'plan-btn-contact': !isCurrentPlan(plan) && !activePriceId(plan),
            }"
            :disabled="isCurrentPlan(plan) || checkoutLoading === plan.id"
            @click="activePriceId(plan) ? checkout(plan) : contactUs()"
          >
            <span v-if="checkoutLoading === plan.id" class="spinner"></span>
            <span v-else-if="isCurrentPlan(plan)">Current plan</span>
            <span v-else-if="!activePriceId(plan)">Contact us</span>
            <span v-else-if="isDowngrade(plan)">Downgrade</span>
            <span v-else>Upgrade</span>
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="error-msg">{{ error }}</div>

      <!-- ── FAQ ─────────────────────────────────────────────────────────── -->
      <div class="faq-section">
        <h3 class="section-heading">FAQ</h3>
        <div class="faq-list">
          <div class="faq-item" v-for="q in faqs" :key="q.q" @click="q.open = !q.open">
            <div class="faq-q">
              {{ q.q }}
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" :style="{ transform: q.open ? 'rotate(180deg)' : '', transition: '.2s' }"><path d="M6 9l6 6 6-6" stroke="#64748b" stroke-width="2" stroke-linecap="round"/></svg>
            </div>
            <div class="faq-a" v-if="q.open">{{ q.a }}</div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()

const loading = ref(true)
const portalLoading = ref(false)
const checkoutLoading = ref(null)
const error = ref('')
const sub = ref({})
const plans = ref([])
const billingInterval = ref('monthly')

// F7 — Add-on top-ups
const addonOptions = ref(null)   // { prices: {message,image,voice,video}, bundles: {...} }
const addonLoading = ref('')     // `${kind}_${qty}` while a purchase is in flight
const addonError = ref('')
const addonKinds = [
  { key: 'message', label: 'AI messages',  icon: '💬', unit: 'msg' },
  { key: 'image',   label: 'Image uploads', icon: '🖼️', unit: 'image' },
  { key: 'voice',   label: 'Voice commands', icon: '🎤', unit: 'voice' },
  { key: 'video',   label: 'Video uploads', icon: '🎬', unit: 'video' },
]

function addonTotal(kind, qty) {
  const price = parseFloat(addonOptions.value?.prices?.[kind] || 0)
  const total = price * qty
  return total >= 10 ? total.toFixed(0) : total.toFixed(2)
}

async function loadAddOns() {
  try {
    addonOptions.value = await api.getAddOnOptions()
  } catch {
    addonOptions.value = null
  }
}

async function buyAddOn(kind, quantity) {
  addonError.value = ''
  addonLoading.value = `${kind}_${quantity}`
  try {
    const { url } = await api.purchaseAddOn(kind, quantity)
    window.location.href = url
  } catch (e) {
    addonError.value = e.message || 'Could not start checkout.'
    addonLoading.value = ''
  }
}

// ── Invoices section ────────────────────────────────────────────────────────
const invoices = ref([])
const invoicesLoading = ref(false)
const testInvoiceSending = ref(false)
const testInvoiceStatus = ref('')
const testInvoiceOk = ref(false)

async function loadInvoices() {
  invoicesLoading.value = true
  try {
    const list = await api.listInvoices()
    invoices.value = Array.isArray(list) ? list : []
  } catch {
    invoices.value = []
  } finally {
    invoicesLoading.value = false
  }
}

function invoiceUrl(inv) {
  // Backend returns a relative download_url like /api/admin/billing/invoices/<uuid>/html/
  // To make this work in a new tab with auth, we'd need to attach the token; for now,
  // open the same path via the API base — the user's session cookie carries auth.
  const base = (typeof window !== 'undefined' && window.location.origin) || ''
  return base + inv.download_url
}

function formatInvoicePeriod(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  } catch { return iso }
}

async function sendTestInvoice() {
  testInvoiceStatus.value = ''
  testInvoiceSending.value = true
  try {
    const res = await api.sendTestInvoice()
    testInvoiceOk.value = true
    testInvoiceStatus.value = `Test invoice sent to ${res.sent_to}. Check your inbox (and spam folder).`
    await loadInvoices()  // refresh list — the generated invoice now appears
  } catch (e) {
    testInvoiceOk.value = false
    testInvoiceStatus.value = e.message || 'Could not send test invoice.'
  } finally {
    testInvoiceSending.value = false
  }
}

// ── helpers ──────────────────────────────────────────────────────────────────

function annualMonthly(plan) {
  return (parseFloat(plan.price_monthly) * 0.85).toFixed(0)
}
function annualTotal(plan) {
  return (parseFloat(plan.price_monthly) * 0.85 * 12).toFixed(0)
}
function activePriceId(plan) {
  return billingInterval.value === 'annual'
    ? plan.stripe_price_id_annual
    : plan.stripe_price_id
}
function isCurrentPlan(plan) {
  return sub.value.plan?.id === plan.id
}
function isDowngrade(plan) {
  return sub.value.plan && parseFloat(plan.price_monthly) < parseFloat(sub.value.plan.price_monthly)
}
function formatLimit(n) {
  if (n < 0) return 'Unlimited'
  return n.toLocaleString()
}
function formatPrice(p) {
  const n = parseFloat(p)
  if (isNaN(n)) return '—'
  return n === 0 ? '0' : n.toFixed(n % 1 === 0 ? 0 : 2)
}
function contactUs() {
  window.open('mailto:support@checkfunnels.com?subject=Plan inquiry', '_blank')
}
function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// ── computed ─────────────────────────────────────────────────────────────────

const statusLabel = computed(() => {
  if (sub.value.trial_ends_at && new Date(sub.value.trial_ends_at) > new Date()) return 'Trial'
  const s = sub.value.stripe_subscription_status
  if (!s || s === 'active') return 'Active'
  if (s === 'past_due') return 'Past due'
  if (s === 'canceled') return 'Canceled'
  if (s === 'trialing') return 'Trial'
  return s
})

const statusClass = computed(() => {
  const s = sub.value.stripe_subscription_status
  if (s === 'past_due') return 'warn'
  if (s === 'canceled') return 'danger'
  return 'ok'
})

const usageResources = computed(() => {
  const u = sub.value.usage || {}

  function pct(used, limit) {
    if (limit < 0) return 0
    if (!limit) return 0
    return Math.min(Math.round((used / limit) * 100), 100)
  }

  return [
    { key: 'messages', label: 'AI Messages', used: u.messages?.used || 0, limit: u.messages?.limit ?? -1, pct: pct(u.messages?.used || 0, u.messages?.limit ?? -1) },
    { key: 'sessions', label: 'Chat Sessions', used: u.sessions?.used || 0, limit: u.sessions?.limit ?? -1, pct: pct(u.sessions?.used || 0, u.sessions?.limit ?? -1) },
    { key: 'images',   label: 'Image Uploads', used: u.images?.used || 0,   limit: u.images?.limit ?? -1,   pct: pct(u.images?.used || 0,   u.images?.limit ?? -1) },
    { key: 'voice',    label: 'Voice Commands', used: u.voice?.used || 0,    limit: u.voice?.limit ?? -1,    pct: pct(u.voice?.used || 0,    u.voice?.limit ?? -1) },
  ].filter(r => r.limit !== 0) // hide resources not in plan
})

const faqs = ref([
  { q: 'Can I cancel anytime?', a: 'Yes — cancel from the Manage billing portal. Your access continues until the end of the billing period.', open: false },
  { q: 'What happens if I exceed my message limit?', a: 'The chatbot will display a polite notice that it has reached its limit for the month. Upgrade your plan to restore access immediately.', open: false },
  { q: 'What is the annual plan discount?', a: 'Annual plans are billed upfront at 15% off the monthly rate. You can switch between monthly and annual at any time.', open: false },
  { q: 'Can I change plans mid-month?', a: 'Yes. Upgrades are pro-rated and take effect immediately. Downgrades apply at the start of the next billing cycle.', open: false },
  { q: 'Is my payment information secure?', a: 'All payments are handled by Stripe — we never store your card details.', open: false },
])

// ── data loading ─────────────────────────────────────────────────────────────

async function load() {
  // Only show the full skeleton on the very first load; subsequent refreshes
  // (navigation back, focus regain) should update silently in the background.
  const isInitial = !sub.value || !sub.value.plan
  if (isInitial) loading.value = true
  error.value = ''
  try {
    const [subData, planData] = await Promise.all([
      api.getSubscription(),
      api.getPublicPlans(),
    ])
    // Defensive: only overwrite sub.value if the API returned a real object.
    // A network blip or 401-then-refresh-failure can return undefined; in
    // that case we keep showing the last-known-good plan instead of
    // collapsing to "No plan / Free".
    if (subData && typeof subData === 'object') {
      sub.value = subData
      if (subData.billing_interval) billingInterval.value = subData.billing_interval
    }
    if (Array.isArray(planData)) plans.value = planData
    // Fetch add-on prices/bundles + invoices in the background (don't block main load)
    loadAddOns()
    loadInvoices()
  } catch (e) {
    error.value = e.message || 'Failed to load billing info.'
  } finally {
    loading.value = false
  }
}

const route = useRoute()

// Refetch when the user navigates back to the billing route. Even though
// the router is not configured with <keep-alive>, this guards against
// future routing changes and the lifecycle is idempotent.
onActivated(load)

// Refetch when the tab regains focus (covers the case where the user
// completes Stripe checkout in another tab and comes back).
function onVisibilityChange() {
  if (document.visibilityState === 'visible') load()
}

onMounted(() => {
  load()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

watch(() => route.fullPath, (newPath) => {
  if (newPath.startsWith('/portal/billing')) load()
})

async function checkout(plan) {
  error.value = ''
  checkoutLoading.value = plan.id
  const priceId = activePriceId(plan)
  if (!priceId) { error.value = 'This plan is not available yet.'; checkoutLoading.value = null; return }
  try {
    const { url } = await api.createCheckoutSession(plan.id)
    window.location.href = url
  } catch (e) {
    error.value = e.message || 'Could not start checkout. Please try again.'
    checkoutLoading.value = null
  }
}

async function openPortal() {
  error.value = ''
  portalLoading.value = true
  try {
    const { url } = await api.createPortalSession()
    window.location.href = url
  } catch (e) {
    error.value = e.message || 'Could not open billing portal.'
  } finally {
    portalLoading.value = false
  }
}

</script>

<style scoped>
.billing-page {
  padding: 32px;
  max-width: 1100px;
}

.page-header { margin-bottom: 28px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 4px; }
.page-sub { font-size: 13px; color: var(--cf-text-muted); margin: 0; }

/* Skeleton */
.skeleton-wrap { display: flex; flex-direction: column; gap: 12px; }
.sk-card { background: var(--cf-bg-surface-raised); border: 1px solid var(--cf-border-subtle); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
.sk-line { height: 12px; border-radius: 6px; background: var(--cf-bg-input); animation: pulse 1.5s ease-in-out infinite; }
.sk-line.w60 { width: 60%; }
.sk-line.w40 { width: 40%; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Current plan card */
.current-plan-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: var(--cf-bg-surface-raised);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 16px;
  padding: 24px 28px;
  margin-bottom: 16px;
  gap: 20px;
}
.current-plan-card.warn { border-color: rgba(245,158,11,0.3); }
.current-plan-card.danger { border-color: rgba(239,68,68,0.3); }

.cp-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 6px;
  margin-bottom: 8px;
  background: rgba(34,197,94,0.1);
  color: #22c55e;
  border: 1px solid rgba(34,197,94,0.2);
}
.cp-badge.warn { background: rgba(245,158,11,0.1); color: #f59e0b; border-color: rgba(245,158,11,0.2); }
.cp-badge.danger { background: rgba(239,68,68,0.1); color: #ef4444; border-color: rgba(239,68,68,0.2); }

.cp-plan-name { font-size: 20px; font-weight: 700; color: var(--cf-text-primary); margin: 0 0 4px; }
.cp-price { font-size: 28px; font-weight: 800; color: var(--cf-text-primary); margin: 0 0 6px; display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.cp-price span:first-child { font-size: 14px; font-weight: 400; color: var(--cf-text-muted); }
.annual-tag { font-size: 11px; font-weight: 600; color: #a78bfa; background: rgba(167,139,250,0.1); border: 1px solid rgba(167,139,250,0.2); border-radius: 6px; padding: 2px 8px; }

.trial-notice {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #a78bfa;
  background: rgba(167,139,250,0.08);
  border: 1px solid rgba(167,139,250,0.2);
  border-radius: 8px;
  padding: 5px 10px;
  margin-top: 8px;
  width: fit-content;
}

/* Usage section */
.usage-section { margin-bottom: 20px; }
.usage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.usage-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.usage-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: var(--cf-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.usage-nums { color: var(--cf-text-primary); font-weight: 700; text-transform: none; letter-spacing: 0; }
.usage-bar { height: 6px; background: var(--cf-bg-ghost); border-radius: 6px; overflow: hidden; }
.usage-fill { height: 100%; border-radius: 6px; transition: width 0.4s; }
.usage-warn { font-size: 11px; color: #f59e0b; }

.btn-portal {
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc;
  border-radius: 10px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-portal:hover:not(:disabled) { background: rgba(99,102,241,0.2); }
.btn-portal:disabled { opacity: 0.5; cursor: not-allowed; }

/* Invoices section */
.invoices-section {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  padding: 20px 22px;
  margin: 16px 0 20px;
}
.invoices-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.section-sub-mini {
  font-size: 12px;
  color: var(--cf-text-muted);
  margin: 4px 0 0;
  line-height: 1.5;
  max-width: 560px;
}
.btn-test-invoice {
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-test-invoice:hover:not(:disabled) { background: rgba(99,102,241,0.18); }
.btn-test-invoice:disabled { opacity: 0.5; cursor: not-allowed; }
.test-invoice-msg {
  font-size: 12px;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 0 0 12px;
}
.test-invoice-msg.ok { background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.25); color: #4ade80; }
.test-invoice-msg.err { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
.invoices-empty {
  font-size: 13px;
  color: var(--cf-text-muted);
  text-align: center;
  padding: 20px 12px;
  border: 1px dashed var(--cf-border-subtle);
  border-radius: 10px;
}
.invoice-list { display: flex; flex-direction: column; gap: 8px; }
.invoice-row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--cf-bg-input);
  border-radius: 10px;
  padding: 12px 14px;
}
.invoice-left { flex: 1; min-width: 0; }
.invoice-number { font-family: ui-monospace, monospace; font-size: 12px; color: var(--cf-text-secondary); }
.invoice-period { font-size: 14px; font-weight: 600; color: var(--cf-text-primary); margin-top: 2px; }
.invoice-center { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.invoice-status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--cf-bg-ghost);
  color: var(--cf-text-muted);
  border: 1px solid var(--cf-border-subtle);
}
.invoice-status.inv-sent { background: rgba(34,197,94,0.12); color: #22c55e; border-color: rgba(34,197,94,0.25); }
.invoice-status.inv-issued { background: rgba(99,102,241,0.12); color: #a5b4fc; border-color: rgba(99,102,241,0.3); }
.invoice-status.inv-paid { background: rgba(34,197,94,0.18); color: #4ade80; border-color: rgba(34,197,94,0.4); }
.invoice-status.inv-draft { background: rgba(245,158,11,0.12); color: #fbbf24; border-color: rgba(245,158,11,0.25); }
.invoice-status.inv-void { background: rgba(239,68,68,0.1); color: #fca5a5; border-color: rgba(239,68,68,0.25); }
.invoice-total { font-size: 14px; font-weight: 700; color: var(--cf-text-primary); font-variant-numeric: tabular-nums; }
.btn-invoice-view {
  font-size: 12px;
  font-weight: 600;
  color: #a5b4fc;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.25);
  white-space: nowrap;
}
.btn-invoice-view:hover { background: rgba(99,102,241,0.18); }

/* Alert banners */
.alert-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 13px;
  margin-bottom: 12px;
}
.alert-banner.warn { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2); color: #fcd34d; }
.alert-banner.danger { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); color: #fca5a5; }
.btn-link { background: none; border: none; text-decoration: underline; cursor: pointer; color: inherit; font-size: 13px; margin-left: auto; }

/* F7 — Add-on top-ups */
.addon-section {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 14px;
  padding: 20px 22px;
  margin: 16px 0 20px;
}
.section-heading + .section-sub { margin-top: -8px; }
.addon-section .section-sub {
  font-size: 13px;
  color: var(--cf-text-muted);
  line-height: 1.5;
  margin: 6px 0 14px;
}
.addon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.addon-card {
  background: var(--cf-bg-input);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.addon-card-header { display: flex; align-items: center; gap: 8px; }
.addon-icon { font-size: 20px; }
.addon-label { font-size: 13px; font-weight: 600; color: var(--cf-text-primary); }
.addon-price-line { font-size: 18px; font-weight: 700; color: var(--cf-text-primary); }
.addon-price-line span { font-size: 11px; font-weight: 500; color: var(--cf-text-muted); margin-left: 3px; }
.addon-bundles { display: flex; flex-direction: column; gap: 6px; }
.addon-bundle-btn {
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.25);
  color: var(--cf-text-primary);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.addon-bundle-btn:hover:not(:disabled) { background: rgba(99,102,241,0.15); }
.addon-bundle-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.addon-error {
  margin-top: 10px;
  font-size: 12px;
  color: #fca5a5;
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 8px;
  padding: 8px 12px;
}

/* Billing interval toggle */
.interval-toggle-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 24px 0 16px;
}
.interval-toggle {
  display: flex;
  background: var(--cf-bg-surface);
  border: 1px solid var(--cf-border-default);
  border-radius: 10px;
  padding: 3px;
  gap: 3px;
}
.interval-toggle button {
  background: none;
  border: none;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--cf-text-muted);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.interval-toggle button.active { background: rgba(99,102,241,0.2); color: #a5b4fc; }
.save-badge {
  font-size: 10px;
  font-weight: 700;
  background: rgba(167,139,250,0.15);
  color: #a78bfa;
  border-radius: 5px;
  padding: 1px 6px;
}

/* Plan grid */
.section-heading { font-size: 14px; font-weight: 600; color: var(--cf-text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 16px; }

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}

.plan-card {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  transition: border-color 0.2s;
}
.plan-card.popular {
  border-color: rgba(99,102,241,0.4);
  background: linear-gradient(135deg, var(--cf-popular-card-bg-start), var(--cf-popular-card-bg-end));
}
.plan-card.current { border-color: rgba(34,197,94,0.3); }

.plan-popular-badge {
  position: absolute;
  top: -11px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 12px;
  border-radius: 20px;
  white-space: nowrap;
}

.plan-header { display: flex; flex-direction: column; gap: 4px; }
.plan-name { font-size: 13px; font-weight: 600; color: var(--cf-text-secondary); text-transform: uppercase; letter-spacing: 0.06em; }
.plan-price { display: flex; align-items: baseline; gap: 2px; }
.plan-amount { font-size: 32px; font-weight: 800; color: var(--cf-text-primary); }
.plan-period { font-size: 13px; color: var(--cf-text-muted); }
.plan-annual-note { font-size: 11px; color: var(--cf-text-muted); margin-top: 2px; }

.plan-features { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.plan-features li { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: var(--cf-text-secondary); line-height: 1.4; }
.plan-features li svg { flex-shrink: 0; margin-top: 2px; }

.plan-btn {
  width: 100%;
  border-radius: 10px;
  padding: 11px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: auto;
}
.plan-btn-current { background: rgba(34,197,94,0.1); color: #22c55e; border: 1px solid rgba(34,197,94,0.2); cursor: default; }
.plan-btn-upgrade { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; }
.plan-btn-contact { background: rgba(99,102,241,0.08); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.2); }
.plan-btn-contact:hover { background: rgba(99,102,241,0.15); }
.plan-btn:disabled:not(.plan-btn-current) { opacity: 0.4; cursor: not-allowed; }
.plan-btn-upgrade:hover:not(:disabled) { opacity: 0.9; }
.plan-amount-custom { font-size: 22px; color: var(--cf-text-muted); }

/* Spinner */
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.error-msg { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 13px; margin-bottom: 16px; }

/* FAQ */
.faq-section { margin-top: 8px; }
.faq-list { display: flex; flex-direction: column; gap: 1px; }
.faq-item {
  background: var(--cf-bg-surface-raised);
  border: 1px solid var(--cf-border-subtle);
  border-radius: 10px;
  padding: 14px 18px;
  cursor: pointer;
  margin-bottom: 6px;
}
.faq-q { display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: var(--cf-text-primary); font-weight: 500; }
.faq-a { font-size: 13px; color: var(--cf-text-muted); margin-top: 10px; line-height: 1.6; }

@media (max-width: 768px) {
  .page-header { flex-direction: column; gap: 12px; align-items: flex-start; }
  .current-plan-card { flex-direction: column; }
}
</style>
