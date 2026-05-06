<template>
  <button
    type="button"
    :class="cn('inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50', isActive ? 'bg-background text-foreground shadow' : 'hover:text-foreground', props.class)"
    @click="ctx?.setActive(value)"
  >
    <slot />
  </button>
</template>
<script setup>
import { cn } from '@/lib/utils'
import { inject, computed } from 'vue'
const props = defineProps({
  value: { type: String, required: true },
  class: { type: String, default: '' },
})
const ctx = inject('tabs', null)
const isActive = computed(() => ctx?.active.value === props.value)
</script>
