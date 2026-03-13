<template>
  <aside class="admin-sidebar">
    <div class="sidebar-logo">
      <span class="logo-icon">💠</span>
      <span class="logo-text">Checkfunnel</span>
    </div>
    <nav class="sidebar-nav">
      <router-link to="/admin" class="nav-item" exact-active-class="active">
        <span class="icon">📊</span> Dashboard
      </router-link>
      <router-link to="/admin/clients" class="nav-item" active-class="active">
        <span class="icon">👥</span> Clients
      </router-link>
      <router-link to="/" class="nav-item back-home">
        <span class="icon">🏠</span> Back to Demo
      </router-link>
    </nav>
  </aside>
</template>

<style scoped>
.admin-sidebar {
  width: 260px;
  background: white;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}
.sidebar-logo {
  padding: 32px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo-icon {
  font-size: 1.5rem;
}
.logo-text {
  font-weight: 800;
  font-size: 1.25rem;
  letter-spacing: -0.025em;
  color: #0f172a;
}
.sidebar-nav {
  flex: 1;
  padding: 0 16px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  color: #64748b;
  text-decoration: none;
  font-weight: 500;
  margin-bottom: 4px;
  transition: all 0.2s;
}
.nav-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.nav-item.active {
  background: #eff6ff;
  color: #2563eb;
}
.back-home {
  margin-top: 32px;
  border-top: 1px solid #f1f5f9;
  padding-top: 24px;
}
</style>
