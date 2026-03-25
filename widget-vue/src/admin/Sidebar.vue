<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="url(#sg)"/>
          <defs>
            <linearGradient id="sg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#A5B4FC"/>
              <stop offset="100%" stop-color="#C4B5FD"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
      <span class="brand-name">Checkfunnel</span>
    </div>

    <nav class="nav">
      <p class="nav-section">Main</p>

      <router-link to="/admin" class="nav-item" :class="{ active: $route.path === '/admin' }">
        <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/><rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/><rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/><rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/></svg>
        Dashboard
      </router-link>

      <router-link to="/admin/kanban" class="nav-item" :class="{ active: $route.path === '/admin/kanban' }">
        <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><rect x="3" y="3" width="5" height="18" rx="1" stroke="currentColor" stroke-width="2"/><rect x="10" y="3" width="5" height="12" rx="1" stroke="currentColor" stroke-width="2"/><rect x="17" y="3" width="5" height="15" rx="1" stroke="currentColor" stroke-width="2"/></svg>
        Kanban
      </router-link>

      <router-link to="/admin/leads" class="nav-item" :class="{ active: $route.path === '/admin/leads' }">
        <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="2"/><line x1="19" y1="8" x2="19" y2="14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="22" y1="11" x2="16" y2="11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Leads
      </router-link>

      <router-link to="/admin/clients" class="nav-item" :class="{ active: $route.path.startsWith('/admin/clients') }">
        <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="currentColor" stroke-width="2"/><circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="2"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Clients
      </router-link>

      <!-- Superadmin only -->
      <template v-if="isSuperAdmin">
        <p class="nav-section">Admin</p>
        <router-link to="/admin/tenants" class="nav-item" :class="{ active: $route.path === '/admin/tenants' }">
          <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><polyline points="9 22 9 12 15 12 15 22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          Tenants
        </router-link>
      </template>
    </nav>

    <!-- Impersonation banner -->
    <div v-if="isImpersonating" class="impersonate-banner">
      <div class="impersonate-info">
        <span class="impersonate-label">Viewing as</span>
        <span class="impersonate-name">{{ user?.username }}</span>
      </div>
      <button class="return-btn" @click="returnFromImpersonation" title="Return to admin account">
        <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M9 14L4 9l5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 9h10.5a6.5 6.5 0 010 13H11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Return
      </button>
    </div>

    <div class="sidebar-bottom">
      <div class="user-card">
        <div class="avatar">{{ initials }}</div>
        <div class="user-info">
          <p class="user-name">{{ user?.username || 'Admin' }}</p>
          <p class="user-role">{{ user?.role || 'admin' }}</p>
        </div>
      </div>
      <button class="logout-btn" @click="logout" title="Logout">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const api = useAdminApi()
const user = computed(() => api.getUser())
const initials = computed(() => {
  const name = user.value?.username || 'A'
  return name.slice(0, 2).toUpperCase()
})
const isSuperAdmin = computed(() => api.isSuperAdmin())
const isImpersonating = computed(() => api.isImpersonating())

function logout() {
  api.logout()
}

function returnFromImpersonation() {
  api.returnFromImpersonation()
}
</script>

<style scoped>
.sidebar {
  width: 220px;
  min-width: 220px;
  background: #0F172A;
  display: flex;
  flex-direction: column;
  padding: 22px 14px;
  border-right: 1px solid rgba(255,255,255,0.05);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
  margin-bottom: 28px;
}

.brand-icon {
  width: 34px; height: 34px;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
}

.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: #F1F5F9;
  letter-spacing: -0.3px;
}

.nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }

.nav-section {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #334155;
  padding: 0 10px;
  margin-bottom: 4px;
  margin-top: 12px;
}
.nav-section:first-child { margin-top: 0; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  color: #64748B;
  text-decoration: none;
  transition: all 0.15s;
}

.nav-item:hover {
  background: rgba(255,255,255,0.05);
  color: #CBD5E1;
}

.nav-item.active {
  background: rgba(99,102,241,0.15);
  color: #A5B4FC;
}

.sidebar-bottom {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.user-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.avatar {
  width: 30px; height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  color: white;
  font-size: 11px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.user-info { min-width: 0; }

.user-name {
  font-size: 12px;
  font-weight: 600;
  color: #CBD5E1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 10px;
  color: #475569;
  text-transform: capitalize;
}

.logout-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 7px;
  color: #475569;
  display: flex; align-items: center;
  transition: all 0.15s;
  flex-shrink: 0;
}

.logout-btn:hover {
  background: rgba(239,68,68,0.1);
  color: #FCA5A5;
}

.impersonate-banner {
  margin: 0 0 10px 0;
  padding: 10px 12px;
  background: rgba(234,179,8,0.12);
  border: 1px solid rgba(234,179,8,0.3);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.impersonate-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.impersonate-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #CA8A04;
}

.impersonate-name {
  font-size: 12px;
  font-weight: 600;
  color: #FDE68A;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.return-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 9px;
  background: rgba(234,179,8,0.2);
  border: 1px solid rgba(234,179,8,0.4);
  border-radius: 6px;
  color: #FDE68A;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  flex-shrink: 0;
}

.return-btn:hover {
  background: rgba(234,179,8,0.35);
}
</style>
