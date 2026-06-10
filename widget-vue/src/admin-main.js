import './assets/cf-theme.css'
import { createApp, defineComponent, h } from 'vue'
import { createRouter, createWebHistory, RouterView } from 'vue-router'

import LoginView from './admin/LoginView.vue'
import SignupView from './admin/SignupView.vue'
import PricingView from './admin/PricingView.vue'
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
import SuperAdminDashboard from './admin/Dashboard.vue'
import PermissionsManager from './admin/PermissionsManager.vue'
import AdminClientInsights from './admin/AdminClientInsights.vue'
import AdminClientHeatmap from './admin/AdminClientHeatmap.vue'
import AdminVisitors from './admin/AdminVisitors.vue'
import AdminInsights from './admin/AdminInsights.vue'
import AdminBackups from './admin/AdminBackups.vue'
import AdminPrompts from './admin/AdminPrompts.vue'
import AdminPromptEditor from './admin/AdminPromptEditor.vue'

import PortalLayout from './portal/PortalLayout.vue'
import OnboardingWizard from './portal/OnboardingWizard.vue'
import PortalInbox from './portal/PortalInbox.vue'
import PortalCustomers from './portal/PortalCustomers.vue'
import PortalReports from './portal/PortalReports.vue'
import PortalReferrals from './portal/PortalReferrals.vue'
import PortalSettings from './portal/PortalSettings.vue'
import PortalIntegrations from './portal/PortalIntegrations.vue'
import PortalLiveView from './portal/PortalLiveView.vue'
import PortalKanban from './portal/PortalKanban.vue'
import PortalBilling from './portal/PortalBilling.vue'
import PortalActivity from './portal/PortalActivity.vue'
import PortalVisitors from './portal/PortalVisitors.vue'

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
  { path: '/pricing', component: PricingView, meta: { public: true } },
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
      { path: 'clients/:id/insights', component: AdminClientInsights },
      { path: 'clients/:id/heatmap', component: AdminClientHeatmap },
      { path: 'visitors', component: AdminVisitors },
      { path: 'insights', component: AdminInsights },
      { path: 'kanban', component: KanbanView },
      { path: 'leads', component: LeadManagement },
      { path: 'godview/:id', component: GodView },
      { path: 'tenants', component: TenantManagement, meta: { superadminOnly: true } },
      { path: 'superadmin', component: SuperAdminDashboard, meta: { superadminOnly: true } },
      { path: 'permissions', component: PermissionsManager, meta: { superadminOnly: true } },
      { path: 'backups', component: AdminBackups, meta: { superadminOnly: true } },
      { path: 'prompts', component: AdminPrompts, meta: { superadminOnly: true } },
      { path: 'prompts/:slug', component: AdminPromptEditor, meta: { superadminOnly: true } },
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
      { path: 'referrals', component: PortalReferrals },
      { path: 'settings', component: PortalSettings },
      { path: 'integrations', component: PortalIntegrations },
      { path: 'live', component: PortalLiveView },
      { path: 'activity', component: PortalActivity },
      { path: 'visitors', component: PortalVisitors },
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

// Self-heal stale impersonation sessions created before the refresh-token fix.
// Those left the super-admin's refresh token in place, so a silent token
// refresh would revert the session to the super-admin (who has no tenant plan
// → the portal showed "No plan / Free" and disabled features). We detect such
// sessions by the absence of the return-refresh marker and cleanly restore the
// super-admin session, so the user can re-impersonate with the fixed flow.
;(function healStaleImpersonation() {
  try {
    if (localStorage.getItem('cf_impersonating') === 'true'
        && !localStorage.getItem('cf_impersonate_return_refresh')) {
      const retToken = localStorage.getItem('cf_impersonate_return_token')
      const retUser = localStorage.getItem('cf_impersonate_return_user')
      if (retToken) localStorage.setItem('cf_access_token', retToken)
      if (retUser) localStorage.setItem('cf_user', retUser)
      localStorage.removeItem('cf_impersonating')
      localStorage.removeItem('cf_impersonate_return_token')
      localStorage.removeItem('cf_impersonate_return_user')
    }
  } catch {}
})()

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
