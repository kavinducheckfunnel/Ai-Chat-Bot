import { createApp, defineComponent, h } from 'vue'
import { createRouter, createWebHistory, RouterView } from 'vue-router'

import LoginView from './admin/LoginView.vue'
import AdminLayout from './admin/AdminLayout.vue'
import LiveDashboard from './admin/LiveDashboard.vue'
import ClientList from './admin/ClientList.vue'
import ClientDetail from './admin/ClientDetail.vue'
import KanbanView from './admin/KanbanView.vue'
import GodView from './admin/GodView.vue'
import TenantManagement from './admin/TenantManagement.vue'
import LeadManagement from './admin/LeadManagement.vue'

const routes = [
  { path: '/admin/login', component: LoginView, meta: { public: true } },
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      { path: '', component: LiveDashboard },
      { path: 'clients', component: ClientList },
      { path: 'clients/:id', component: ClientDetail },
      { path: 'kanban', component: KanbanView },
      { path: 'leads', component: LeadManagement },
      { path: 'godview/:id', component: GodView },
      { path: 'tenants', component: TenantManagement, meta: { superadminOnly: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/admin' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('cf_access_token')
  if (!to.meta.public && !token) return '/admin/login'

  // Guard superadmin-only routes
  if (to.meta.superadminOnly) {
    try {
      const user = JSON.parse(localStorage.getItem('cf_user') || 'null')
      if (!user?.is_superuser && user?.role !== 'superadmin') return '/admin'
    } catch {
      return '/admin'
    }
  }
})

const Root = defineComponent({ render: () => h(RouterView) })
const app = createApp(Root)
app.use(router)
app.mount('#cf-admin-root')
