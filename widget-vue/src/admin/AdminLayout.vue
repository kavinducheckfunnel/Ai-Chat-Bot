<template>
  <div class="flex h-screen overflow-hidden bg-background">
    <!-- Sidebar -->
    <AppSidebar
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileOpen"
      :user="user"
      :plan-info="planInfo"
      @close="mobileOpen = false"
      @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
    />

    <!-- Main content area -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <!-- Top bar -->
      <header class="flex h-16 shrink-0 items-center gap-4 border-b bg-background px-6">
        <!-- Mobile menu button -->
        <button
          class="lg:hidden rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          @click="mobileOpen = true"
        >
          <Menu class="h-5 w-5" />
        </button>

        <!-- Breadcrumb -->
        <div class="flex items-center gap-1 text-sm text-muted-foreground">
          <span>Checkfunnel</span>
          <ChevronRight class="h-3.5 w-3.5" />
          <span class="font-medium text-foreground">{{ pageTitle }}</span>
        </div>

        <!-- Right side actions -->
        <div class="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="icon" @click="refreshPage">
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': refreshing }" />
          </Button>
          <div class="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-600">
            <div class="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, ChevronRight, RefreshCw } from 'lucide-vue-next'
import AppSidebar from './AppSidebar.vue'
import Button from '@/components/ui/Button.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const api = useAdminApi()
const route = useRoute()
const sidebarCollapsed = ref(false)
const mobileOpen = ref(false)
const refreshing = ref(false)

const user = computed(() => api.getUser())

const planInfo = ref(null)
api.getSubscription().then(data => {
  if (data) planInfo.value = {
    planName: data.plan?.name || 'Free',
    sessionsUsed: data.usage?.sessions?.used ?? 0,
    sessionsMax: data.usage?.sessions?.limit ?? 100,
  }
}).catch(() => {})

const PAGE_TITLES = {
  '/admin': 'Dashboard',
  '/admin/kanban': 'Kanban',
  '/admin/leads': 'Leads',
  '/admin/clients': 'Clients',
  '/admin/superadmin': 'Intelligence',
  '/admin/tenants': 'Tenants',
  '/admin/permissions': 'Permissions',
}

const pageTitle = computed(() => {
  if (route.path.startsWith('/admin/clients/')) return 'Client Detail'
  return PAGE_TITLES[route.path] || 'Dashboard'
})

function refreshPage() {
  refreshing.value = true
  setTimeout(() => { refreshing.value = false }, 1000)
  window.location.reload()
}
</script>
