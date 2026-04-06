import { createApp, defineComponent, h } from 'vue'
import { createRouter, createWebHistory, RouterView } from 'vue-router'

import LoginView from './admin/LoginView.vue'
import SignupView from './admin/SignupView.vue'
import ForgotPasswordView from './admin/ForgotPasswordView.vue'
import ResetPasswordView from './admin/ResetPasswordView.vue'
import AdminLayout from './admin/AdminLayout.vue'
import LiveDashboard from './admin/LiveDashboard.vue'
import ClientList from './admin/ClientList.vue'
import ClientDetail from './admin/ClientDetail.vue'
import KanbanView from './admin/KanbanView.vue'
import GodView from './admin/GodView.vue'
import TenantManagement from './admin/TenantManagement.vue'
import LeadManagement from './admin/LeadManagement.vue'

import PortalLayout from './portal/PortalLayout.vue'
import OnboardingWizard from './portal/OnboardingWizard.vue'
import PortalInbox from './portal/PortalInbox.vue'
import PortalCustomers from './portal/PortalCustomers.vue'
import PortalReports from './portal/PortalReports.vue'
import PortalSettings from './portal/PortalSettings.vue'
import PortalLiveView from './portal/PortalLiveView.vue'
import PortalKanban from './portal/PortalKanban.vue'
import PortalBilling from './portal/PortalBilling.vue'

function getUser() {
  try { return JSON.parse(localStorage.getItem('cf_user') || 'null') } catch { return null }
}

function isTenantAdmin(user) {
  return user?.role === 'tenant_admin' && !user?.is_superuser
}

const routes = [
  // ── Shared auth ──────────────────────────────────────────────────────────
  { path: '/admin/login', component: LoginView, meta: { public: true } },
  { path: '/portal/login', redirect: '/admin/login' },
  { path: '/signup', component: SignupView, meta: { public: true } },
  { path: '/forgot-password', component: ForgotPasswordView, meta: { public: true } },
  { path: '/reset-password', component: ResetPasswordView, meta: { public: true } },

  // ── Superadmin / staff admin SPA ─────────────────────────────────────────
  {
    path: '/admin',
    component: AdminLayout,
    meta: { adminOnly: true },
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

  // ── Tenant self-service portal ────────────────────────────────────────────
  {
    path: '/portal',
    component: PortalLayout,
    meta: { portalOnly: true },
    children: [
      { path: '', redirect: '/portal/inbox' },
      { path: 'setup', component: OnboardingWizard },
      { path: 'inbox', component: PortalInbox },
      { path: 'customers', component: PortalCustomers },
      { path: 'reports', component: PortalReports },
      { path: 'settings', component: PortalSettings },
      { path: 'live', component: PortalLiveView },
      { path: 'pipeline', component: PortalKanban },
      { path: 'billing', component: PortalBilling },
    ],
  },

  // ── Fallback ──────────────────────────────────────────────────────────────
  { path: '/:pathMatch(.*)*', redirect: '/admin/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('cf_access_token')

  // Public routes: redirect logged-in users to their dashboard
  if (to.meta.public) {
    if (token && (to.path === '/signup' || to.path === '/admin/login')) {
      const user = getUser()
      return isTenantAdmin(user) ? '/portal/inbox' : '/admin'
    }
    return true
  }

  // No token → login
  if (!token) return '/admin/login'

  const user = getUser()

  // Tenant admins must stay in /portal/
  if (to.meta.adminOnly && isTenantAdmin(user)) {
    return '/portal/inbox'
  }

  // Superadmins can't access portalOnly unless impersonating a tenant
  if (to.meta.portalOnly && !isTenantAdmin(user) && !localStorage.getItem('cf_impersonating')) {
    return '/admin'
  }

  // Superadmin-only guard
  if (to.meta.superadminOnly) {
    if (!user?.is_superuser && user?.role !== 'superadmin') return '/admin'
  }
})

const Root = defineComponent({ render: () => h(RouterView) })
const app = createApp(Root)
app.use(router)
app.mount('#cf-admin-root')
