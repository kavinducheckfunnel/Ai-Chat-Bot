<template>
  <div v-show="isActive" :class="cn('mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2', props.class)">
    <slot />
  </div>
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
