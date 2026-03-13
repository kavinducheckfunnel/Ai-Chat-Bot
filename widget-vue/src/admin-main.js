import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import AdminApp from './AdminApp.vue'

// ── Route definitions ─────────────────────────────────────────────────────
const routes = [
  {
    path: '/admin/login',
    name: 'Login',
    component: () => import('./admin/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/admin',
    name: 'Dashboard',
    component: () => import('./admin/LiveDashboard.vue'),
  },
  {
    path: '/admin/god-view/:sessionId',
    name: 'GodView',
    component: () => import('./admin/GodView.vue'),
  },
  {
    path: '/admin/kanban',
    name: 'Kanban',
    component: () => import('./admin/LeadKanban.vue'),
  },
  {
    path: '/admin/clients',
    name: 'ClientList',
    component: () => import('./admin/ClientList.vue'),
  },
  {
    path: '/admin/clients/:id',
    name: 'ClientDetail',
    component: () => import('./admin/ClientDetail.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/admin' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── Auth guard ────────────────────────────────────────────────────────────
router.beforeEach((to) => {
  const token = localStorage.getItem('cf_access_token')
  if (!to.meta.public && !token) {
    return { name: 'Login' }
  }
})

const app = createApp(AdminApp)
app.use(router)
app.mount('#cf-admin-root')
