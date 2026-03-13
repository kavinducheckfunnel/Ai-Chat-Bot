<template>
  <div class="layout">
    <nav class="sidebar">
      <div class="brand">
        <div class="brand-icon">CF</div>
        <span>Checkfunnel</span>
      </div>
      <ul class="nav-links">
        <li><router-link to="/admin" exact-active-class="active">
          <span class="icon">📊</span> Dashboard
        </router-link></li>
        <li><router-link to="/admin/kanban" active-class="active">
          <span class="icon">🎯</span> Lead Kanban
        </router-link></li>
        <li><router-link to="/admin/clients" active-class="active">
          <span class="icon">🏢</span> Clients
        </router-link></li>
      </ul>
      <div class="sidebar-footer">
        <div class="user-pill">{{ userRole }}</div>
        <button @click="logout" class="logout-btn">Sign Out</button>
      </div>
    </nav>
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi.js'

const { getMe, logout } = useAdminApi()
const userRole = ref('')

onMounted(async () => {
  try {
    const me = await getMe()
    userRole.value = me?.profile?.role || 'admin'
  } catch {}
})
</script>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 240px; background: #0f172a; color: white;
  display: flex; flex-direction: column; padding: 24px 0;
  position: fixed; top: 0; left: 0; height: 100vh; z-index: 50;
}
.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 0 20px 24px; border-bottom: 1px solid rgba(255,255,255,0.1);
  font-weight: 700; font-size: 1.1rem;
}
.brand-icon {
  width: 36px; height: 36px; background: #2563eb;
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 0.875rem; font-weight: 800;
}
.nav-links { list-style: none; padding: 16px 0; flex: 1; }
.nav-links li a {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 20px; color: rgba(255,255,255,0.7);
  font-size: 0.9375rem; transition: all 0.15s; border-radius: 0;
}
.nav-links li a:hover, .nav-links li a.active {
  color: white; background: rgba(37,99,235,0.3);
}
.icon { font-size: 1.1rem; }
.sidebar-footer { padding: 16px 20px; border-top: 1px solid rgba(255,255,255,0.1); }
.user-pill {
  font-size: 0.75rem; color: rgba(255,255,255,0.5);
  text-transform: uppercase; letter-spacing: 0.05em;
  margin-bottom: 8px;
}
.logout-btn {
  background: rgba(255,255,255,0.1); color: white;
  border: none; padding: 8px 16px; border-radius: 6px;
  cursor: pointer; font-size: 0.875rem; width: 100%;
  transition: background 0.2s;
}
.logout-btn:hover { background: rgba(255,255,255,0.2); }
.main-content { margin-left: 240px; flex: 1; padding: 40px; min-height: 100vh; }
</style>
