<template>
  <!-- Mobile overlay -->
  <div v-if="mobileOpen" class="fixed inset-0 z-40 bg-black/50 lg:hidden" @click="$emit('close')" />

  <!-- Sidebar -->
  <aside
    :class="[
      'fixed inset-y-0 left-0 z-50 flex h-full flex-col bg-sidebar-background text-sidebar-foreground transition-transform duration-300 lg:translate-x-0 lg:static lg:z-auto',
      collapsed && !mobileOpen ? 'w-16' : 'w-64',
      mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    ]"
  >
    <!-- Header -->
    <div class="flex h-16 items-center border-b border-sidebar-border px-4">
      <div class="flex items-center gap-3 overflow-hidden">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
          <Zap class="h-4 w-4" />
        </div>
        <span v-if="!collapsed || mobileOpen" class="truncate text-sm font-semibold text-sidebar-foreground">Checkfunnel</span>
      </div>
      <button
        class="ml-auto hidden rounded-md p-1 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground lg:flex"
        @click="$emit('toggle-collapse')"
      >
        <PanelLeft class="h-4 w-4" />
      </button>
    </div>

    <!-- Impersonation banner -->
    <div v-if="isImpersonating" class="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2">
      <div class="flex items-center gap-2">
        <UserCheck class="h-3 w-3 text-amber-400 shrink-0" />
        <span v-if="!collapsed || mobileOpen" class="text-xs text-amber-400">Viewing as tenant</span>
      </div>
      <button
        v-if="!collapsed || mobileOpen"
        class="mt-1 text-xs text-amber-400 underline hover:no-underline"
        @click="api.returnFromImpersonation()"
      >Return to superadmin</button>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto py-4">
      <!-- Main section -->
      <div class="px-3">
        <p v-if="!collapsed || mobileOpen" class="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/40">Main</p>
        <NavItem v-for="item in mainItems" :key="item.to" :item="item" :collapsed="collapsed && !mobileOpen" />
      </div>

      <!-- Superadmin section -->
      <div v-if="isSuperAdmin" class="mt-6 px-3">
        <p v-if="!collapsed || mobileOpen" class="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/40">Super Admin</p>
        <NavItem v-for="item in adminItems" :key="item.to" :item="item" :collapsed="collapsed && !mobileOpen" />
      </div>
    </nav>

    <!-- Footer: Usage + User -->
    <div class="border-t border-sidebar-border p-3 space-y-2">
      <!-- Plan usage pill -->
      <div v-if="(!collapsed || mobileOpen) && planInfo" class="rounded-md bg-sidebar-accent p-3 text-xs">
        <div class="flex items-center justify-between mb-1.5">
          <span class="font-medium text-sidebar-foreground/80">{{ planInfo.planName }}</span>
          <Badge variant="outline" class="text-[10px] border-sidebar-border text-sidebar-foreground/60 px-1.5 py-0">
            {{ planInfo.sessionsUsed }}/{{ planInfo.sessionsMax === -1 ? '∞' : planInfo.sessionsMax }}
          </Badge>
        </div>
        <div class="h-1 w-full rounded-full bg-sidebar-border overflow-hidden">
          <div
            class="h-full rounded-full bg-sidebar-primary transition-all"
            :style="{ width: planInfo.sessionsMax === -1 ? '10%' : `${Math.min(100, (planInfo.sessionsUsed / planInfo.sessionsMax) * 100)}%` }"
          />
        </div>
      </div>

      <!-- User row -->
      <DropdownMenu align="end">
        <template #trigger>
          <button class="flex w-full items-center gap-3 rounded-md px-2 py-2 hover:bg-sidebar-accent transition-colors">
            <Avatar class="h-7 w-7 shrink-0">
              <AvatarFallback class="bg-sidebar-primary text-sidebar-primary-foreground text-xs">
                {{ userInitials }}
              </AvatarFallback>
            </Avatar>
            <div v-if="!collapsed || mobileOpen" class="flex-1 overflow-hidden text-left">
              <p class="truncate text-xs font-medium text-sidebar-foreground">{{ user?.username || user?.email }}</p>
              <p class="truncate text-[10px] text-sidebar-foreground/50">{{ user?.role || 'Admin' }}</p>
            </div>
            <ChevronsUpDown v-if="!collapsed || mobileOpen" class="h-3 w-3 shrink-0 text-sidebar-foreground/40" />
          </button>
        </template>
        <DropdownMenuItem @click="$router.push('/admin/settings')">
          <Settings class="h-4 w-4" /> Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem :destructive="true" @click="api.logout()">
          <LogOut class="h-4 w-4" /> Log out
        </DropdownMenuItem>
      </DropdownMenu>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Zap, PanelLeft, LayoutDashboard, Trello, Users, Building2,
  BarChart3, Shield, UserCheck, LogOut, ChevronsUpDown, Settings,
  FileText,
} from 'lucide-vue-next'
import NavItem from './NavItem.vue'
import Avatar from '@/components/ui/Avatar.vue'
import AvatarFallback from '@/components/ui/AvatarFallback.vue'
import Badge from '@/components/ui/Badge.vue'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import DropdownMenuItem from '@/components/ui/DropdownMenuItem.vue'
import DropdownMenuSeparator from '@/components/ui/DropdownMenuSeparator.vue'
import { useAdminApi } from '@/composables/useAdminApi'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
  user: { type: Object, default: null },
  planInfo: { type: Object, default: null },
})

defineEmits(['close', 'toggle-collapse'])

const api = useAdminApi()
const isSuperAdmin = computed(() => api.isSuperAdmin())
const isImpersonating = computed(() => api.isImpersonating())
const userInitials = computed(() => {
  const name = props.user?.username || props.user?.email || '?'
  return name.slice(0, 2).toUpperCase()
})

const mainItems = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/admin/kanban', label: 'Kanban', icon: Trello },
  { to: '/admin/leads', label: 'Leads', icon: Users },
  { to: '/admin/clients', label: 'Clients', icon: Building2 },
]

const adminItems = [
  { to: '/admin/superadmin', label: 'Intelligence', icon: BarChart3 },
  { to: '/admin/tenants', label: 'Tenants', icon: Users },
  { to: '/admin/permissions', label: 'Permissions', icon: Shield },
  { to: '/admin/prompts', label: 'System Prompts', icon: FileText },
]
</script>
