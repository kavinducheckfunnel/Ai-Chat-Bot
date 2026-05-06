<template>
  <div :class="cn('relative h-2 w-full overflow-hidden rounded-full bg-primary/20', props.class)">
    <div
      class="h-full w-full flex-1 bg-primary transition-all"
      :style="{ transform: `translateX(-${100 - (value ?? 0)}%)` }"
    />
  </div>
</template>
<script setup>
import { cn } from '@/lib/utils'
const props = defineProps({
  value: { type: Number, default: 0 },
  class: { type: String, default: '' },
})
</script>
