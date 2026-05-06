<template>
  <div :class="cn('flex h-full w-full items-center justify-center rounded-full bg-muted text-sm font-medium', props.class)">
    <slot />
  </div>
</template>
<script setup>
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: String, default: '' } })
</script>
