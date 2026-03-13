/**
 * Admin API composable — handles JWT auth, API calls, and token refresh.
 */
const API_BASE = window.__CF_API_URL__ || 'http://localhost:8000'

function getToken() {
  return localStorage.getItem('cf_access_token')
}

async function apiFetch(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    // Try to refresh
    const refreshed = await tryRefresh()
    if (refreshed) {
      headers.Authorization = `Bearer ${getToken()}`
      return fetch(`${API_BASE}${path}`, { ...options, headers })
    }
    // Redirect to login
    localStorage.removeItem('cf_access_token')
    localStorage.removeItem('cf_refresh_token')
    window.location.href = '/admin/login'
    return res
  }
  return res
}

async function tryRefresh() {
  const refresh = localStorage.getItem('cf_refresh_token')
  if (!refresh) return false
  try {
    const res = await fetch(`${API_BASE}/api/admin/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) return false
    const data = await res.json()
    localStorage.setItem('cf_access_token', data.access)
    if (data.refresh) localStorage.setItem('cf_refresh_token', data.refresh)
    return true
  } catch {
    return false
  }
}

export function useAdminApi() {
  async function login(username, password) {
    const res = await fetch(`${API_BASE}/api/admin/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) throw new Error('Invalid credentials')
    const data = await res.json()
    localStorage.setItem('cf_access_token', data.access)
    localStorage.setItem('cf_refresh_token', data.refresh)
    return data
  }

  function logout() {
    localStorage.removeItem('cf_access_token')
    localStorage.removeItem('cf_refresh_token')
    window.location.href = '/admin/login'
  }

  async function getMe() {
    const res = await apiFetch('/api/admin/auth/me/')
    return res.json()
  }

  async function getKanban() {
    const res = await apiFetch('/api/chat/admin/kanban/')
    return res.json()
  }

  async function patchSession(sessionId, data) {
    const res = await apiFetch(`/api/chat/admin/sessions/${sessionId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
    return res.json()
  }

  async function takeoverSession(sessionId) {
    const res = await apiFetch(`/api/chat/admin/sessions/${sessionId}/takeover/`, { method: 'POST' })
    return res.json()
  }

  async function releaseSession(sessionId) {
    const res = await apiFetch(`/api/chat/admin/sessions/${sessionId}/release/`, { method: 'POST' })
    return res.json()
  }

  async function sendAdminMessage(sessionId, message) {
    const res = await apiFetch(`/api/chat/admin/sessions/${sessionId}/send/`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    })
    return res.json()
  }

  async function getClients() {
    const res = await apiFetch('/api/admin/clients/')
    return res.json()
  }

  async function getPlatformStats() {
    const res = await apiFetch('/api/admin/superadmin/stats/')
    return res.json()
  }

  return {
    login, logout, getMe,
    getKanban, patchSession, takeoverSession, releaseSession, sendAdminMessage,
    getClients, getPlatformStats,
    getToken,
    API_BASE,
  }
}
