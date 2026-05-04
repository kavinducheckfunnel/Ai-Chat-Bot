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

function getHeaders() {
  const token = localStorage.getItem('cf_access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function apiFetch(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: getHeaders(),
    ...opts,
  })
  if (res.status === 401) {
    localStorage.removeItem('cf_access_token')
    localStorage.removeItem('cf_refresh_token')
    window.location.href = '/admin/login'
    return
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
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

    forgotPassword: (email) => fetch(`${API_BASE}/api/admin/auth/forgot-password/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    }).then(r => r.json()),

    resetPassword: (uid, token, new_password) => fetch(`${API_BASE}/api/admin/auth/reset-password/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid, token, new_password }),
    }).then(r => r.json()),

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

    getClientSessions(id, params = {}) {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined && v !== false))
      ).toString()
      return apiFetch(`/api/admin/clients/${id}/sessions/${qs ? '?' + qs : ''}`)
    },

    getClientAnalytics: (id, period = '30d') => apiFetch(`/api/admin/clients/${id}/analytics/?period=${period}`),

    async exportAnalyticsCSV(clientId, period = '30d') {
      const token = localStorage.getItem('cf_access_token')
      const res = await fetch(`${API_BASE}/api/admin/clients/${clientId}/analytics/export/?period=${period}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Export failed')
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

    sendMessage: (id, message) => apiFetch(`/api/admin/sessions/${id}/send/`, {
      method: 'POST', body: JSON.stringify({ message }),
    }),

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
      localStorage.setItem('cf_access_token', returnToken)
      localStorage.setItem('cf_user', returnUser)
      localStorage.removeItem('cf_impersonating')
      localStorage.removeItem('cf_impersonate_return_token')
      localStorage.removeItem('cf_impersonate_return_user')
      window.location.href = '/admin/tenants'
    },

    assignClientToTenant: (clientId, tenantId) => apiFetch(`/api/admin/clients/${clientId}/assign-tenant/`, {
      method: 'POST', body: JSON.stringify({ tenant_id: tenantId }),
    }),

    // ── Portal helpers ────────────────────────────────────────────────
    async getPortalClient() {
      const clients = await apiFetch('/api/admin/clients/')
      return clients?.[0] || null
    },

    updatePortalClient: (id, data) => apiFetch(`/api/admin/clients/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    getPortalSessions: (clientId, params = {}) => {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
      ).toString()
      return apiFetch(`/api/admin/clients/${clientId}/sessions/${qs ? '?' + qs : ''}`)
    },

    getPortalAnalytics: (clientId, period = '30d') => apiFetch(`/api/admin/clients/${clientId}/analytics/?period=${period}`),

    // ── Billing ──────────────────────────────────────────────────────────────
    getSubscription: () => apiFetch('/api/admin/billing/subscription/'),

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
