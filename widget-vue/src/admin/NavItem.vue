<template>
  <RouterLink
    :to="item.to"
    :class="[
      'group flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors',
      isActive
        ? 'bg-sidebar-accent text-sidebar-foreground'
        : 'text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground',
    ]"
    :title="collapsed ? item.label : undefined"
  >
    <component :is="item.icon" class="h-4 w-4 shrink-0" />
    <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
    <Badge v-if="item.badge && !collapsed" variant="secondary" class="ml-auto text-[10px] px-1.5 py-0">
      {{ item.badge }}
    </Badge>
  </RouterLink>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Badge from '@/components/ui/Badge.vue'

const props = defineProps({
  item: { type: Object, required: true },
  collapsed: { type: Boolean, default: false },
})

const route = useRoute()
const isActive = computed(() =>
  props.item.exact ? route.path === props.item.to : route.path.startsWith(props.item.to)
)
</script>
