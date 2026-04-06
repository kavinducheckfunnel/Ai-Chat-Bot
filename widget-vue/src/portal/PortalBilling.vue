<template>
  <div class="billing-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Billing</h1>
        <p class="page-sub">Manage your subscription and plan.</p>
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
            ${{ sub.plan.price_monthly }}<span>/mo</span>
          </p>
          <p class="cp-price" v-else>Free</p>
          <div class="cp-meta">
            <span>{{ sub.sessions_this_month || 0 }} / {{ sub.plan?.max_sessions_per_month || '—' }} sessions this month</span>
          </div>
          <div class="usage-bar-wrap" v-if="sub.plan">
            <div class="usage-bar">
              <div class="usage-fill" :style="{ width: usagePct + '%', background: usagePct > 80 ? '#ef4444' : '#6366f1' }"></div>
            </div>
            <span class="usage-pct">{{ usagePct }}%</span>
          </div>
        </div>
        <div class="cp-right">
          <button v-if="sub.stripe_subscription_id" class="btn-portal" @click="openPortal" :disabled="portalLoading">
            <span v-if="portalLoading" class="spinner"></span>
            <span v-else>Manage billing</span>
          </button>
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

      <!-- ── Plan picker ──────────────────────────────────────────────────── -->
      <h3 class="section-heading">Choose a plan</h3>
      <div class="plans-grid">
        <div
          v-for="plan in plans"
          :key="plan.id"
          class="plan-card"
          :class="{ current: sub.plan?.id === plan.id, popular: plan.name === 'Professional' }"
        >
          <div class="plan-popular-badge" v-if="plan.name === 'Professional'">Most popular</div>
          <div class="plan-header">
            <span class="plan-name">{{ plan.name }}</span>
            <div class="plan-price">
              <span class="plan-amount">${{ plan.price_monthly }}</span>
              <span class="plan-period">/mo</span>
            </div>
          </div>
          <ul class="plan-features">
            <li>
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              {{ plan.max_sessions_per_month.toLocaleString() }} sessions/mo
            </li>
            <li>
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Up to {{ plan.max_clients }} chatbot{{ plan.max_clients !== 1 ? 's' : '' }}
            </li>
            <li>
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              AI chat + lead capture
            </li>
            <li v-if="plan.price_monthly > 0">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              WhatsApp + Messenger
            </li>
            <li v-if="plan.price_monthly >= 79">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              HubSpot CRM sync
            </li>
            <li v-if="plan.price_monthly >= 149">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke="#22c55e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              BYOK (your own AI key)
            </li>
          </ul>
          <button
            class="plan-btn"
            :class="{ 'plan-btn-current': sub.plan?.id === plan.id, 'plan-btn-upgrade': sub.plan?.id !== plan.id }"
            :disabled="sub.plan?.id === plan.id || !plan.stripe_price_id || checkoutLoading === plan.id"
            @click="checkout(plan)"
          >
            <span v-if="checkoutLoading === plan.id" class="spinner"></span>
            <span v-else-if="sub.plan?.id === plan.id">Current plan</span>
            <span v-else-if="!plan.stripe_price_id">Coming soon</span>
            <span v-else-if="sub.plan && plan.price_monthly < sub.plan.price_monthly">Downgrade</span>
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
import { ref, computed, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()

const loading = ref(true)
const portalLoading = ref(false)
const checkoutLoading = ref(null)
const error = ref('')
const sub = ref({})
const plans = ref([])

const usagePct = computed(() => {
  const used = sub.value.sessions_this_month || 0
  const max = sub.value.plan?.max_sessions_per_month || 1
  return Math.min(Math.round((used / max) * 100), 100)
})

const statusLabel = computed(() => {
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

const faqs = ref([
  { q: 'Can I cancel anytime?', a: 'Yes — cancel from the Manage billing portal. Your access continues until the end of the billing period.', open: false },
  { q: 'What happens if I exceed my session limit?', a: 'Visitors will see a polite message that the chatbot is temporarily unavailable. Upgrade your plan to restore access immediately.', open: false },
  { q: 'Can I change plans mid-month?', a: 'Yes. Upgrades are pro-rated and take effect immediately. Downgrades apply at the start of the next billing cycle.', open: false },
  { q: 'Is my payment information secure?', a: 'All payments are handled by Stripe — we never store your card details.', open: false },
])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [subData, planData] = await Promise.all([
      api.getSubscription(),
      api.getPublicPlans(),
    ])
    sub.value = subData
    plans.value = planData
  } catch (e) {
    error.value = e.message || 'Failed to load billing info.'
  } finally {
    loading.value = false
  }
}

async function checkout(plan) {
  error.value = ''
  checkoutLoading.value = plan.id
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

onMounted(load)
</script>

<style scoped>
.billing-page {
  padding: 32px;
  max-width: 1000px;
}

.page-header { margin-bottom: 28px; }
.page-title { font-size: 22px; font-weight: 700; color: #f1f5f9; margin: 0 0 4px; }
.page-sub { font-size: 13px; color: #475569; margin: 0; }

/* Skeleton */
.skeleton-wrap { display: flex; flex-direction: column; gap: 12px; }
.sk-card { background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
.sk-line { height: 12px; border-radius: 6px; background: rgba(255,255,255,0.05); animation: pulse 1.5s ease-in-out infinite; }
.sk-line.w60 { width: 60%; }
.sk-line.w40 { width: 40%; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Current plan card */
.current-plan-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1a1a2e;
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 16px;
  padding: 24px 28px;
  margin-bottom: 12px;
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

.cp-plan-name { font-size: 20px; font-weight: 700; color: #f1f5f9; margin: 0 0 4px; }
.cp-price { font-size: 28px; font-weight: 800; color: #f1f5f9; margin: 0 0 8px; }
.cp-price span { font-size: 14px; font-weight: 400; color: #64748b; }
.cp-meta { font-size: 13px; color: #64748b; margin-bottom: 8px; }

.usage-bar-wrap { display: flex; align-items: center; gap: 10px; }
.usage-bar { flex: 1; height: 6px; background: rgba(255,255,255,0.06); border-radius: 6px; overflow: hidden; max-width: 200px; }
.usage-fill { height: 100%; border-radius: 6px; transition: width 0.4s; }
.usage-pct { font-size: 12px; color: #64748b; }

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

/* Plan grid */
.section-heading { font-size: 14px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin: 24px 0 16px; }

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}

.plan-card {
  background: #1a1a2e;
  border: 1px solid rgba(255,255,255,0.06);
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
  background: linear-gradient(135deg, #1a1a2e, #1e1b3a);
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
.plan-name { font-size: 13px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; }
.plan-price { display: flex; align-items: baseline; gap: 2px; }
.plan-amount { font-size: 32px; font-weight: 800; color: #f1f5f9; }
.plan-period { font-size: 13px; color: #475569; }

.plan-features { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.plan-features li { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #94a3b8; }

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
.plan-btn:disabled:not(.plan-btn-current) { opacity: 0.4; cursor: not-allowed; }
.plan-btn-upgrade:hover:not(:disabled) { opacity: 0.9; }

/* Spinner */
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.error-msg { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 13px; margin-bottom: 16px; }

/* FAQ */
.faq-section { margin-top: 8px; }
.faq-list { display: flex; flex-direction: column; gap: 1px; }
.faq-item {
  background: #1a1a2e;
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 10px;
  padding: 14px 18px;
  cursor: pointer;
  margin-bottom: 6px;
}
.faq-q { display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: #cbd5e1; font-weight: 500; }
.faq-a { font-size: 13px; color: #64748b; margin-top: 10px; line-height: 1.6; }
</style>
