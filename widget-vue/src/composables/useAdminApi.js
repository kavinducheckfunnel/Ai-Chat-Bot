const API_BASE = 'http://localhost:8000'
const WS_BASE = 'ws://localhost:8000'

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

    triggerScrape: (id) => apiFetch(`/api/admin/clients/${id}/scrape/`, { method: 'POST' }),

    // ── Sessions ─────────────────────────────────────────────────────────
    getSession: (id) => apiFetch(`/api/admin/sessions/${id}/`),

    updateSession: (id, data) => apiFetch(`/api/admin/sessions/${id}/`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

    // ── Kanban ───────────────────────────────────────────────────────────
    getKanban: () => apiFetch('/api/admin/kanban/'),

    // ── God View ─────────────────────────────────────────────────────────
    takeoverSession: (id) => apiFetch(`/api/admin/sessions/${id}/takeover/`, { method: 'POST' }),

    releaseSession: (id) => apiFetch(`/api/admin/sessions/${id}/release/`, { method: 'POST' }),

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

    assignPlan: (tenantId, planId) => apiFetch(`/api/admin/tenants/${tenantId}/assign-plan/`, {
      method: 'POST', body: JSON.stringify({ plan_id: planId }),
    }),

    impersonateTenant: (tenantId) => apiFetch(`/api/admin/tenants/${tenantId}/impersonate/`, { method: 'POST' }),

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
