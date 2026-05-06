<template>
  <!-- Mobile overlay -->
  <div v-if="mobileOpen" class="fixed inset-0 z-40 bg-black/50 lg:hidden" @click="mobileOpen = false" />

  <!-- Sidebar -->
  <aside class="fixed inset-y-0 left-0 z-50 flex h-full w-64 flex-col bg-sidebar-background text-sidebar-foreground transition-transform duration-300 lg:translate-x-0 lg:static lg:z-auto" :class="mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'">

    <!-- Header -->
    <div class="flex h-16 items-center gap-3 border-b border-sidebar-border px-4">
      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
        <Zap class="h-4 w-4" />
      </div>
      <span class="truncate text-sm font-semibold text-sidebar-foreground">Checkfunnel</span>
    </div>

    <!-- Client badge -->
    <div v-if="props.client" class="mx-3 mt-3 flex items-center gap-2.5 rounded-md bg-sidebar-accent px-3 py-2">
      <div class="h-2 w-2 rounded-full shrink-0" :style="{ background: props.client.chatbot_color || 'hsl(var(--sidebar-primary))' }"></div>
      <span class="truncate text-xs font-medium text-sidebar-foreground/80">{{ props.client.name }}</span>
    </div>

    <!-- Impersonation banner -->
    <div v-if="isImpersonating" class="mx-3 mt-3 rounded-md bg-amber-500/10 border border-amber-500/20 px-3 py-2">
      <p class="text-[9px] font-semibold uppercase tracking-wider text-amber-400">Superadmin view</p>
      <p class="text-xs font-semibold text-amber-300 truncate">{{ user?.username }}</p>
      <button class="mt-1 text-[10px] text-amber-400 underline hover:no-underline" @click="returnFromImpersonation">Return to superadmin</button>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
      <p class="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">Inbox</p>
      <RouterLink to="/portal/inbox" :class="navClass('/portal/inbox', true)">
        <MessageSquare class="h-4 w-4 shrink-0" />
        All chats
        <span v-if="liveBadge > 0" class="ml-auto inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-sidebar-primary px-1 text-[10px] font-bold text-sidebar-primary-foreground">{{ liveBadge }}</span>
      </RouterLink>

      <p class="mt-5 mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">Customers</p>
      <RouterLink to="/portal/customers" :class="navClass('/portal/customers', true)">
        <Users class="h-4 w-4 shrink-0" />
        All leads
      </RouterLink>

      <p class="mt-5 mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">Reports</p>
      <RouterLink to="/portal/reports" :class="navClass('/portal/reports', true)">
        <BarChart3 class="h-4 w-4 shrink-0" />
        Overview
      </RouterLink>

      <p class="mt-5 mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">Live</p>
      <RouterLink to="/portal/live" :class="navClass('/portal/live', true)">
        <Eye class="h-4 w-4 shrink-0" />
        Live View
      </RouterLink>

      <p class="mt-5 mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">Pipeline</p>
      <RouterLink to="/portal/pipeline" :class="navClass('/portal/pipeline', true)">
        <Trello class="h-4 w-4 shrink-0" />
        Pipeline
      </RouterLink>

      <p class="mt-5 mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">Account</p>
      <RouterLink to="/portal/billing" :class="navClass('/portal/billing', true)">
        <CreditCard class="h-4 w-4 shrink-0" />
        Billing
      </RouterLink>
      <RouterLink to="/portal/settings" :class="navClass('/portal/settings')">
        <Settings class="h-4 w-4 shrink-0" />
        Channels &amp; embed
      </RouterLink>
    </nav>

    <!-- Footer: user + logout -->
    <div class="border-t border-sidebar-border p-3">
      <div class="flex items-center gap-2.5 rounded-md px-2 py-2">
        <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold text-sidebar-primary-foreground" :style="{ background: props.client?.chatbot_color || 'hsl(var(--sidebar-primary))' }">
          {{ initials }}
        </div>
        <div class="flex-1 overflow-hidden">
          <p class="truncate text-xs font-medium text-sidebar-foreground">{{ user?.username || 'Tenant' }}</p>
          <p class="truncate text-[10px] text-sidebar-foreground/50">{{ user?.email || 'tenant admin' }}</p>
        </div>
        <button class="rounded-md p-1.5 text-sidebar-foreground/40 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors" @click="logout" title="Logout">
          <LogOut class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  </aside>

  <!-- Mobile top bar (hidden on desktop) -->
  <div class="fixed top-0 left-0 right-0 z-30 flex h-14 items-center gap-3 border-b bg-background px-4 lg:hidden">
    <button class="rounded-md p-1.5 text-muted-foreground hover:bg-accent" @click="mobileOpen = true">
      <Menu class="h-5 w-5" />
    </button>
    <div class="flex items-center gap-2">
      <div class="flex h-6 w-6 items-center justify-center rounded bg-primary text-primary-foreground">
        <Zap class="h-3 w-3" />
      </div>
      <span class="text-sm font-semibold">Checkfunnel</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Zap, MessageSquare, Users, BarChart3, Eye, Trello, CreditCard, Settings, LogOut, Menu } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'

const props = defineProps({ client: Object })
const api = useAdminApi()
const route = useRoute()

const user = computed(() => api.getUser())
const isImpersonating = computed(() => api.isImpersonating())
const initials = computed(() => (user.value?.username || 'T').slice(0, 2).toUpperCase())
const mobileOpen = ref(false)
const liveBadge = ref(0)

let ws = null

onMounted(() => {
  ws = api.connectAdminDashboard((msg) => {
    if (msg.type === 'session_update' && msg.active_count !== undefined) {
      liveBadge.value = msg.active_count
    }
  })
})

onUnmounted(() => { if (ws) ws.close() })

function logout() { api.logout() }
function returnFromImpersonation() { api.returnFromImpersonation() }

function navClass(path, exact = false) {
  const active = exact ? route.path === path : route.path.startsWith(path)
  return [
    'group flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors',
    active
      ? 'bg-sidebar-accent text-sidebar-foreground'
      : 'text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground',
  ]
}
</script>
