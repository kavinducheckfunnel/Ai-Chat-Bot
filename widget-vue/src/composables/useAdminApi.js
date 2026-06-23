// Derive the backend URL from wherever the admin SPA is being served.
// In dev (npm run dev on :5173) window.location.origin is the Vite dev server,
// so fall back to localhost:8000.  In production the admin is served from the
// same Django/Daphne origin, so window.location.origin is already correct.
const API_BASE =
  window.location.port === '5173'
    ? 'http://localhost:8000'
    : window.location.origin
const WS_BASE = API_BASE.replace(/^http/, 'ws')
export const WIDGET_URL = `${API_BASE}/widget/widget.js`

function getHeaders(token) {
  const t = token || localStorage.getItem('cf_access_token')
  return {
    'Content-Type': 'application/json',
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
  }
}

async function tryRefreshToken() {
  const refresh = localStorage.getItem('cf_refresh_token')
  if (!refresh) return null
  try {
    const res = await fetch(`${API_BASE}/api/admin/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) return null
    const data = await res.json()
    if (data.access) {
      localStorage.setItem('cf_access_token', data.access)
      return data.access
    }
  } catch {}
  return null
}

function redirectToLogin() {
  localStorage.removeItem('cf_access_token')
  localStorage.removeItem('cf_refresh_token')
  window.location.href = '/admin/login'
}

async function apiFetch(path, opts = {}) {
  // Merge caller-provided headers WITH the auth-header set. Without this
  // merge, any caller passing custom headers (e.g. X-Reauth-Token) would
  // accidentally drop the Authorization header on retry-after-refresh.
  const { headers: callerHeaders, ...rest } = opts
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: { ...getHeaders(), ...(callerHeaders || {}) },
  })
  if (res.status === 401) {
    // Try to silently refresh the access token once
    const newToken = await tryRefreshToken()
    if (newToken) {
      const retryRes = await fetch(`${API_BASE}${path}`, {
        ...rest,
        headers: { ...getHeaders(newToken), ...(callerHeaders || {}) },
      })
      if (retryRes.status === 401) {
        redirectToLogin()
        return
      }
      if (!retryRes.ok) {
        const err = await retryRes.json().catch(() => ({ detail: retryRes.statusText }))
        const e = new Error(err.detail || 'Request failed')
        e.response = err
        e.status = retryRes.status
        throw e
      }
      if (retryRes.status === 204) return null
      return retryRes.json()
    }
    redirectToLogin()
    return
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const e = new Error(err.detail || 'Request failed')
    e.response = err
    e.status = res.status
    throw e
  }
  if (res.status === 204) return null
  return res.json()
}

export function useAdminApi() {
  return {
    // ── Auth ────────────────────────────────────────────────────────────
    async register(company_name, email, password, confirm_password) {
      const res = await fetch(`${API_BASE}/api/admin/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name, email, password, confirm_password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Registration failed')
      localStorage.setItem('cf_access_token', data.access)
      localStorage.setItem('cf_refresh_token', data.refresh)
      localStorage.setItem('cf_user', JSON.stringify(data.user))
      return data
    },

    async login(username, password) {
      const res = await fetch(`${API_BASE}/api/admin/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Login failed')
      localStorage.setItem('cf_access_token', data.access)
      localStorage.setItem('cf_refresh_token', data.refresh)
      localStorage.setItem('cf_user', JSON.stringify(data.user))
      return data
    },

    logout() {
      localStorage.removeItem('cf_access_token')
      localStorage.removeItem('cf_refresh_token')
      localStorage.removeItem('cf_user')
      window.location.href = '/admin/login'
    },

    getUser() {
      try { return JSON.parse(localStorage.getItem('cf_user') || 'null') } catch { return null }
    },

    isSuperAdmin() {
      const user = this.getUser()
      return user?.role === 'superadmin' || user?.is_superuser
    },

    getMe: () => apiFetch('/api/admin/auth/me/'),

    async forgotPassword(email) {
      const res = await fetch(`${API_BASE}/api/admin/auth/forgot-password/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Something went wrong. Please try again.')
      }
      return res.json()
    },

    async resetPassword(uid, token, new_password) {
      const res = await fetch(`${API_BASE}/api/admin/auth/reset-password/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, token, new_password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Something went wrong. Please try again.')
      }
      return res.json()
    },

    changePassword: (current_password, new_password) => apiFetch('/api/admin/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),

    // ── Platform ─────────────────────────────────────────────────────────
    getStats: () => apiFetch('/api/admin/stats/'),

    // ── Plans ────────────────────────────────────────────────────────────
    getPlans: () => apiFetch('/api/admin/plans/'),

    updatePlan: (id, data) => apiFetch(`/api/admin/plans/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    // ── Clients ──────────────────────────────────────────────────────────
    getClients: () => apiFetch('/api/admin/clients/'),

    createClient: (data) => apiFetch('/api/admin/clients/', {
      method: 'POST', body: JSON.stringify(data),
    }),

    getClient: (id) => apiFetch(`/api/admin/clients/${id}/`),

    updateClient: (id, data) => apiFetch(`/api/admin/clients/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    deleteClient: (id) => apiFetch(`/api/admin/clients/${id}/`, { method: 'DELETE' }),

    // Phase D — onboarding auto-detect. Returns { platform, detected }
    // where platform is one of 'SHOPIFY' | 'WORDPRESS' | 'CUSTOM'.
    detectPlatform: (url) => apiFetch('/api/admin/platform/detect/', {
      method: 'POST', body: JSON.stringify({ url }),
    }),

    // Upload a logo image (PNG/JPEG/GIF/WebP, ≤2 MB). The backend writes
    // it under MEDIA_ROOT, stores the absolute URL on chatbot_logo_url,
    // and returns { logo_url }.
    async uploadClientLogo(id, file) {
      const form = new FormData()
      form.append('logo', file)
      const token = localStorage.getItem('cf_access_token')
      const res = await fetch(`${API_BASE}/api/admin/clients/${id}/upload-logo/`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        const e = new Error(err.detail || 'Upload failed')
        e.status = res.status
        throw e
      }
      return res.json()
    },

    getClientSessions(id, params = {}) {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined && v !== false))
      ).toString()
      return apiFetch(`/api/admin/clients/${id}/sessions/${qs ? '?' + qs : ''}`)
    },

    getClientAnalytics: (id, period = '30d') => apiFetch(`/api/admin/clients/${id}/analytics/?period=${period}`),

    async exportAnalyticsCSV(clientId, period = '30d') {
      const path = `/api/admin/clients/${clientId}/analytics/export/?period=${period}`
      const doFetch = (tok) => fetch(`${API_BASE}${path}`, {
        headers: tok ? { Authorization: `Bearer ${tok}` } : {},
      })
      // First attempt with the current access token.
      let res = await doFetch(localStorage.getItem('cf_access_token'))
      // On 401 the token has expired — silently refresh once and retry,
      // mirroring apiFetch. The raw-fetch path used to skip this, so a
      // perfectly valid export looked "broken" whenever the 8h token aged out.
      if (res.status === 401) {
        const newToken = await tryRefreshToken()
        if (newToken) res = await doFetch(newToken)
      }
      if (res.status === 403) {
        // Plan-gated feature → clear, actionable message instead of "Export failed".
        const err = new Error('CSV export is available on the Growth plan and above. Upgrade to export your reports.')
        err.code = 'upgrade_required'
        throw err
      }
      if (!res.ok) throw new Error('Export failed. Please try again.')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics_${period}_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },

    triggerScrape: (id) => apiFetch(`/api/admin/clients/${id}/scrape/`, { method: 'POST' }),

    getScrapeProgress: (id) => apiFetch(`/api/admin/clients/${id}/scrape-progress/`),

    // ── Webhooks (real-time sync) ────────────────────────────────────────
    // Returns webhook_secret, ready-to-paste webhook URLs, 50 most recent
    // audit events, and 24h success/failure counters in a single call —
    // everything the Knowledge → Real-time sync panel needs.
    getWebhookEvents: (id) => apiFetch(`/api/admin/clients/${id}/webhook-events/`),

    // Rotates the secret; old value stops working immediately. UI should
    // confirm before calling and copy the new secret to clipboard.
    rotateWebhookSecret: (id) => apiFetch(`/api/admin/clients/${id}/rotate-secret/`, { method: 'POST' }),

    // ── Sessions ─────────────────────────────────────────────────────────
    getSession: (id) => apiFetch(`/api/admin/sessions/${id}/`),

    updateSession: (id, data) => apiFetch(`/api/admin/sessions/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    // ── Kanban ───────────────────────────────────────────────────────────
    getKanban: () => apiFetch('/api/admin/kanban/'),

    // ── Leads ─────────────────────────────────────────────────────────────
    getLeads(params = {}) {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
      ).toString()
      return apiFetch(`/api/admin/leads/${qs ? '?' + qs : ''}`)
    },

    async exportLeadsCSV(params = {}) {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
      ).toString()
      const token = localStorage.getItem('cf_access_token')
      const res = await fetch(`${API_BASE}/api/admin/leads/export/${qs ? '?' + qs : ''}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `leads_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },

    updateSessionTags: (sessionId, tags) => apiFetch(`/api/admin/sessions/${sessionId}/tags/`, {
      method: 'PATCH', body: JSON.stringify({ tags }),
    }),

    // ── God View ─────────────────────────────────────────────────────────
    takeoverSession: (id) => apiFetch(`/api/admin/sessions/${id}/takeover/`, { method: 'POST', body: '{}' }),

    releaseSession: (id) => apiFetch(`/api/admin/sessions/${id}/release/`, { method: 'POST', body: '{}' }),

    sendMessage: (id, message, attachments = []) => apiFetch(`/api/admin/sessions/${id}/send/`, {
      method: 'POST', body: JSON.stringify({ message, attachments }),
    }),

    // Upload a takeover media attachment (QA #3). multipart — no JSON header.
    uploadAttachment: async (id, file, kind) => {
      const fd = new FormData()
      fd.append('file', file)
      if (kind) fd.append('kind', kind)
      const t = localStorage.getItem('cf_access_token')
      const res = await fetch(`${API_BASE}/api/admin/sessions/${id}/upload/`, {
        method: 'POST',
        headers: { ...(t ? { Authorization: `Bearer ${t}` } : {}) },
        body: fd,
      })
      if (!res.ok) throw new Error('Upload failed')
      return res.json()
    },

    getSessionHistory: (id) => apiFetch(`/api/admin/sessions/${id}/history/`),

    // ── Tenant Management ────────────────────────────────────────────────
    getTenants: () => apiFetch('/api/admin/tenants/'),

    createTenant: (data) => apiFetch('/api/admin/tenants/', {
      method: 'POST', body: JSON.stringify(data),
    }),

    getTenant: (id) => apiFetch(`/api/admin/tenants/${id}/`),

    updateTenant: (id, data) => apiFetch(`/api/admin/tenants/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    deleteTenant: (id) => apiFetch(`/api/admin/tenants/${id}/`, { method: 'DELETE' }),

    assignPlan: (tenantId, planId, remarks = '') => apiFetch(`/api/admin/tenants/${tenantId}/assign-plan/`, {
      method: 'POST', body: JSON.stringify({ plan_id: planId, remarks }),
    }),

    getPlanHistory: (tenantId) => apiFetch(`/api/admin/tenants/${tenantId}/plan-history/`),

    impersonateTenant: (tenantId) => apiFetch(`/api/admin/tenants/${tenantId}/impersonate/`, { method: 'POST', body: '{}' }),

    isImpersonating() {
      return localStorage.getItem('cf_impersonating') === 'true'
    },

    returnFromImpersonation() {
      const returnToken = localStorage.getItem('cf_impersonate_return_token')
      const returnUser = localStorage.getItem('cf_impersonate_return_user')
      const returnRefresh = localStorage.getItem('cf_impersonate_return_refresh')
      localStorage.setItem('cf_access_token', returnToken)
      localStorage.setItem('cf_user', returnUser)
      // Restore the super-admin's refresh token (swapped out during impersonation).
      if (returnRefresh) localStorage.setItem('cf_refresh_token', returnRefresh)
      localStorage.removeItem('cf_impersonating')
      localStorage.removeItem('cf_impersonate_return_token')
      localStorage.removeItem('cf_impersonate_return_user')
      localStorage.removeItem('cf_impersonate_return_refresh')
      window.location.href = '/admin/tenants'
    },

    assignClientToTenant: (clientId, tenantId) => apiFetch(`/api/admin/clients/${clientId}/assign-tenant/`, {
      method: 'POST', body: JSON.stringify({ tenant_id: tenantId }),
    }),

    // ── Portal helpers ────────────────────────────────────────────────
    async getPortalClient() {
      // Tenant-scoped + stable: resolves the user's OWN primary client,
      // never the global-newest one. Falls back to the old list endpoint
      // only if the new route is unavailable (older backend).
      try {
        const c = await apiFetch('/api/admin/portal/client/')
        if (c !== undefined) return c || null
      } catch { /* fall through */ }
      const clients = await apiFetch('/api/admin/clients/')
      return clients?.[0] || null
    },

    updatePortalClient: (id, data) => apiFetch(`/api/admin/clients/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    getTelegramWebhookStatus: (clientId) =>
      apiFetch(`/api/admin/clients/${clientId}/telegram-webhook/`),
    reregisterTelegramWebhook: (clientId) =>
      apiFetch(`/api/admin/clients/${clientId}/telegram-webhook/`, { method: 'POST' }),

    // ── Shopify order tracking (OAuth) ─────────────────────────────────────────
    getShopifyStatus: (clientId) => apiFetch(`/api/shopify/status/${clientId}/`),
    getShopifyAuthorizeUrl: (clientId, shop) =>
      apiFetch(`/api/shopify/authorize-url/?client_id=${clientId}&shop=${encodeURIComponent(shop)}`),
    disconnectShopify: (clientId) =>
      apiFetch(`/api/shopify/disconnect/${clientId}/`, { method: 'POST', body: '{}' }),

    getPortalSessions: (clientId, params = {}) => {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
      ).toString()
      return apiFetch(`/api/admin/clients/${clientId}/sessions/${qs ? '?' + qs : ''}`)
    },

    // period: 'today'|'7d'|'30d'|'90d'|'all'|'custom'. For 'custom' pass {dateFrom, dateTo}.
    getPortalAnalytics: (clientId, period = '30d', opts = {}) => {
      const params = {}
      if (opts.dateFrom || opts.dateTo) {
        if (opts.dateFrom) params.date_from = opts.dateFrom
        if (opts.dateTo) params.date_to = opts.dateTo
      } else {
        params.period = period
      }
      const qs = new URLSearchParams(params).toString()
      return apiFetch(`/api/admin/clients/${clientId}/analytics/${qs ? '?' + qs : ''}`)
    },

    // Issue 4 — product-link click attribution
    getClientLinkClicks: (clientId, period = '30d') => apiFetch(`/api/admin/clients/${clientId}/link-clicks/?period=${period}`),
    getPlatformLinkClicks: (period = '30d') => apiFetch(`/api/admin/link-clicks/?period=${period}`),

    suggestCta: (clientId) => apiFetch(`/api/admin/clients/${clientId}/suggest-cta/`, {
      method: 'POST', body: JSON.stringify({}),
    }),

    getActivityPages: (clientId, days = 7) =>
      apiFetch(`/api/admin/clients/${clientId}/activity/pages/?days=${days}`),

    getPageHeatmap: (clientId, pageUrl, days = 7) =>
      apiFetch(`/api/admin/clients/${clientId}/heatmap/?page_url=${encodeURIComponent(pageUrl)}&days=${days}`),

    getSessionTimeline: (sessionId) =>
      apiFetch(`/api/admin/sessions/${sessionId}/timeline/`),

    getClientVisitors: (clientId, params = {}) => {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
      ).toString()
      return apiFetch(`/api/admin/clients/${clientId}/visitors/${qs ? '?' + qs : ''}`)
    },

    getVisitorDetail: (visitorUid, clientId) =>
      apiFetch(`/api/admin/visitors/${visitorUid}/?client_id=${clientId}`),

    // ── Billing ──────────────────────────────────────────────────────────────
    getSubscription: () => apiFetch('/api/admin/billing/subscription/'),
    getAddOnOptions: () => apiFetch('/api/admin/billing/addons/'),
    purchaseAddOn: (kind, quantity) => apiFetch('/api/admin/billing/addons/purchase/', {
      method: 'POST', body: JSON.stringify({ kind, quantity }),
    }),
    grantAddOnCredits: (tenant_id, kind, quantity, reason) =>
      apiFetch('/api/admin/billing/addons/grant/', {
        method: 'POST', body: JSON.stringify({ tenant_id, kind, quantity, reason }),
      }),

    // Invoices
    listInvoices: () => apiFetch('/api/admin/billing/invoices/'),
    sendTestInvoice: (to) => apiFetch('/api/admin/billing/invoices/test-email/', {
      method: 'POST', body: JSON.stringify({ to: to || '' }),
    }),

    getPublicPlans: () => apiFetch('/api/admin/billing/plans/'),

    createCheckoutSession: (planId) => apiFetch('/api/admin/billing/checkout/', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
    }),

    createPortalSession: () => apiFetch('/api/admin/billing/portal/', {
      method: 'POST',
      body: '{}',
    }),

    // ── Revenue & Health (superadmin) ─────────────────────────────────
    getRevenue: () => apiFetch('/api/admin/revenue/'),
    getTenantHealthBoard: () => apiFetch('/api/admin/health/'),
    getLifecycleAlerts: () => apiFetch('/api/admin/alerts/'),
    getAuditLog: (params = {}) => {
      const qs = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([,v]) => v))).toString()
      return apiFetch(`/api/admin/audit/${qs ? '?' + qs : ''}`)
    },

    // ── Subscription management (superadmin) ─────────────────────────
    getTenantSubscription: (tenantId) => apiFetch(`/api/admin/tenants/${tenantId}/subscription/`),
    updateTenantSubscription: (tenantId, data) => apiFetch(`/api/admin/tenants/${tenantId}/subscription/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    // ── Feature Overrides ─────────────────────────────────────────────
    getTenantFeatureOverrides: (tenantId) => apiFetch(`/api/admin/tenants/${tenantId}/feature-overrides/`),
    createFeatureOverride: (tenantId, data) => apiFetch(`/api/admin/tenants/${tenantId}/feature-overrides/`, {
      method: 'POST', body: JSON.stringify(data),
    }),
    deleteFeatureOverride: (tenantId, overrideId) => apiFetch(`/api/admin/tenants/${tenantId}/feature-overrides/${overrideId}/`, {
      method: 'DELETE',
    }),

    // ── Announcements ─────────────────────────────────────────────────
    getAnnouncements: () => apiFetch('/api/admin/announcements/'),
    createAnnouncement: (data) => apiFetch('/api/admin/announcements/', {
      method: 'POST', body: JSON.stringify(data),
    }),
    dismissAnnouncement: (id) => apiFetch(`/api/admin/announcements/${id}/dismiss/`, { method: 'POST', body: '{}' }),

    // ── Feature flags (portal) ────────────────────────────────────────
    getFeatureFlags: () => apiFetch('/api/admin/feature-flags/'),

    // ── Platform AI Config (superadmin) ──────────────────────────────
    getPlatformConfig: () => apiFetch('/api/admin/platform-config/'),
    updatePlatformConfig: (data) => apiFetch('/api/admin/platform-config/', {
      method: 'PUT', body: JSON.stringify(data),
    }),
    getOpenRouterModels: () => apiFetch('/api/admin/platform-config/models/'),

    // ── Backups (superadmin) ─────────────────────────────────────────
    // Powers /admin/backups. The list endpoint returns snapshots grouped
    // by tier (daily/weekly/monthly), the status endpoint returns the
    // header strip data (latest run, disk usage, retention counts).
    getBackups:       () => apiFetch('/api/admin/backups/'),
    getBackupStatus:  () => apiFetch('/api/admin/backups/status/'),
    triggerBackup:    () => apiFetch('/api/admin/backups/trigger/', { method: 'POST', body: '{}' }),
    deleteBackup:     (tier, date) => apiFetch(`/api/admin/backups/${tier}/${date}/`, { method: 'DELETE' }),

    // Auth-protected download: fetch with Bearer header, then trigger an
    // <a download> click via Blob. This works for any reasonably-sized
    // file (the browser holds the blob in RAM, so don't expect to download
    // 10GB this way — but our backups are ~5-50MB right now).
    async downloadBackupFile(tier, date, filename) {
      const token = localStorage.getItem('cf_access_token') || ''
      const url   = `${API_BASE}/api/admin/backups/${tier}/${date}/${encodeURIComponent(filename)}/`
      const resp  = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!resp.ok) {
        throw new Error(`Download failed (${resp.status})`)
      }
      const blob  = await resp.blob()
      const obj   = URL.createObjectURL(blob)
      const a     = document.createElement('a')
      a.href      = obj
      a.download  = `checkfunnel-${tier}-${date}-${filename}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      // Free the blob URL on next tick — leaving it briefly bound lets
      // some browsers actually finish persisting the download.
      setTimeout(() => URL.revokeObjectURL(obj), 1000)
    },

    // ── Prompt editor (superadmin) ───────────────────────────────────────
    // Powers /admin/prompts. Writes (save / rollback / reset) require a
    // short-lived re-auth token issued by promptReauth() — pass it as the
    // `reauthToken` arg and we'll attach it as X-Reauth-Token.
    promptReauth: (password) => apiFetch('/api/admin/prompts/reauth/', {
      method: 'POST', body: JSON.stringify({ password }),
    }),
    listPrompts:    ()     => apiFetch('/api/admin/prompts/'),
    getPrompt:      (slug) => apiFetch(`/api/admin/prompts/${slug}/`),
    getPromptVersions:      (slug)    => apiFetch(`/api/admin/prompts/${slug}/versions/`),
    getPromptVersionDetail: (slug, vid) => apiFetch(`/api/admin/prompts/${slug}/versions/${vid}/`),
    previewPrompt:  (slug, body) => apiFetch(`/api/admin/prompts/${slug}/preview/`, {
      method: 'POST', body: JSON.stringify({ body }),
    }),
    savePrompt: (slug, body, notes, reauthToken) => apiFetch(`/api/admin/prompts/${slug}/save/`, {
      method: 'POST',
      headers: { 'X-Reauth-Token': reauthToken || '' },
      body: JSON.stringify({ body, notes: notes || '' }),
    }),
    rollbackPrompt: (slug, versionId, reauthToken) => apiFetch(`/api/admin/prompts/${slug}/rollback/`, {
      method: 'POST',
      headers: { 'X-Reauth-Token': reauthToken || '' },
      body: JSON.stringify({ version_id: versionId }),
    }),
    resetPrompt: (slug, reauthToken) => apiFetch(`/api/admin/prompts/${slug}/reset/`, {
      method: 'POST',
      headers: { 'X-Reauth-Token': reauthToken || '' },
      body: '{}',
    }),

    // ── WebSocket ────────────────────────────────────────────────────────
    connectAdminDashboard(onMessage) {
      const token = localStorage.getItem('cf_access_token')
      const ws = new WebSocket(`${WS_BASE}/ws/admin/dashboard/?token=${token}`)
      ws.onmessage = (e) => {
        try { onMessage(JSON.parse(e.data)) } catch {}
      }
      ws.onerror = (e) => console.warn('Admin WS error', e)
      return ws
    },

    connectGodView(sessionId, onMessage) {
      const ws = new WebSocket(`${WS_BASE}/ws/chat/admin/${sessionId}/`)
      ws.onmessage = (e) => {
        try { onMessage(JSON.parse(e.data)) } catch {}
      }
      return ws
    },
  }
}
