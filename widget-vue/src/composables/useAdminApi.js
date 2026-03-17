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

    // ── Platform ─────────────────────────────────────────────────────────
    getStats: () => apiFetch('/api/admin/stats/'),

    // ── Plans ────────────────────────────────────────────────────────────
    getPlans: () => apiFetch('/api/admin/plans/'),

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

    getClientSessions: (id) => apiFetch(`/api/admin/clients/${id}/sessions/`),

    getClientAnalytics: (id) => apiFetch(`/api/admin/clients/${id}/analytics/`),

    getClientPageAnalytics: (id) => apiFetch(`/api/analytics/client/${id}/`),

    triggerScrape: (id) => apiFetch(`/api/admin/clients/${id}/scrape/`, { method: 'POST' }),

    // ── Sessions ─────────────────────────────────────────────────────────
    getSession: (id) => apiFetch(`/api/admin/sessions/${id}/`),

    updateSession: (id, data) => apiFetch(`/api/admin/sessions/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    // ── Kanban ───────────────────────────────────────────────────────────
    getKanban: () => apiFetch('/api/admin/kanban/'),

    // ── God View ─────────────────────────────────────────────────────────
    takeoverSession: (id) => apiFetch(`/api/admin/sessions/${id}/takeover/`, { method: 'POST', body: '{}' }),

    releaseSession: (id) => apiFetch(`/api/admin/sessions/${id}/release/`, { method: 'POST', body: '{}' }),

    sendMessage: (id, message) => apiFetch(`/api/admin/sessions/${id}/send/`, {
      method: 'POST', body: JSON.stringify({ message }),
    }),

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
