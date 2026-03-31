<template>
  <aside class="sidebar">
    <!-- Brand -->
    <div class="brand">
      <div class="brand-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="url(#sg-p)"/>
          <defs>
            <linearGradient id="sg-p" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#A5B4FC"/>
              <stop offset="100%" stop-color="#C4B5FD"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
      <span class="brand-name">Checkfunnel</span>
    </div>

    <!-- Client badge -->
    <div class="client-badge" v-if="props.client">
      <div class="client-dot" :style="{ background: props.client.chatbot_color || '#6366f1' }"></div>
      <span class="client-name">{{ props.client.name }}</span>
    </div>

    <nav class="nav">
      <!-- INBOX -->
      <p class="nav-section">Inbox</p>
      <router-link to="/portal/inbox" class="nav-item" :class="{ active: $route.path === '/portal/inbox' }">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        All chats
        <span class="badge" v-if="liveBadge > 0">{{ liveBadge }}</span>
      </router-link>

      <!-- CUSTOMERS -->
      <p class="nav-section">Customers</p>
      <router-link to="/portal/customers" class="nav-item" :class="{ active: $route.path === '/portal/customers' }">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="2"/></svg>
        All leads
      </router-link>

      <!-- REPORTS -->
      <p class="nav-section">Reports</p>
      <router-link to="/portal/reports" class="nav-item" :class="{ active: $route.path === '/portal/reports' }">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/><rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/><rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/><rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/></svg>
        Overview
      </router-link>

      <!-- SETTINGS -->
      <p class="nav-section">Settings</p>
      <router-link to="/portal/settings" class="nav-item" :class="{ active: $route.path.startsWith('/portal/settings') }">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Channels & embed
      </router-link>
    </nav>

    <!-- Impersonation banner -->
    <div v-if="isImpersonating" class="impersonate-banner">
      <div class="impersonate-info">
        <span class="impersonate-label">Superadmin view</span>
        <span class="impersonate-name">{{ user?.username }}</span>
      </div>
      <button class="return-btn" @click="returnFromImpersonation">
        <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M9 14L4 9l5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 9h10.5a6.5 6.5 0 010 13H11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Return
      </button>
    </div>

    <!-- User footer -->
    <div class="sidebar-bottom">
      <div class="user-card">
        <div class="avatar" :style="{ background: props.client?.chatbot_color || '#6366f1' }">
          {{ initials }}
        </div>
        <div class="user-info">
          <p class="user-name">{{ user?.username || 'Tenant' }}</p>
          <p class="user-role">{{ user?.email || 'tenant admin' }}</p>
        </div>
      </div>
      <button class="logout-btn" @click="logout" title="Logout">
        <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()
const user = computed(() => api.getUser())
const isImpersonating = computed(() => api.isImpersonating())
const initials = computed(() => (user.value?.username || 'T').slice(0, 2).toUpperCase())

const liveBadge = ref(0)
let ws = null

onMounted(() => {
  ws = api.connectAdminDashboard((msg) => {
    if (msg.type === 'session_update') {
      // Update live count based on active sessions
      if (msg.active_count !== undefined) liveBadge.value = msg.active_count
    }
  })
})

onUnmounted(() => { if (ws) ws.close() })

function logout() { api.logout() }
function returnFromImpersonation() { api.returnFromImpersonation() }
</script>

<style scoped>
.sidebar {
  width: 224px;
  min-width: 224px;
  background: #111111;
  border-right: 1px solid rgba(255,255,255,0.06);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  gap: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 8px;
  margin-bottom: 20px;
}

.brand-icon {
  width: 32px; height: 32px;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.22);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
}

.brand-name {
  font-size: 14px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.3px;
}

.client-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 10px;
  background: rgba(255,255,255,0.04);
  border-radius: 8px;
  margin-bottom: 18px;
}

.client-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.client-name {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav { flex: 1; display: flex; flex-direction: column; gap: 1px; }

.nav-section {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #334155;
  padding: 0 10px;
  margin: 14px 0 4px;
}
.nav-section:first-child { margin-top: 0; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  text-decoration: none;
  transition: all 0.12s;
  position: relative;
}

.nav-item:hover { background: rgba(255,255,255,0.04); color: #cbd5e1; }
.nav-item.active { background: rgba(99,102,241,0.12); color: #a5b4fc; }

.badge {
  margin-left: auto;
  background: #6366f1;
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.impersonate-banner {
  margin: 8px 0;
  padding: 8px 10px;
  background: rgba(234,179,8,0.1);
  border: 1px solid rgba(234,179,8,0.25);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.impersonate-info { display: flex; flex-direction: column; min-width: 0; }
.impersonate-label { font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #ca8a04; }
.impersonate-name { font-size: 11px; font-weight: 600; color: #fde68a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.return-btn {
  display: flex; align-items: center; gap: 3px;
  padding: 4px 8px;
  background: rgba(234,179,8,0.15);
  border: 1px solid rgba(234,179,8,0.35);
  border-radius: 6px;
  color: #fde68a;
  font-size: 10px; font-weight: 600;
  cursor: pointer; white-space: nowrap;
  transition: all 0.12s; flex-shrink: 0;
}
.return-btn:hover { background: rgba(234,179,8,0.28); }

.sidebar-bottom {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 6px;
  border-top: 1px solid rgba(255,255,255,0.05);
  margin-top: 8px;
}

.user-card { flex: 1; display: flex; align-items: center; gap: 8px; min-width: 0; }

.avatar {
  width: 28px; height: 28px;
  border-radius: 7px;
  color: white;
  font-size: 10px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.user-info { min-width: 0; }
.user-name { font-size: 12px; font-weight: 600; color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { font-size: 10px; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.logout-btn {
  background: none; border: none; cursor: pointer;
  padding: 5px; border-radius: 6px; color: #475569;
  display: flex; align-items: center;
  transition: all 0.12s; flex-shrink: 0;
}
.logout-btn:hover { background: rgba(239,68,68,0.1); color: #fca5a5; }
</style>
