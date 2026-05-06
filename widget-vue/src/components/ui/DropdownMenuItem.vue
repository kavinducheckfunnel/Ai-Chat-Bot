<template>
  <div
    :class="cn('relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground', destructive ? 'text-destructive hover:text-destructive' : '', props.class)"
    v-bind="$attrs"
  >
    <slot />
  </div>
</template>
<script setup>
import { cn } from '@/lib/utils'
defineOptions({ inheritAttrs: false })
const props = defineProps({
  destructive: { type: Boolean, default: false },
  class: { type: String, default: '' },
})
</script>
