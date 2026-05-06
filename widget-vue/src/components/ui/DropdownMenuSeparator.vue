<template>
  <div :class="cn('-mx-1 my-1 h-px bg-muted', props.class)" />
</template>
<script setup>
import { cn } from '@/lib/utils'
const props = defineProps({ class: { type: String, default: '' } })
</script>
