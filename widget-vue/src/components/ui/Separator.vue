<template>
  <div
    role="separator"
    :aria-orientation="orientation"
    :class="cn('shrink-0 bg-border', orientation === 'vertical' ? 'w-px h-full' : 'h-px w-full', props.class)"
  />
</template>
<script setup>
import { cn } from '@/lib/utils'
const props = defineProps({
  orientation: { type: String, default: 'horizontal' },
  class: { type: String, default: '' },
})
</script>
